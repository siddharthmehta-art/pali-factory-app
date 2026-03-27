import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Auto Inventory", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
ORDER_FILE = "production_orders.csv"

# --- DATA LOADING (Self-Healing) ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Material_Used_Qty'] else "Pending QCI"
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- LOGIN ---
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

# --- SIDEBAR ---
st.sidebar.title(f"User: {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["📋 Orders", "🏗️ Production & Scrap", "📦 Raw Material Stock", "🏭 QCI & Dispatch", "📊 Reports"])

# 1. ORDERS
with tabs[0]:
    st.header("Daily Production Orders")
    order_df = load_data(ORDER_FILE, ["Timestamp", "Machine", "Specs", "Target"])
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Set New Order"):
            with st.form("order_form"):
                m_type = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
                specs = st.text_area("Specs (Size, OD, etc.)")
                target = st.number_input("Target KM", min_value=0.0)
                if st.form_submit_button("Issue Order"):
                    new_o = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Machine": m_type, "Specs": specs, "Target": target}])
                    save_data(pd.concat([order_df, new_o]), ORDER_FILE)
                    st.success("Order Issued!")
                    st.rerun()
    st.dataframe(order_df)

# 2. PRODUCTION & SCRAP (WITH AUTO-STOCK LESSING)
with tabs[1]:
    st.header("Production Entry & Material Consumption")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    
    with st.form("prod_form", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
        prod_name = st.text_input("Product Name/Size")
        
        c1, c2 = st.columns(2)
        km = c1.number_input("Finished Output (KM)", min_value=0.0)
        scrp = c2.number_input("Scrap Produced (KG)", min_value=0.0)
        
        st.markdown("---")
        st.subheader("Material Consumption")
        mat_type = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"])
        mat_consumed = st.number_input(f"Total {mat_type} used in Production (KG)", min_value=0.0)
        
        if st.form_submit_button("Submit Production & Update Stock"):
            total_deduction = mat_consumed + scrp
            
            # Check if enough stock exists
            current_stock = stock_df.loc[stock_df['Item'] == mat_type, 'Quantity'].values[0] if mat_type in stock_df['Item'].values else 0
            
            if current_stock < total_deduction:
                st.error(f"Insufficient Stock! You need {total_deduction}kg but only {current_stock}kg available.")
            else:
                # 1. Update Stock File
                stock_df.loc[stock_df['Item'] == mat_type, 'Quantity'] -= total_deduction
                save_data(stock_df, STOCK_FILE)
                
                # 2. Log Production
                new_log = pd.DataFrame([{
                    "Date": datetime.now().date(), "Machine": m_sel, "Product": prod_name, 
                    "KM": km, "Scrap": scrp, "Material": mat_type, "Mat_Consumed": total_deduction, "Status": "Pending QCI"
                }])
                all_logs = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Material", "Mat_Consumed", "Status"])
                save_data(pd.concat([all_logs, new_log], ignore_index=True), PROD_FILE)
                
                st.success(f"Logged! {total_deduction}kg deducted from {mat_type} stock.")

# 3. RAW MATERIAL STOCK
with tabs[2]:
    st.header("Current Inventory Status")
    curr_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Add Raw Material (Purchase)"):
            with st.form("stock_update"):
                it = st.selectbox("Item", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"])
                qty = st.number_input("Quantity Received (KG)", min_value=0.0)
                if st.form_submit_button("Add to Stock"):
                    if it in curr_stock['Item'].values:
                        curr_stock.loc[curr_stock['Item'] == it, 'Quantity'] += qty
                    else:
                        curr_stock = pd.concat([curr_stock, pd.DataFrame([{"Item": it, "Quantity": qty}])], ignore_index=True)
                    save_data(curr_stock, STOCK_FILE)
                    st.rerun()
    st.table(curr_stock)

# 4. QCI & DISPATCH
with tabs[3]:
    st.header("Quality Check & Ready Goods")
    all_p = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Status"])
    pending = all_p[all_p['Status'] == "Pending QCI"]
    
    if not pending.empty:
        sel = st.selectbox("Select Batch for QC", pending['Product'].unique())
        if st.button("Pass QC & Approve for Dispatch"):
            all_p.loc[all_p['Product'] == sel, 'Status'] = "Ready for Dispatch"
            save_data(all_p, PROD_FILE)
            st.success("Approved!")
            st.rerun()
    
    st.subheader("📦 Ready for Dispatch")
    st.dataframe(all_p[all_p['Status'] == "Ready for Dispatch"])

# 5. REPORTS
with tabs[4]:
    st.header("Master Factory Reports")
    full_log = load_data(PROD_FILE, [])
    st.dataframe(full_log)
    if st.session_state['user_role'] == "Admin":
        st.download_button("Download Full Excel Report", full_log.to_csv(index=False), "Pali_Factory_Master.csv")
