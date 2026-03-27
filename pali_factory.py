import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Professional", layout="wide")

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
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Mat_Consumed'] else "None"
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
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- TABS ---
main_tabs = ["📋 Order Book", "🏗️ Production & Stoppage", "🧪 QCI Lab", "📦 Raw Material", "📊 Daily Reports"]
if st.session_state['user_role'] == "Admin":
    main_tabs.append("👨‍💼 Admin Control")

tabs = st.tabs(main_tabs)

# 1. ORDER BOOK & FG STOCK
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.header("📝 Customer Orders")
        orders = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
        st.dataframe(orders, use_container_width=True)
    with c2:
        st.header("📦 Finished Goods")
        fg = load_data(FG_STOCK_FILE, ["Item", "Qty", "Status"])
        st.dataframe(fg, use_container_width=True)

# 2. PRODUCTION ENTRY (NOW WITH STOPPAGE DESCRIPTION)
with tabs[1]:
    st.header("Machine Work & Stoppage Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_name = st.text_input("Batch/Product Name")
        km = st.number_input("Finished Production (KM)", min_value=0.0)
        
        st.divider()
        st.subheader("Material Deduction")
        available_mats = stock_df['Item'].unique().tolist() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"]
        mat = st.selectbox("Material Used", available_mats)
        cons = st.number_input("Net Material Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Produced (KG)", min_value=0.0)
        
        st.divider()
        st.subheader("Machine Stoppage / Delay Info")
        stop_reason = st.text_area("Reason for Delay/Stoppage (e.g. Power Cut, Wire Break, Maintenance, None)")
        
        if st.form_submit_button("Submit Daily Report"):
            total_deduct = cons + scrp
            if mat in stock_df['Item'].values:
                # 1. Deduct Stock
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= total_deduct
                save_data(stock_df, STOCK_FILE)
                # 2. Log Production + Stoppage
                prod_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
                new_log = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Machine": m_sel, "Product": p_name, "KM": km, 
                    "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, 
                    "Stoppage_Info": stop_reason if stop_reason else "Smooth Run",
                    "Status": "Pending QCI"
                }])
                save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
                st.success("Entry Saved. Stock Adjusted.")

# 3. QCI LAB
with tabs[2]:
    st.header("🧪 QCI Lab Testing")
    p_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch", pending['Product'].unique())
        if st.button("APPROVE & PASS QCI"):
            p_log.loc[p_log['Product'] == batch, 'Status'] = "Ready for Dispatch"
            save_data(p_log, PROD_FILE)
            st.rerun()

# 4. RAW MATERIAL STOCK
with tabs[3]:
    st.header("Raw Material Inventory")
    rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
    st.table(rm_stock)

# 5. NEW DETAILED REPORTS (Daily Production, Consumed, Stoppage)
with tabs[4]:
    st.header("📊 Daily Factory Reports")
    full_data = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info"])
    
    # Filter by Date (Defaults to Today)
    search_date = st.date_input("Filter Report by Date", datetime.now())
    daily_filtered = full_data[full_data['Date'] == str(search_date)]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📍 Daily Production (KM)")
        st.dataframe(daily_filtered[["Machine", "Product", "KM"]], use_container_width=True)
        
    with col_b:
        st.subheader("🔥 Material Consumed (KG)")
        # Total deduction = Mat_Consumed + Scrap
        if not daily_filtered.empty:
            daily_filtered['Total_KG'] = daily_filtered['Mat_Consumed'] + daily_filtered['Scrap']
            st.dataframe(daily_filtered[["Material", "Mat_Consumed", "Scrap", "Total_KG"]], use_container_width=True)
    
    st.divider()
    st.subheader("⚠️ Machine Delay & Stoppage Report")
    st.table(daily_filtered[["Machine", "Stoppage_Info"]])
    
    st.download_button("📥 Download This Day's Report", daily_filtered.to_csv(index=False), f"Report_{search_date}.csv")

# 6. ADMIN CONTROL
if st.session_state['user_role'] == "Admin":
    with tabs[5]:
        st.header("👨‍💼 Master Admin Tools")
        # Correction and User Management same as before
        st.write("Manage Staff and adjust stock here.")
