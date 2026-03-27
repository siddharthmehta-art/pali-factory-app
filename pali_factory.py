import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Master", layout="wide")

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
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Qty'] else ""
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

# --- TABS (Nothing Removed) ---
main_tabs = ["📋 Orders & FG Stock", "🏗️ Production Entry", "🧪 QCI Lab", "📦 Raw Material", "📊 Reports"]
if st.session_state['user_role'] == "Admin":
    main_tabs.append("👨‍💼 Admin Control")

tabs = st.tabs(main_tabs)

# 1. ORDER BOOK & FG STOCK
with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.header("📝 Customer Order Book")
        orders = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
        if st.session_state['user_role'] == "Admin":
            with st.expander("➕ Add Manual Order"):
                with st.form("manual_order"):
                    cust = st.text_input("Customer Name")
                    it = st.text_input("Item Specs")
                    q = st.number_input("Qty (KM)", min_value=0.0)
                    dd = st.date_input("Deadline")
                    if st.form_submit_button("Save Order"):
                        new_o = pd.DataFrame([{"Order_ID": datetime.now().strftime("%S"), "Customer": cust, "Item": it, "Qty": q, "Deadline": dd}])
                        save_data(pd.concat([orders, new_o], ignore_index=True), ORDER_BOOK_FILE)
                        st.rerun()
        st.dataframe(orders, use_container_width=True)
    with col2:
        st.header("📦 Finished Goods Stock")
        fg = load_data(FG_STOCK_FILE, ["Item", "Qty", "Status"])
        st.dataframe(fg, use_container_width=True)

# 2. PRODUCTION ENTRY (Material Consumed + Scrap Deduction)
with tabs[1]:
    st.header("Machine Work Entry")
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
                st.success("Entry Saved & Stock Deducted")

# 3. QCI LAB (The Requested Tests)
with tabs[2]:
    st.header("🧪 QCI Lab Testing")
    p_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch for Lab Testing", pending['Product'].unique())
        with st.form("lab_tests"):
            st.write(f"Testing Batch: {batch}")
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("Tensile Strength (N/mm²)")
                st.number_input("Elongation (%)")
                st.number_input("Hotset Test (mm)")
            with c2:
                st.number_input("CR Test (Ω/km)")
                st.number_input("Breaking Load (kN)")
            if st.form_submit_button("APPROVE & PASS"):
                p_log.loc[p_log['Product'] == batch, 'Status'] = "Ready for Dispatch"
                save_data(p_log, PROD_FILE)
                # Auto add to Finished Goods
                fg_curr = load_data(FG_STOCK_FILE, ["Item", "Qty", "Status"])
                new_fg = pd.DataFrame([{"Item": batch, "Qty": p_log.loc[p_log['Product']==batch, 'KM'].values[0], "Status": "Passed QC"}])
                save_data(pd.concat([fg_curr, new_fg], ignore_index=True), FG_STOCK_FILE)
                st.rerun()

# 4. RAW MATERIAL STOCK
with tabs[3]:
    st.header("Raw Material Inventory")
    rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
    st.table(rm_stock)

# 5. REPORTS (RESTORED)
with tabs[4]:
    st.header("📊 Master Factory Reports")
    report_data = load_data(PROD_FILE, [])
    st.dataframe(report_data, use_container_width=True)
    st.download_button("📥 Download All Production Data", report_data.to_csv(index=False), "Full_Factory_Report.csv")

# 6. ADMIN CONTROL (WITH NEW STOCK ADJUSTMENT)
if st.session_state['user_role'] == "Admin":
    with tabs[5]:
        st.header("👨‍💼 Master Admin Tools")
        
        # A. User Management
        with st.expander("👤 Manage Staff Accounts"):
            new_u = st.text_input("New ID")
            new_p = st.text_input("New Pass")
            if st.button("Create Staff Login"):
                users_df = pd.concat([users_df, pd.DataFrame([{"UserID": new_u, "Password": new_p, "Role": "Operator"}])], ignore_index=True)
                save_data(users_df, USER_FILE); st.rerun()

        # B. Correction Tool
        with st.expander("🛠️ Delete Mistake Entries"):
            all_p = load_data(PROD_FILE, ["Product"])
            to_del = st.selectbox("Select Batch to Delete", all_p['Product'].unique())
            if st.button("Delete Permanently", type="primary"):
                p_new = load_data(PROD_FILE, []); p_new = p_new[p_new['Product'] != to_del]
                save_data(p_new, PROD_FILE); st.rerun()

        # C. Stock Adjustment (Requested)
        with st.expander("⚖️ Manual Stock Adjustment"):
            st.warning("Use this only if an operator entered wrong deduction values.")
            adj_rm = load_data(STOCK_FILE, ["Item", "Quantity"])
            target_rm = st.selectbox("Select Material to Fix", adj_rm['Item'].unique() if not adj_rm.empty else ["Aluminum Rod"])
            new_qty = st.number_input("Set Correct Total Weight (KG)")
            if st.button("Fix Stock Level"):
                adj_rm.loc[adj_rm['Item'] == target_rm, 'Quantity'] = new_qty
                save_data(adj_rm, STOCK_FILE); st.success("Stock Level Fixed"); st.rerun()
