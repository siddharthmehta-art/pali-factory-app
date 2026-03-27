import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Inventory Sync", layout="wide")

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
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Mat_Consumed'] else "Pending QCI"
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
    st.dataframe(order_df, use_container_width=True)

# 2. PRODUCTION & SCRAP (DEDUCTION LOGIC)
with tabs[1]:
    st.header("Machine Entry & Automatic Stock Deduction")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    
    with st.form("prod_form", clear_on_submit=True):
        m_sel = st.selectbox("Machine ID", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
        prod_name = st.text_input("Product Size/Name")
        
        col_out, col_scrp = st.columns(2)
        km_out = col_out.number_input("Production Finished (KM)", min_value=0.0)
        scrap_val = col_scrp.number_input("Scrap Generated (KG)", min_value=0.0)
        
        st.markdown("---")
        st.subheader("Inventory Consumption")
        # List items from stock for operator to choose
        available_mats = stock_df['Item'].unique().tolist() if not stock_df.empty else ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"]
        mat_type = st.selectbox("Select Material Used", available_mats)
        mat_consumed = st.number_input(f"Net {mat_type} Consumed in Product (KG)", min_value=0.0)
        
        st.info(f"Formula: Total Stock Deduction = {mat_consumed} (Consumed) + {scrap_val} (Scrap)")

        if st.form_submit_button("Submit Work & Update Stock"):
            # CRITICAL CALCULATION
            total_to_less = mat_consumed + scrap_val
            
            # Check if stock exists
            if mat_type in stock_df['Item'].values:
                current_qty = stock_df.loc[stock_df['Item'] == mat_type, 'Quantity'].values[0]
                
                if current_qty < total_to_less:
                    st.error(f"Cannot Submit! Stock for {mat_type} is only {current_qty}kg. You are trying to deduct {total_to_less}kg.")
                else:
                    # 1. Deduct from Stock
                    stock_df.loc[stock_df['Item'] == mat_type, 'Quantity'] -= total_to_less
                    save_data(stock_df, STOCK_FILE)
                    
                    # 2. Log to Production History
                    new_entry = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Machine": m_sel, "Product": prod_name, "KM": km_out, 
                        "Scrap": scrap_val, "Material": mat_type, 
                        "Total_Deduction": total_to_less, "Status": "Pending QCI"
                    }])
                    prod_logs = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Material", "Total_Deduction", "Status"])
                    save_data(pd.concat([prod_logs, new_entry], ignore_index=True), PROD_FILE)
                    
                    st.success(f"Success! Deducted {total_to_less} KG from {mat_type} stock.")
                    st.rerun()
            else:
                st.error("Material not found in Stock Records. Admin must add stock first.")

# 3. RAW MATERIAL STOCK (Admin Updates)
with tabs[2]:
    st.header("Raw Material Inventory")
    curr_inv = load_data(STOCK_FILE, ["Item", "Quantity"])
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Update/Add Stock (Purchase)"):
            with st.form("add_stock"):
                it_name = st.selectbox("Material", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"])
                it_qty = st.number_input("Weight Received (KG)", min_value=0.0)
                if st.form_submit_button("Add to Inventory"):
                    if it_name in curr_inv['Item'].values:
                        curr_inv.loc[curr_inv['Item'] == it_name, 'Quantity'] += it_qty
                    else:
                        curr_inv = pd.concat([curr_inv, pd.DataFrame([{"Item": it_name, "Quantity": it_qty}])], ignore_index=True)
                    save_data(curr_inv, STOCK_FILE)
                    st.success(f"Added {it_qty}kg to {it_name}")
                    st.rerun()
    st.table(curr_inv)

# 4. QCI & DISPATCH
with tabs[3]:
    st.header("Quality Control & Testing")
    p_data = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Scrap", "Material", "Total_Deduction", "Status"])
    pending = p_data[p_data['Status'] == "Pending QCI"]
    
    if not pending.empty:
        sel_batch = st.selectbox("Select Batch to Approve", pending['Product'].unique())
        if st.button("Approve Batch for Dispatch"):
            p_data.loc[p_data['Product'] == sel_batch, 'Status'] = "Ready for Dispatch"
            save_data(p_data, PROD_FILE)
            st.success(f"{sel_batch} cleared for dispatch.")
            st.rerun()
    
    st.subheader("🚛 Ready for Dispatch")
    st.dataframe(p_data[p_data['Status'] == "Ready for Dispatch"], use_container_width=True)

# 5. REPORTS
with tabs[4]:
    st.header("Master Factory Logs")
    master_df = load_data(PROD_FILE, [])
    st.dataframe(master_df, use_container_width=True)
    if st.session_state['user_role'] == "Admin":
        st.download_button("Download Full Excel Report", master_df.to_csv(index=False), "Pali_ERP_Report.csv")
