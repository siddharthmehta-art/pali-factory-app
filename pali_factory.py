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

# --- DATA LOADING & CLEANING (Fixes the TypeError) ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            # Ensure all columns exist
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Mat_Consumed'] else ""
            
            # CRITICAL FIX: Convert numeric columns and replace errors with 0
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
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- TABS ---
main_tabs = ["📋 Orders", "🏗️ Production & Stoppage", "🧪 QCI Lab", "📦 Raw Material", "📊 Daily Reports"]
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

# 2. PRODUCTION ENTRY
with tabs[1]:
    st.header("Machine Work & Stoppage Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_name = st.text_input("Batch/Product Name")
        km = st.number_input("Finished Production (KM)", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Net Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Produced (KG)", min_value=0.0)
        stop_reason = st.text_area("Reason for Delay/Stoppage (Optional)")
        
        if st.form_submit_button("Submit Daily Report"):
            total_deduct = cons + scrp
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= total_deduct
                save_data(stock_df, STOCK_FILE)
                prod_log = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
                new_log = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Machine": m_sel, "Product": p_name, "KM": km, 
                    "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, 
                    "Stoppage_Info": stop_reason if stop_reason else "None", "Status": "Pending QCI"
                }])
                save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
                st.success("Entry Saved!")

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

# 5. REPORTS (Fixed the TypeError here)
with tabs[4]:
    st.header("📊 Daily Factory Reports")
    full_data = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info"])
    search_date = st.date_input("Filter Report by Date", datetime.now())
    daily_filtered = full_data[full_data['Date'] == str(search_date)].copy()
    
    if daily_filtered.empty:
        st.warning("No data found for this date.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("📍 Daily Production")
            st.dataframe(daily_filtered[["Machine", "Product", "KM"]], use_container_width=True)
            
        with col_b:
            st.subheader("🔥 Material Consumed (KG)")
            # Math is now safe because we forced numeric conversion in load_data
            daily_filtered['Total_KG'] = daily_filtered['Mat_Consumed'] + daily_filtered['Scrap']
            st.dataframe(daily_filtered[["Material", "Mat_Consumed", "Scrap", "Total_KG"]], use_container_width=True)
        
        st.divider()
        st.subheader("⚠️ Machine Delay & Stoppage Report")
        st.table(daily_filtered[["Machine", "Stoppage_Info"]])

# 6. ADMIN CONTROL
if st.session_state['user_role'] == "Admin":
    with tabs[5]:
        st.header("👨‍💼 Master Admin Tools")
        # Manage Staff Account
        with st.expander("👤 Create Operator Account"):
            n_u = st.text_input("New ID")
            n_p = st.text_input("Password")
            if st.button("Save User"):
                u_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
                u_df = pd.concat([u_df, pd.DataFrame([{"UserID": n_u, "Password": n_p, "Role": "Operator"}])], ignore_index=True)
                save_data(u_df, USER_FILE); st.rerun()
