import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Master Control", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
ORDER_BOOK_FILE = "order_book.csv"
FG_STOCK_FILE = "fg_stock.csv"
PROG_FILE = "daily_programme.csv"

# --- DATA LOADING & CLEANING ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Mat_Consumed', 'Qty'] else "None"
            num_cols = ['KM', 'Scrap', 'Mat_Consumed', 'Quantity', 'Qty']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
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
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['Role'], 'user_id': u_id})
                st.rerun()
            else:
                st.error("Access Denied")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- TABS ---
main_tabs = ["📅 Daily Programme", "🏗️ Production Entry", "🧪 QCI Lab", "📝 Order Book"]
if st.session_state['user_role'] == "Admin":
    main_tabs.extend(["📦 Raw Material Stock", "📊 Admin Reports", "👨‍💼 Admin Control"])

tabs = st.tabs(main_tabs)

# 1. DAILY PROGRAMME (All view, Admin updates)
with tabs[0]:
    st.header("📅 Daily Production Programme")
    prog_df = load_data(PROG_FILE, ["Machine", "Target_Product", "Target_Qty", "Instructions"])
    machines = ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"]
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("📝 Update Machine Programme"):
            with st.form("update_prog"):
                m_target = st.selectbox("Select Machine", machines)
                p_target = st.text_input("Product Size/Type")
                q_target = st.text_input("Target (KM/Units)")
                instr = st.text_area("Instructions")
                if st.form_submit_button("Update"):
                    prog_df = prog_df[prog_df['Machine'] != m_target]
                    new_entry = pd.DataFrame([{"Machine": m_target, "Target_Product": p_target, "Target_Qty": q_target, "Instructions": instr}])
                    prog_df = pd.concat([prog_df, new_entry], ignore_index=True)
                    save_data(prog_df, PROG_FILE); st.rerun()
    st.table(prog_df)

# 2. PRODUCTION ENTRY (Traceability + Stoppage)
with tabs[1]:
    st.header("Machine Work Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", machines)
        p_name = st.text_input("Batch/Product Name")
        km = st.number_input("Output KM", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Net Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap (KG)", min_value=0.0)
        stop_reason = st.text_area("Delay Reason (Optional)")
        if st.form_submit_button("Submit"):
            # Logic same as before...
            prod_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state['user_id'], "Machine": m_sel, "Product": p_name, "KM": km, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop_reason, "Status": "Pending QCI"}])
            save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= (cons + scrp)
                save_data(stock_df, STOCK_FILE)
            st.success("Entry Saved")

# 3. QCI LAB
with tabs[2]:
    st.header("🧪 QCI Lab Testing")
    p_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch", pending['Product'].unique())
        if st.button("APPROVE & PASS QCI"):
            p_log.loc[p_log['Product'] == batch, 'Status'] = "Ready for Dispatch"
            save_data(p_log, PROD_FILE); st.rerun()

# 4. ORDER BOOK (View Mode)
with tabs[3]:
    st.header("📝 Customer Orders")
    order_book = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
    st.dataframe(order_book, use_container_width=True)

# --- ADMIN ONLY TABS ---
if st.session_state['user_role'] == "Admin":
    # 5. RAW MATERIAL (Admin View)
    with tabs[4]:
        st.header("📦 Private Inventory")
        rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
        st.table(rm_stock)

    # 6. REPORTS (Traceability)
    with tabs[5]:
        st.header("📊 Performance Reports")
        full_data = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info"])
        st.dataframe(full_data, use_container_width=True)

    # 7. ADMIN CONTROL (EDIT/DELETE SUITE)
    with tabs[6]:
        st.header("👨‍💼 Master Admin Tools")
        
        # EDIT ORDER BOOK
        with st.expander("📝 Manage Order Book (Add/Edit/Delete)"):
            ob_df = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Add New Order")
                with st.form("add_ob"):
                    cust = st.text_input("Customer")
                    it = st.text_input("Item")
                    q = st.number_input("Qty", min_value=0.0)
                    dl = st.date_input("Deadline")
                    if st.form_submit_button("Add Order"):
                        new_o = pd.DataFrame([{"Order_ID": datetime.now().strftime("%f"), "Customer": cust, "Item": it, "Qty": q, "Deadline": dl}])
                        save_data(pd.concat([ob_df, new_o], ignore_index=True), ORDER_BOOK_FILE); st.rerun()
            
            with c2:
                st.subheader("Edit/Delete Existing Order")
                if not ob_df.empty:
                    to_edit = st.selectbox("Select Order ID to Remove", ob_df['Order_ID'].unique())
                    if st.button("Delete Selected Order", type="primary"):
                        ob_df = ob_df[ob_df['Order_ID'] != str(to_edit)]
                        save_data(ob_df, ORDER_BOOK_FILE); st.rerun()

        # EDIT RAW MATERIAL STOCK
        with st.expander("⚖️ Edit Raw Material Stock (Manual Fix)"):
            rms_df = load_data(STOCK_FILE, ["Item", "Quantity"])
            target_rm = st.selectbox("Select Material", rms_df['Item'].unique() if not rms_df.empty else ["Aluminum Rod"])
            new_val = st.number_input("Set Absolute Correct Quantity (KG)", min_value=0.0)
            if st.button("Overwrite Stock Level"):
                rms_df.loc[rms_df['Item'] == target_rm, 'Quantity'] = new_val
                save_data(rms_df, STOCK_FILE); st.success("Stock Level Updated!"); st.rerun()

        # MANAGE STAFF
        with st.expander("👤 Manage Operator Logins"):
            new_u = st.text_input("New Operator ID")
            new_p = st.text_input("Password")
            if st.button("Save Staff Account"):
                u_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
                u_df = pd.concat([u_df, pd.DataFrame([{"UserID": new_u, "Password": new_p, "Role": "Operator"}])], ignore_index=True)
                save_data(u_df, USER_FILE); st.rerun()
