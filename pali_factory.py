import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Mat_Consumed', 'Qty', 'Target_Qty'] else ""
            num_cols = ['KM', 'Scrap', 'Mat_Consumed', 'Quantity', 'Qty', 'Target_Qty']
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
main_tabs = ["📅 Daily Programme", "🏗️ Production Entry", "🧪 QCI Lab", "📝 Order Book Search"]
if st.session_state['user_role'] == "Admin":
    main_tabs.extend(["📦 Raw Material Stock", "📊 Performance Reports", "👨‍💼 Admin Control"])

tabs = st.tabs(main_tabs)

# 1. DAILY PROGRAMME (Shift, Time, Date + Carry-Forward)
with tabs[0]:
    st.header("📅 Daily Production Programme")
    prog_df = load_data(PROG_FILE, ["Date", "Shift", "Time", "Machine", "Target_Product", "Target_Qty", "Instructions"])
    prod_logs = load_data(PROD_FILE, ["Date", "Machine", "KM"])
    machines = ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"]
    
    if st.session_state['user_role'] == "Admin":
        # AUTOMATED CARRY FORWARD CHECK
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_prog = prog_df[prog_df['Date'] == yesterday]
        if not y_prog.empty:
            for _, row in y_prog.iterrows():
                done = prod_logs[(prod_logs['Date'] == yesterday) & (prod_logs['Machine'] == row['Machine'])]['KM'].sum()
                pending = row['Target_Qty'] - done
                if pending > 0:
                    st.warning(f"⚠️ {row['Machine']} pending: {pending:.2f} KM from yesterday.")
                    if st.button(f"Carry Forward {row['Machine']} Order"):
                        new_c = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00 AM", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": pending, "Instructions": "PENDING CARRY-FORWARD"}])
                        save_data(pd.concat([prog_df, new_c], ignore_index=True), PROG_FILE); st.rerun()

        with st.expander("📝 Update Machine Schedule"):
            with st.form("prog_form"):
                d_f, s_f, t_f = st.columns(3)
                p_date = d_f.date_input("Plan Date", datetime.now())
                p_shift = s_f.selectbox("Shift", ["Day", "Night"])
                p_time = t_f.text_input("Shift Start Time", "08:00 AM")
                m_sel = st.selectbox("Machine", machines)
                p_spec = st.text_input("Product Specification")
                q_tar = st.number_input("Target Quantity (KM)", min_value=0.0)
                notes = st.text_area("Production Notes")
                if st.form_submit_button("Set Schedule"):
                    prog_df = prog_df[~((prog_df['Machine'] == m_sel) & (prog_df['Date'] == str(p_date)) & (prog_df['Shift'] == p_shift))]
                    new_p = pd.DataFrame([{"Date": str(p_date), "Shift": p_shift, "Time": p_time, "Machine": m_sel, "Target_Product": p_spec, "Target_Qty": q_tar, "Instructions": notes}])
                    save_data(pd.concat([prog_df, new_p], ignore_index=True), PROG_FILE); st.rerun()

    view_d = st.date_input("View Plan For Date:", datetime.now())
    st.table(prog_df[prog_df['Date'] == str(view_d)])

# 2. PRODUCTION ENTRY (Traceability + Stoppage)
with tabs[1]:
    st.header("🏗️ Operator Production Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine Name", machines)
        p_name = st.text_input("Batch/Item Name")
        km_val = st.number_input("Production KM", min_value=0.0)
        st.divider()
        mat = st.selectbox("Raw Material", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum", "Copper", "PVC"])
        cons = st.number_input("Consumed Weight (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Weight (KG)", min_value=0.0)
        stop_desc = st.text_area("Any Machinery Stoppage or Delay Reason?")
        if st.form_submit_button("Submit Daily Report"):
            logs = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state['user_id'], "Machine": m_sel, "Product": p_name, "KM": km_val, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop_desc if stop_desc else "No Delay", "Status": "Pending QCI"}])
            save_data(pd.concat([logs, new_log], ignore_index=True), PROD_FILE)
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= (cons + scrp)
                save_data(stock_df, STOCK_FILE)
            st.success(f"Log recorded by {st.session_state['user_id']}")

# 3. QCI LAB
with tabs[2]:
    st.header("🧪 QCI Batch Testing")
    p_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch to Approve", pending['Product'].unique())
        if st.button("APPROVE & MARK AS PASSED"):
            p_log.loc[p_log['Product'] == batch, 'Status'] = "Ready"
            save_data(p_log, PROD_FILE); st.rerun()

# 4. ORDER BOOK (With New Search Feature)
with tabs[3]:
    st.header("📝 Customer Order Search")
    ob_df = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
    search_q = st.text_input("🔍 Search by Customer Name or Item Type")
    if search_q:
        filtered_ob = ob_df[ob_df['Customer'].str.contains(search_q, case=False) | ob_df['Item'].str.contains(search_q, case=False)]
        st.dataframe(filtered_ob, use_container_width=True)
    else:
        st.dataframe(ob_df, use_container_width=True)

# ADMIN ONLY VIEWS
if st.session_state['user_role'] == "Admin":
    # 5. STOCK
    with tabs[4]:
        st.header("📦 Inventory Levels")
        st.table(load_data(STOCK_FILE, ["Item", "Quantity"]))
    
    # 6. REPORTS (Efficiency + Traceability)
    with tabs[5]:
        st.header("📊 Daily Executive Summary")
        rep_d = st.date_input("Analysis Date", datetime.now())
        d_logs = load_data(PROD_FILE, ["Date", "Operator", "Machine", "KM", "Mat_Consumed", "Scrap", "Stoppage_Info"])
        d_plan = load_data(PROG_FILE, ["Date", "Machine", "Target_Qty"])
        
        day_logs = d_logs[d_logs['Date'] == str(rep_d)]
        if not day_logs.empty:
            # Efficiency Score Calculation
            actuals = day_logs.groupby(['Machine', 'Operator'])['KM'].sum().reset_index()
            targs = d_plan[d_plan['Date'] == str(rep_d)][['Machine', 'Target_Qty']]
            comp = pd.merge(actuals, targs, on='Machine', how='left').fillna(0)
            comp['Efficiency %'] = (comp['KM'] / comp['Target_Qty'] * 100).replace([float('inf')], 0)
            
            st.subheader("Machine Efficiency Scores")
            st.dataframe(comp, use_container_width=True)
            st.subheader("Stoppage & Delay Logs")
            st.table(day_logs[["Operator", "Machine", "Stoppage_Info"]])
        else:
            st.info("No data for this date.")

    # 7. ADMIN CONTROL (Edit & Correction)
    with tabs[6]:
        st.header("👨‍💼 Admin Master Controls")
        with st.expander("🛠️ Stock Correction / Manual Entry"):
            # Same logic as previous version...
            pass
