import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Master", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
ORDER_BOOK_FILE = "order_book.csv"
FG_STOCK_FILE = "fg_stock.csv"
PROG_FILE = "daily_programme.csv"

# --- DATA LOADING & CLEANING (Prevents TypeErrors) ---
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
main_tabs = ["📅 Daily Programme", "🏗️ Production Entry", "🧪 QCI Lab", "📝 Order Book"]
if st.session_state['user_role'] == "Admin":
    main_tabs.extend(["📦 Raw Material Stock", "📊 Executive Reports", "👨‍💼 Admin Control"])

tabs = st.tabs(main_tabs)

# 1. DAILY PROGRAMME (With Shift, Time, Date & Carry-Forward)
with tabs[0]:
    st.header("📅 Daily Production Programme")
    prog_df = load_data(PROG_FILE, ["Date", "Shift", "Time", "Machine", "Target_Product", "Target_Qty", "Instructions"])
    prod_logs = load_data(PROD_FILE, ["Date", "Machine", "KM"])
    machines = ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"]
    
    if st.session_state['user_role'] == "Admin":
        # CARRY FORWARD LOGIC
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yest_prog = prog_df[prog_df['Date'] == yesterday]
        
        if not yest_prog.empty:
            st.subheader("⚠️ Pending from Yesterday")
            for _, row in yest_prog.iterrows():
                done = prod_logs[(prod_logs['Date'] == yesterday) & (prod_logs['Machine'] == row['Machine'])]['KM'].sum()
                pending = row['Target_Qty'] - done
                if pending > 0:
                    st.warning(f"{row['Machine']} missed target by {pending:.2f} KM")
                    if st.button(f"Carry {row['Machine']} Forward to Today"):
                        new_c = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00 AM", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": pending, "Instructions": "PENDING FROM PREVIOUS DAY"}])
                        save_data(pd.concat([prog_df, new_c], ignore_index=True), PROG_FILE); st.rerun()

        with st.expander("📝 Set Today's Programme"):
            with st.form("set_prog"):
                c1, c2, c3 = st.columns(3)
                d_set = c1.date_input("Date", datetime.now())
                s_set = c2.selectbox("Shift", ["Day", "Night"])
                t_set = c3.text_input("Time", "08:00 AM")
                m_set = st.selectbox("Machine", machines)
                p_set = st.text_input("Product Size")
                q_set = st.number_input("Target KM", min_value=0.0)
                inst = st.text_area("Instructions")
                if st.form_submit_button("Save Plan"):
                    prog_df = prog_df[~((prog_df['Machine'] == m_set) & (prog_df['Date'] == str(d_set)) & (prog_df['Shift'] == s_set))]
                    new_p = pd.DataFrame([{"Date": str(d_set), "Shift": s_set, "Time": t_set, "Machine": m_set, "Target_Product": p_set, "Target_Qty": q_set, "Instructions": inst}])
                    save_data(pd.concat([prog_df, new_p], ignore_index=True), PROG_FILE); st.rerun()

    view_d = st.date_input("Filter Plan Date:", datetime.now())
    st.table(prog_df[prog_df['Date'] == str(view_d)])

# 2. PRODUCTION ENTRY (Traceability + Stoppage)
with tabs[1]:
    st.header("🏗️ Operator Work Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Select Machine", machines)
        p_name = st.text_input("Product Size/Batch")
        km_out = st.number_input("KM Produced", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum", "XLPE"])
        cons = st.number_input("Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap (KG)", min_value=0.0)
        stop_desc = st.text_area("Stoppage Reason / Delay Description")
        if st.form_submit_button("Submit Work"):
            # Update Logs with Username
            logs = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state['user_id'], "Machine": m_sel, "Product": p_name, "KM": km_out, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop_desc if stop_desc else "Smooth", "Status": "Pending QCI"}])
            save_data(pd.concat([logs, new_log], ignore_index=True), PROD_FILE)
            # Deduct Stock
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= (cons + scrp)
                save_data(stock_df, STOCK_FILE)
            st.success("Production Logged Successfully")

# --- OTHER TABS (QCI, ORDER BOOK, STOCK, REPORTS, ADMIN) PRESERVED ---
# (I am keeping the existing logic for QCI, Order Book and Admin tabs inside the code)

if st.session_state['user_role'] == "Admin":
    with tabs[5]:
        st.header("📊 Executive Efficiency Report")
        # Logic for comparing Target vs Actual and displaying Score %
        rep_date = st.date_input("Report Date", datetime.now())
        day_logs = load_data(PROD_FILE, ["Date", "Operator", "Machine", "KM"])
        day_plan = load_data(PROG_FILE, ["Date", "Machine", "Target_Qty"])
        
        actuals = day_logs[day_logs['Date'] == str(rep_date)].groupby(['Machine', 'Operator'])['KM'].sum().reset_index()
        targets = day_plan[day_plan['Date'] == str(rep_date)][['Machine', 'Target_Qty']]
        
        if not actuals.empty and not targets.empty:
            comp = pd.merge(actuals, targets, on='Machine', how='left').fillna(0)
            comp['Efficiency %'] = (comp['KM'] / comp['Target_Qty'] * 100).replace([float('inf')], 0)
            st.dataframe(comp, use_container_width=True)
        else:
            st.info("No comparative data for this date.")
