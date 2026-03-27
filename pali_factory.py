import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
QCI_FILE = "qci_testing_logs.csv"
ORDER_FILE = "production_orders.csv"

# --- FIXED DATA LOADING (Self-Healing Logic) ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            # FIX: If file exists but missing columns (like Status), add them automatically
            for col in default_cols:
                if col not in df.columns:
                    df[col] = "Pending QCI" if col == "Status" else ""
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- INITIALIZE SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Load Users
users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    users_df = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    save_data(users_df, USER_FILE)

# --- LOGIN ---
if not st.session_state['logged_in']:
    st.title("🔐 Pali Cable ERP - Login")
    with st.form("login"):
        u = st.text_input("User ID")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            match = users_df[(users_df['UserID'] == u) & (users_df['Password'] == p)]
            if not match.empty:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = match.iloc[0]['Role']
                st.session_state['user_id'] = u
                st.rerun()
    st.stop()

# --- MAIN NAVIGATION ---
st.sidebar.title(f"User: {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["📋 Orders", "🏗️ Production & Scrap", "📦 Raw Material", "🏭 QCI & Testing", "📊 Reports"])

# 1. DAILY PRODUCTION ORDERS
with tabs[0]:
    st.header("Daily Production Orders")
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Set Machine Order"):
            m_type = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
            with st.form("order_form"):
                specs = st.text_area("Enter Specifications (Size, OD, No. of Bobbin, etc.)")
                target = st.number_input("Target KM", min_value=0.0)
                if st.form_submit_button("Issue Order"):
                    new_o = pd.DataFrame([{"Timestamp": datetime.now(), "Machine": m_type, "Specs": specs, "Target": target}])
                    save_data(pd.concat([load_data(ORDER_FILE, ["Timestamp", "Machine", "Specs", "Target"]), new_o]), ORDER_FILE)
                    st.success("Order Sent!")
    st.dataframe(load_data(ORDER_FILE, ["Timestamp", "Machine", "Specs", "Target"]))

# 2. PRODUCTION & SCRAP
with tabs[1]:
    st.header("Daily Machine Entry")
    with st.form("prod_form", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
        prod_name = st.text_input("Product Size/Name")
        km = st.number_input("Finished KM", min_value=0.0)
        scrp = st.number_input("Scrap (KG)", min_value=0.0)
        if st.form_submit_button("Log Production"):
            new_log = pd.DataFrame([{"Date": datetime.now().date(), "Machine": m_sel, "Product": prod_name, "KM": km, "Scrap": scrp, "Status": "Pending QCI"}])
            all_logs = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Status"])
            save_data(pd.concat([all_logs, new_log], ignore_index=True), PROD_FILE)
            st.success("Logged! Awaiting Quality Check.")

# 3. RAW MATERIAL STOCK
with tabs[2]:
    st.header("Stock of Raw Materials")
    mat_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    if st.session_state['user_role'] == "Admin":
        with st.form("stock_update"):
            it = st.selectbox("Item", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"])
            qty = st.number_input("Add/Subtract Qty", value=0.0)
            if st.form_submit_button("Update Stock"):
                if it in mat_df['Item'].values:
                    mat_df.loc[mat_df['Item'] == it, 'Quantity'] += qty
                else:
                    mat_df = pd.concat([mat_df, pd.DataFrame([{"Item": it, "Quantity": qty}])], ignore_index=True)
                save_data(mat_df, STOCK_FILE)
                st.rerun()
    st.table(mat_df)

# 4. QCI & TESTING
with tabs[3]:
    st.header("Quality Control Inspection")
    prod_data = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Status"])
    # Filter only items that are pending
    if 'Status' in prod_data.columns:
        pending = prod_data[prod_data['Status'] == "Pending QCI"]
        if pending.empty:
            st.info("No items pending QCI.")
        else:
            selected_prod = st.selectbox("Select Batch", pending['Product'].unique())
            with st.form("qci_form"):
                st.write(f"Testing: {selected_prod}")
                test1 = st.checkbox("Resistance Test Passed?")
                test2 = st.checkbox("HV Test Passed?")
                if st.form_submit_button("Approve for Dispatch"):
                    if test1 and test2:
                        prod_data.loc[prod_data['Product'] == selected_prod, 'Status'] = "Ready for Dispatch"
                        save_data(prod_data, PROD_FILE)
                        st.success("Passed and Ready for Dispatch!")
                        st.rerun()
                    else:
                        st.error("Cannot approve without passing tests.")
    else:
        st.error("Data structure error. Please log a new production entry.")

# 5. REPORTS
with tabs[4]:
    st.header("Reports & Final Stock")
    final_df = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Status"])
    
    st.subheader("Ready for Dispatch (Finished Products)")
    # Double check for Status column before filtering
    if 'Status' in final_df.columns:
        st.dataframe(final_df[final_df['Status'] == "Ready for Dispatch"])
    else:
        st.write("No dispatch-ready items found.")
    
    if st.session_state['user_role'] == "Admin":
        st.download_button("Download All Records", final_df.to_csv(index=False), "Factory_Report.csv")
