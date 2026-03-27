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
ORDER_FILE = "production_orders.csv"

# --- DATA LOADING ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Total_Deduction'] else ""
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    admin_df = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    save_data(admin_df, USER_FILE)
    users_df = admin_df

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

# --- SIDEBAR ---
st.sidebar.title(f"User: {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["📋 Daily Production Order", "🏗️ Production & Scrap Entry", "📦 Raw Material Stock", "📊 Reports"])

# 1. DAILY PRODUCTION ORDER (3 COLUMNS ONLY)
with tabs[0]:
    st.header("Daily Production Order")
    order_df = load_data(ORDER_FILE, ["Machine", "Specs", "Quantity", "Order_Date"])
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Create New Order"):
            with st.form("order_form", clear_on_submit=True):
                m_type = st.selectbox("Select Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                
                # Simplified 3 Columns Input
                specs = st.text_input("SPECS (e.g. Size, OD, Grade)")
                qty = st.number_input("QUANTITY (KM or Units)", min_value=0.0)
                o_date = st.date_input("DATE OF PRODUCTION ORDER")
                
                if st.form_submit_button("Submit Order"):
                    new_o = pd.DataFrame([{"Machine": m_type, "Specs": specs, "Quantity": qty, "Order_Date": o_date}])
                    save_data(pd.concat([order_df, new_o], ignore_index=True), ORDER_FILE)
                    st.success("Order Created Successfully!")
                    st.rerun()
    
    # Display table with ONLY specified columns
    if not order_df.empty:
        st.subheader("Current Floor Orders")
        st.table(order_df[["Machine", "Specs", "Quantity", "Order_Date"]])
        st.download_button("📥 Download Order Sheet", order_df.to_csv(index=False), "Daily_Orders.csv")

# 2. PRODUCTION & SCRAP (WITH AUTO-DEDUCTION)
with tabs[1]:
    st.header("Machine Work Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_name = st.text_input("Product Name")
        km_done = st.number_input("Output (KM)", min_value=0.0)
        
        st.divider()
        st.subheader("Material & Scrap Deduction")
        mat_type = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC", "Steel"])
        mat_consumed = st.number_input("Net Material Consumed (KG)", min_value=0.0)
        scrap_kg = st.number_input("Scrap Produced (KG)", min_value=0.0)
        
        if st.form_submit_button("Submit Entry"):
            total_less = mat_consumed + scrap_kg
            
            # Inventory Check & Deduction
            if mat_type in stock_df['Item'].values:
                current_q = stock_df.loc[stock_df['Item'] == mat_type, 'Quantity'].values[0]
                if current_q >= total_less:
                    # 1. Deduct Stock
                    stock_df.loc[stock_df['Item'] == mat_type, 'Quantity'] -= total_less
                    save_data(stock_df, STOCK_FILE)
                    
                    # 2. Save Production Log
                    prod_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Material", "Total_Deduction"])
                    new_log = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Machine": m_sel, "Product": p_name, "KM": km_done, 
                        "Scrap": scrap_kg, "Material": mat_type, "Total_Deduction": total_less
                    }])
                    save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
                    st.success(f"Log Saved! {total_less}kg deducted from {mat_type} stock.")
                else:
                    st.error(f"Insufficient Stock! Only {current_q}kg available.")
            else:
                st.error("Material not found in stock. Admin must add stock first.")

# 3. RAW MATERIAL STOCK
with tabs[2]:
    st.header("Inventory Status")
    curr_inv = load_data(STOCK_FILE, ["Item", "Quantity"])
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Add Stock"):
            with st.form("add_stock"):
                it = st.selectbox("Item", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"])
                q = st.number_input("Quantity Added (KG)", min_value=0.0)
                if st.form_submit_button("Update Inventory"):
                    if it in curr_inv['Item'].values:
                        curr_inv.loc[curr_inv['Item'] == it, 'Quantity'] += q
                    else:
                        curr_inv = pd.concat([curr_inv, pd.DataFrame([{"Item": it, "Quantity": q}])], ignore_index=True)
                    save_data(curr_inv, STOCK_FILE)
                    st.success("Stock Added")
                    st.rerun()
    st.table(curr_inv)

# 4. REPORTS
with tabs[3]:
    st.header("Master Factory Logs")
    full_report = load_data(PROD_FILE, [])
    st.dataframe(full_report, use_container_width=True)
    if st.session_state['user_role'] == "Admin":
        st.download_button("📥 Download Final Report", full_report.to_csv(index=False), "Pali_ERP_Full_Report.csv")
