import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Performance Master", layout="wide")

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
main_tabs = ["📅 Daily Programme", "🏗️ Production Entry", "🧪 QCI Lab", "📝 Order Book"]
if st.session_state['user_role'] == "Admin":
    main_tabs.extend(["📦 Raw Material Stock", "📊 Performance & Efficiency", "👨‍💼 Admin Control"])

tabs = st.tabs(main_tabs)

# 1. DAILY PROGRAMME
with tabs[0]:
    st.header("📅 Production Planning")
    prog_df = load_data(PROG_FILE, ["Date", "Time_Shift", "Machine", "Target_Product", "Target_Qty", "Instructions"])
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("📝 Set New Targets"):
            with st.form("update_prog"):
                p_date = st.date_input("Date", datetime.now())
                p_time = st.selectbox("Shift", ["Day", "Night"])
                m_target = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                p_target = st.text_input("Product Size")
                q_target = st.number_input("Target KM", min_value=0.0)
                instr = st.text_area("Notes")
                if st.form_submit_button("Confirm Plan"):
                    prog_df = prog_df[~((prog_df['Machine'] == m_target) & (prog_df['Date'] == str(p_date)))]
                    new_entry = pd.DataFrame([{"Date": str(p_date), "Time_Shift": p_time, "Machine": m_target, "Target_Product": p_target, "Target_Qty": q_target, "Instructions": instr}])
                    save_data(pd.concat([prog_df, new_entry], ignore_index=True), PROG_FILE); st.rerun()

    view_date = st.date_input("View Plan Date:", datetime.now())
    daily_view = prog_df[prog_df['Date'] == str(view_date)]
    st.table(daily_view)

# 2. PRODUCTION ENTRY
with tabs[1]:
    st.header("Operator Work Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Your Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_name = st.text_input("What was produced?")
        km = st.number_input("Final KM Output", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Weight Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Produced (KG)", min_value=0.0)
        stop_reason = st.text_area("Reason for Stoppage/Delay")
        if st.form_submit_button("Submit Production"):
            prod_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state['user_id'], "Machine": m_sel, "Product": p_name, "KM": km, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop_reason if stop_reason else "Smooth", "Status": "Pending QCI"}])
            save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= (cons + scrp)
                save_data(stock_df, STOCK_FILE)
            st.success("Work Logged!")

# --- ADMIN ONLY TABS ---
if st.session_state['user_role'] == "Admin":
    # 6. PERFORMANCE & EFFICIENCY (The New Scorecard)
    with tabs[5]:
        st.header("📊 Operator Efficiency Scorecard")
        rep_date = st.date_input("Select Date for Scorecard", datetime.now())
        
        # Load both DataFrames
        day_prod = load_data(PROD_FILE, ["Date", "Operator", "Machine", "KM"])
        day_prog = load_data(PROG_FILE, ["Date", "Machine", "Target_Qty"])
        
        # Filter for the selected date
        actuals = day_prod[day_prod['Date'] == str(rep_date)].groupby(['Machine', 'Operator'])['KM'].sum().reset_index()
        targets = day_prog[day_prog['Date'] == str(rep_date)][['Machine', 'Target_Qty']]
        
        if not actuals.empty and not targets.empty:
            # Merge to compare
            comparison = pd.merge(actuals, targets, on='Machine', how='left').fillna(0)
            
            # Calculate Score
            comparison['Efficiency %'] = (comparison['KM'] / comparison['Target_Qty'] * 100).replace([float('inf')], 0).fillna(0)
            
            st.subheader(f"Efficiency Ratings for {rep_date}")
            for index, row in comparison.iterrows():
                col_score, col_details = st.columns([1, 4])
                with col_score:
                    # Color logic for score
                    color = "green" if row['Efficiency %'] >= 90 else "orange" if row['Efficiency %'] >= 70 else "red"
                    st.markdown(f"<h2 style='text-align: center; color: {color};'>{row['Efficiency %']:.1f}%</h2>", unsafe_allow_html=True)
                with col_details:
                    st.write(f"**Operator:** {row['Operator']} | **Machine:** {row['Machine']}")
                    st.write(f"**Target:** {row['Target_Qty']} KM | **Actual:** {row['KM']} KM")
                    st.progress(min(row['Efficiency %']/100, 1.0))
            
            st.divider()
            st.subheader("Raw Data Comparison")
            st.dataframe(comparison, use_container_width=True)
        else:
            st.warning("Ensure both a Programme (Target) and Production (Actual) are entered for this date to see scores.")

    # 7. ADMIN CONTROL (Simplified Correction)
    with tabs[6]:
        st.header("👨‍💼 Master Controls")
        with st.expander("🛠️ Delete Incorrect Production Entry"):
            p_df = load_data(PROD_FILE, [])
            if not p_df.empty:
                del_id = st.selectbox("Select Batch to Remove", p_df['Product'].unique())
                if st.button("Delete Entry Permanently"):
                    p_df = p_df[p_df['Product'] != del_id]
                    save_data(p_df, PROD_FILE); st.rerun()
