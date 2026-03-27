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
PROGRAM_FILE = "daily_program.csv" # New: Daily Machine Schedule
FG_STOCK_FILE = "fg_stock.csv"

# --- DATA LOADING & CLEANING ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Mat_Consumed'] else "None"
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
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = match.iloc[0]['Role']
                st.session_state['user_id'] = u_id
                st.rerun()
            else:
                st.error("Access Denied")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state['user_id']}")
st.sidebar.info(f"Access Level: {st.session_state['user_role']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- TAB LOGIC (Admin vs Operator Visibility) ---
if st.session_state['user_role'] == "Admin":
    main_tabs = ["📅 Production Program", "🏗️ Machine Entry", "🧪 QCI Lab", "📦 Raw Material", "📊 Daily Reports", "👨‍💼 Admin Tools"]
else:
    # Operators CANNOT see Raw Material or Reports
    main_tabs = ["📅 Production Program", "🏗️ Machine Entry", "🧪 QCI Lab"]

tabs = st.tabs(main_tabs)
MACHINES = ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"]

# 1. DAILY PRODUCTION PROGRAM
with tabs[0]:
    st.header("📋 Daily Machine Schedule")
    prog_df = load_data(PROGRAM_FILE, ["Machine", "Target_Specs", "Target_Qty", "Updated_By"])
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("📝 Update Machine Program (Admin Only)"):
            with st.form("update_program"):
                m_target = st.selectbox("Select Machine to Update", MACHINES)
                specs = st.text_input("Specifications / Size")
                t_qty = st.text_input("Target Quantity (KM)")
                if st.form_submit_button("Update Program"):
                    # Remove old entry for this machine and add new
                    prog_df = prog_df[prog_df['Machine'] != m_target]
                    new_entry = pd.DataFrame([{"Machine": m_target, "Target_Specs": specs, "Target_Qty": t_qty, "Updated_By": st.session_state['user_id']}])
                    prog_df = pd.concat([prog_df, new_entry], ignore_index=True)
                    save_data(prog_df, PROGRAM_FILE)
                    st.success(f"Program for {m_target} updated.")
                    st.rerun()
    
    st.table(prog_df)

# 2. MACHINE ENTRY (WITH OPERATOR TRACKING)
with tabs[1]:
    st.header("🏗️ Machine Work Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine ID", MACHINES)
        p_name = st.text_input("Product Name/Batch")
        km = st.number_input("Finished KM", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Material Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Produced (KG)", min_value=0.0)
        stop_reason = st.text_area("Stoppage Reason / Remarks")
        
        if st.form_submit_button("Submit Work Report"):
            total_less = cons + scrp
            if mat in stock_df['Item'].values:
                # Stock Math
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= total_less
                save_data(stock_df, STOCK_FILE)
                # Production Log with USERNAME
                prod_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Operator", "Status"])
                new_log = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Machine": m_sel, "Product": p_name, "KM": km, 
                    "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, 
                    "Stoppage_Info": stop_reason if stop_reason else "Smooth",
                    "Operator": st.session_state['user_id'], # TRACKING NAME
                    "Status": "Pending QCI"
                }])
                save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
                st.success(f"Entry Saved by {st.session_state['user_id']}")

# 3. QCI LAB
with tabs[2]:
    st.header("🧪 QCI Testing Suite")
    p_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Operator", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch", pending['Product'].unique())
        if st.button("APPROVE BATCH"):
            p_log.loc[p_log['Product'] == batch, 'Status'] = "Passed QC"
            # Add to QC log with username
            save_data(p_log, PROD_FILE)
            st.success(f"Approved by {st.session_state['user_id']}")
            st.rerun()

# --- ADMIN ONLY TABS ---
if st.session_state['user_role'] == "Admin":
    # 4. RAW MATERIAL
    with tabs[3]:
        st.header("📦 Raw Material Inventory (Admin Only)")
        rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
        st.table(rm_stock)

    # 5. REPORTS
    with tabs[4]:
        st.header("📊 Full Factory Reports (Admin Only)")
        full_data = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Operator", "Stoppage_Info"])
        st.dataframe(full_data, use_container_width=True)

    # 6. ADMIN TOOLS
    with tabs[5]:
        st.header("👨‍💼 Staff & Stock Control")
        # Manage Users Code...
        with st.expander("Create Staff Account"):
            n_u = st.text_input("New Operator Username")
            n_p = st.text_input("Assign Password")
            if st.button("Add Staff"):
                u_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
                u_df = pd.concat([u_df, pd.DataFrame([{"UserID": n_u, "Password": n_p, "Role": "Operator"}])], ignore_index=True)
                save_data(u_df, USER_FILE); st.success("Staff Created"); st.rerun()
