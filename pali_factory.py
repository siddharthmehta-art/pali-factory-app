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
PROG_FILE = "daily_programme.csv" # New: Daily Machine Program

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
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- TABS CONFIGURATION ---
# Programme and Production are visible to all. Reports/Stock moved to Admin.
main_tabs = ["📅 Daily Programme", "🏗️ Production Entry", "🧪 QCI Lab", "📝 Order Book"]
if st.session_state['user_role'] == "Admin":
    main_tabs.extend(["📦 Raw Material Stock", "📊 Admin Reports", "👨‍💼 Admin Control"])

tabs = st.tabs(main_tabs)

# 1. DAILY PROGRAMME (All view, Admin updates)
with tabs[0]:
    st.header("📅 Daily Production Programme")
    prog_df = load_data(PROG_FILE, ["Machine", "Target_Product", "Target_Qty", "Instructions"])
    
    # Machines List
    machines = ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"]
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("📝 Update Machine Programme"):
            with st.form("update_prog"):
                m_target = st.selectbox("Select Machine", machines)
                p_target = st.text_input("Product Size/Type")
                q_target = st.text_input("Target (KM/Units)")
                instr = st.text_area("Specific Instructions")
                if st.form_submit_button("Update Programme"):
                    prog_df = prog_df[prog_df['Machine'] != m_target] # Remove old
                    new_entry = pd.DataFrame([{"Machine": m_target, "Target_Product": p_target, "Target_Qty": q_target, "Instructions": instr}])
                    prog_df = pd.concat([prog_df, new_entry], ignore_index=True)
                    save_data(prog_df, PROG_FILE)
                    st.success(f"Programme updated for {m_target}")
                    st.rerun()
    
    st.table(prog_df if not prog_df.empty else pd.DataFrame(columns=["Machine", "Target_Product", "Target_Qty", "Instructions"]))

# 2. PRODUCTION ENTRY (With Operator Name Tracking)
with tabs[1]:
    st.header("Machine Work Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", machines)
        p_name = st.text_input("Batch/Product Name")
        km = st.number_input("Finished Production (KM)", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Material Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Produced (KG)", min_value=0.0)
        stop_reason = st.text_area("Reason for Delay/Stoppage (Mandatory if any)")
        
        if st.form_submit_button("Submit Daily Report"):
            total_deduct = cons + scrp
            # Log with Operator ID
            prod_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Operator": st.session_state['user_id'], # TRACEABILITY
                "Machine": m_sel, "Product": p_name, "KM": km, 
                "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, 
                "Stoppage_Info": stop_reason if stop_reason else "None", "Status": "Pending QCI"
            }])
            save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
            
            # Stock Deduction
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= total_deduct
                save_data(stock_df, STOCK_FILE)
            st.success(f"Entry Saved by {st.session_state['user_id']}")

# 3. QCI LAB
with tabs[2]:
    st.header("🧪 QCI Lab Testing")
    p_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch", pending['Product'].unique())
        if st.button("APPROVE & PASS QCI"):
            p_log.loc[p_log['Product'] == batch, 'Status'] = "Ready for Dispatch"
            save_data(p_log, PROD_FILE)
            st.rerun()

# 4. ORDER BOOK
with tabs[3]:
    st.header("📝 Customer Orders")
    orders = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
    st.dataframe(orders, use_container_width=True)

# --- ADMIN ONLY TABS ---
if st.session_state['user_role'] == "Admin":
    # 5. RAW MATERIAL (Admin Only)
    with tabs[4]:
        st.header("📦 Raw Material Inventory (Private)")
        rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
        st.table(rm_stock)

    # 6. ADMIN REPORTS (Admin Only)
    with tabs[5]:
        st.header("📊 Detailed Factory Performance")
        full_data = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info"])
        
        search_date = st.date_input("Filter by Date", datetime.now())
        daily_filtered = full_data[full_data['Date'] == str(search_date)].copy()
        
        if not daily_filtered.empty:
            st.subheader(f"Final Production Report - {search_date}")
            # Highlight Operator Name
            st.dataframe(daily_filtered[["Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap"]], use_container_width=True)
            
            st.subheader("⚠️ Machinery Stoppage Log")
            st.table(daily_filtered[["Operator", "Machine", "Stoppage_Info"]])
        else:
            st.info("No data for selected date.")

    # 7. ADMIN CONTROL
    with tabs[6]:
        st.header("👨‍💼 Staff & System Settings")
        with st.expander("👤 Manage Staff Accounts"):
            n_u = st.text_input("New Operator ID")
            n_p = st.text_input("Password")
            if st.button("Save User"):
                u_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
                u_df = pd.concat([u_df, pd.DataFrame([{"UserID": n_u, "Password": n_p, "Role": "Operator"}])], ignore_index=True)
                save_data(u_df, USER_FILE); st.rerun()
