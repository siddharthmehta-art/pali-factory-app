import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Quality Control", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
QCI_FILE = "qci_testing_logs.csv"

# --- DATA FUNCTIONS ---
def load_data(filename, cols):
    if os.path.exists(filename):
        try: return pd.read_csv(filename)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    users_df = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    save_data(users_df, USER_FILE)

if not st.session_state['logged_in']:
    st.title("🔐 Pali Cable ERP - Login")
    with st.form("login"):
        u = st.text_input("User ID")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            match = users_df[(users_df['UserID'] == u) & (users_df['Password'] == p)]
            if not match.empty:
                st.session_state['logged_in'], st.session_state['user_role'], st.session_state['user_id'] = True, match.iloc[0]['Role'], u
                st.rerun()
    st.stop()

# --- MAIN NAVIGATION ---
st.sidebar.title(f"User: {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["🏗️ Production & Scrap", "📦 Raw Material Stock", "🏭 Finished Goods & QCI", "📊 Dispatch & Reports"])

# 1. PRODUCTION & SCRAP
with tabs[0]:
    st.header("Daily Machine Entry")
    with st.form("prod_form", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
        c1, c2 = st.columns(2)
        km = c1.number_input("Finished KM", min_value=0.0)
        scrp = c2.number_input("Scrap (KG)", min_value=0.0)
        item_name = st.text_input("Product Name (e.g., 1.1KV 3x25 ABC)")
        
        if st.form_submit_button("Log Production"):
            # Log Production
            new_log = pd.DataFrame([{"Date": datetime.now().date(), "Machine": m_sel, "Product": item_name, "KM": km, "Scrap": scrp, "Status": "Pending QCI"}])
            all_logs = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Status"])
            save_data(pd.concat([all_logs, new_log], ignore_index=True), PROD_FILE)
            st.success("Production logged. Now awaiting QCI Check.")

# 2. RAW MATERIAL STOCK
with tabs[1]:
    st.header("Raw Material Inventory")
    mat_df = load_data(STOCK_FILE, ["Item", "Quantity", "Unit"])
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Update Raw Material Stock"):
            with st.form("stock_form"):
                it = st.selectbox("Item", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire", "Masterbatch"])
                qty = st.number_input("Add/Subtract Quantity", value=0.0)
                if st.form_submit_button("Update Stock"):
                    if it in mat_df['Item'].values:
                        mat_df.loc[mat_df['Item'] == it, 'Quantity'] += qty
                    else:
                        mat_df = pd.concat([mat_df, pd.DataFrame([{"Item": it, "Quantity": qty, "Unit": "KG"}])], ignore_index=True)
                    save_data(mat_df, STOCK_FILE)
                    st.rerun()
    st.table(mat_df)

# 3. FINISHED GOODS & QCI (The "Gatekeeper")
with tabs[2]:
    st.header("Quality Control Inspection (QCI)")
    prod_data = load_data(PROD_FILE, [])
    pending_qci = prod_data[prod_data['Status'] == "Pending QCI"]

    if pending_qci.empty:
        st.info("No products currently waiting for QCI.")
    else:
        st.subheader("Items Awaiting Testing")
        selected_prod = st.selectbox("Select Batch to Test", pending_qci['Product'].unique())
        
        with st.form("qci_form"):
            st.write(f"Testing Batch: {selected_prod}")
            c1, c2, c3 = st.columns(3)
            res = c1.checkbox("Conductor Resistance Test Passed?")
            hv = c2.checkbox("High Voltage (HV) Test Passed?")
            od = c3.checkbox("Outer Diameter (OD) Verified?")
            remarks = st.text_area("QC Remarks / Test Values")
            qci_status = st.radio("Final Decision", ["PASS", "FAIL"])
            
            if st.form_submit_button("Submit QC Report"):
                if res and hv and od and qci_status == "PASS":
                    # Update Production Status to 'Ready for Dispatch'
                    prod_data.loc[prod_data['Product'] == selected_prod, 'Status'] = "Ready for Dispatch"
                    save_data(prod_data, PROD_FILE)
                    
                    # Log to QCI History
                    qci_log = pd.DataFrame([{"Timestamp": datetime.now(), "Product": selected_prod, "Status": "PASS", "Inspector": st.session_state['user_id']}])
                    save_data(pd.concat([load_data(QCI_FILE, []), qci_log], ignore_index=True), QCI_FILE)
                    st.success(f"{selected_prod} is now Ready for Dispatch!")
                else:
                    st.error("Batch FAILED Quality Check. Cannot be dispatched.")

# 4. DISPATCH & REPORTS
with tabs[3]:
    st.header("Dispatch Control & Reports")
    final_df = load_data(PROD_FILE, [])
    
    st.subheader("✅ Ready for Dispatch (Passed QCI)")
    ready_items = final_df[final_df['Status'] == "Ready for Dispatch"]
    st.dataframe(ready_items)

    if st.session_state['user_role'] == "Admin":
        st.subheader("📥 Master Reports")
        st.download_button("Download Full Production & QC Report", final_df.to_csv(index=False), "Factory_Master_Report.csv")
