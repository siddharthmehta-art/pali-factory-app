import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Admin Master", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
ORDER_BOOK_FILE = "order_book.csv"
FG_STOCK_FILE = "fg_stock.csv"

# --- DATA LOADING & SAVING ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- LOGIN SYSTEM (The Firewall) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    admin_setup = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    save_data(admin_setup, USER_FILE)
    users_df = admin_setup

if not st.session_state['logged_in']:
    st.title("🛡️ Pali Cable ERP - Secure Login")
    with st.form("login_gate"):
        u_id = st.text_input("User ID")
        u_pw = st.text_input("Password", type="password")
        if st.form_submit_button("Enter Factory App"):
            match = users_df[(users_df['UserID'] == u_id) & (users_df['Password'] == u_pw)]
            if not match.empty:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = match.iloc[0]['Role']
                st.session_state['user_id'] = u_id
                st.rerun()
            else:
                st.error("Access Denied")
    st.stop()

# --- LOGGED IN AREA ---
st.sidebar.title(f"👤 {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

main_tabs = ["📋 Orders & FG Stock", "🏗️ Production Entry", "🧪 QCI Lab", "📦 Raw Material"]
if st.session_state['user_role'] == "Admin":
    main_tabs.append("👨‍💼 Admin Control")

tabs = st.tabs(main_tabs)

# 1. ORDER BOOK & FG STOCK
with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.header("📝 Order Book")
        orders = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
        st.dataframe(orders, use_container_width=True)
    with col2:
        st.header("📦 Finished Goods")
        fg = load_data(FG_STOCK_FILE, ["Item", "Qty", "Status"])
        st.dataframe(fg, use_container_width=True)

# 2. PRODUCTION ENTRY
with tabs[1]:
    st.header("Production & Scrap Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_name = st.text_input("Batch Size/Name")
        km = st.number_input("Output KM", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Material Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap (KG)", min_value=0.0)
        if st.form_submit_button("Submit Entry"):
            total_deduct = cons + scrp
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= total_deduct
                save_data(stock_df, STOCK_FILE)
                prod_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Status"])
                new_log = pd.DataFrame([{"Date": datetime.now().date(), "Machine": m_sel, "Product": p_name, "KM": km, "Status": "Pending QCI"}])
                save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
                st.success("Entry Saved")

# 3. QCI LAB (Full Test Suite)
with tabs[2]:
    st.header("🧪 QCI Lab Testing")
    p_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch", pending['Product'].unique())
        with st.form("lab_tests"):
            st.write(f"Testing: {batch}")
            c1, c2 = st.columns(2)
            with c1:
                t1 = st.number_input("Tensile Strength")
                t2 = st.number_input("Elongation %")
                t3 = st.number_input("Hotset Test")
            with c2:
                t4 = st.number_input("CR Test (Resistance)")
                t5 = st.number_input("Breaking Load")
            if st.form_submit_button("PASS BATCH"):
                p_log.loc[p_log['Product'] == batch, 'Status'] = "Ready for Dispatch"
                save_data(p_log, PROD_FILE)
                fg_curr = load_data(FG_STOCK_FILE, ["Item", "Qty", "Status"])
                new_fg = pd.DataFrame([{"Item": batch, "Qty": p_log.loc[p_log['Product']==batch, 'KM'].values[0], "Status": "QC Passed"}])
                save_data(pd.concat([fg_curr, new_fg], ignore_index=True), FG_STOCK_FILE)
                st.success("Batch Approved")

# 4. RAW MATERIAL
with tabs[3]:
    st.header("Raw Material Inventory")
    rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
    st.table(rm_stock)

# 5. ADMIN CONTROL (DELETE & MANAGE)
if st.session_state['user_role'] == "Admin":
    with tabs[4]:
        st.header("👨‍💼 Master Admin Controls")
        
        # Section A: Manage Users
        st.subheader("1. Staff Account Management")
        u_col1, u_col2 = st.columns(2)
        with u_col1:
            new_user = st.text_input("New Operator ID")
            new_pass = st.text_input("Password")
            if st.button("Create Account"):
                users_df = pd.concat([users_df, pd.DataFrame([{"UserID": new_user, "Password": new_pass, "Role": "Operator"}])], ignore_index=True)
                save_data(users_df, USER_FILE)
                st.rerun()
        with u_col2:
            del_u = st.selectbox("Select User to Remove", users_df[users_df['Role'] != 'Admin']['UserID'].unique())
            if st.button("Delete User Account", type="primary"):
                users_df = users_df[users_df['UserID'] != del_u]
                save_data(users_df, USER_FILE)
                st.rerun()

        st.divider()
        
        # Section B: Delete Mistakes
        st.subheader("2. Correct Production Mistakes")
        current_logs = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Status"])
        if not current_logs.empty:
            log_to_del = st.selectbox("Select Entry to Delete", current_logs['Product'].unique())
            if st.button("Delete This Production Entry", type="primary"):
                current_logs = current_logs[current_logs['Product'] != log_to_del]
                save_data(current_logs, PROD_FILE)
                st.success(f"Entry {log_to_del} removed.")
                st.rerun()
