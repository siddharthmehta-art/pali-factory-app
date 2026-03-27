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
PROG_FILE = "daily_programme.csv" # New: Machine Scheduling

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

# --- TABS (Dynamic based on Role) ---
main_tabs = ["📅 Daily Programme", "🏗️ Production Entry", "🧪 QCI Lab", "📝 Order Book"]
if st.session_state['user_role'] == "Admin":
    main_tabs.extend(["📦 Raw Material Stock", "📊 Admin Reports", "👨‍💼 Admin Control"])

tabs = st.tabs(main_tabs)

# 1. DAILY PROGRAMME (All view, Admin updates)
with tabs[0]:
    st.header("📅 Machine Production Programme")
    prog_df = load_data(PROG_FILE, ["Machine", "Target_Product", "Target_Qty", "Instructions"])
    machines = ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"]
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("📝 Set Today's Programme (Admin Only)"):
            with st.form("update_prog"):
                m_target = st.selectbox("Select Machine", machines)
                p_target = st.text_input("Target Product (Size/Spec)")
                q_target = st.text_input("Target Quantity (KM)")
                instr = st.text_area("Stoppage Prevention / Special Instructions")
                if st.form_submit_button("Update Machine Plan"):
                    prog_df = prog_df[prog_df['Machine'] != m_target] # Replace old plan
                    new_entry = pd.DataFrame([{"Machine": m_target, "Target_Product": p_target, "Target_Qty": q_target, "Instructions": instr}])
                    prog_df = pd.concat([prog_df, new_entry], ignore_index=True)
                    save_data(prog_df, PROG_FILE); st.success(f"Plan Updated for {m_target}"); st.rerun()
    
    st.table(prog_df if not prog_df.empty else pd.DataFrame(columns=["Machine", "Target_Product", "Target_Qty", "Instructions"]))

# 2. PRODUCTION ENTRY (Now with Operator Name)
with tabs[1]:
    st.header("🏗️ Operator Production Entry")
    stock_df = load_data(STOCK_FILE, ["Item", "Quantity"])
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Your Machine", machines)
        p_name = st.text_input("Batch/Product Name")
        km = st.number_input("Finished Production (KM)", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum Rod", "XLPE", "PVC"])
        cons = st.number_input("Net Material Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap Produced (KG)", min_value=0.0)
        stop_reason = st.text_area("Reason for Delay/Stoppage (Mandatory if any)")
        
        if st.form_submit_button("Submit Work Entry"):
            total_deduct = cons + scrp
            # Log with Operator ID
            prod_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Operator": st.session_state['user_id'], # THE OPERATOR'S NAME
                "Machine": m_sel, "Product": p_name, "KM": km, 
                "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, 
                "Stoppage_Info": stop_reason if stop_reason else "None", "Status": "Pending QCI"
            }])
            save_data(pd.concat([prod_log, new_log], ignore_index=True), PROD_FILE)
            
            # Stock Deduction
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= total_deduct
                save_data(stock_df, STOCK_FILE)
            st.success(f"Log submitted by {st.session_state['user_id']}")

# 3. QCI LAB
with tabs[2]:
    st.header("🧪 Quality Control Approval")
    p_log = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Status"])
    pending = p_log[p_log['Status'] == "Pending QCI"]
    if not pending.empty:
        batch = st.selectbox("Select Batch", pending['Product'].unique())
        if st.button("APPROVE & PASS QCI"):
            p_log.loc[p_log['Product'] == batch, 'Status'] = "Passed"
            save_data(p_log, PROD_FILE); st.rerun()

# 4. ORDER BOOK
with tabs[3]:
    st.header("📝 Customer Orders")
    orders = load_data(ORDER_BOOK_FILE, ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
    st.dataframe(orders, use_container_width=True)

# --- ADMIN ONLY SECTIONS ---
if st.session_state['user_role'] == "Admin":
    # 5. RAW MATERIAL (Admin Only)
    with tabs[4]:
        st.header("📦 Raw Material Availability (Private)")
        rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
        st.table(rm_stock)

    # 6. ADMIN REPORTS (Admin Only)
    with tabs[5]:
        st.header("📊 Daily Performance Reports")
        full_data = load_data(PROD_FILE, ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info"])
        
        search_date = st.date_input("Filter by Date", datetime.now())
        daily_filtered = full_data[full_data['Date'] == str(search_date)].copy()
        
        if not daily_filtered.empty:
            st.subheader(f"Final Production & Consumption for {search_date}")
            # Showing Operator Names in the report
            st.dataframe(daily_filtered[["Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap"]], use_container_width=True)
            
            st.subheader("⚠️ Machinery Stoppage Log")
            st.table(daily_filtered[["Operator", "Machine", "Stoppage_Info"]])
        else:
            st.info("No records found for this date.")

    # 7. ADMIN CONTROL (Manage Staff)
    with tabs[6]:
        st.header("👨‍💼 Staff Account Management")
        with st.form("create_staff"):
            n_u = st.text_input("New Operator ID")
            n_p = st.text_input("New Password")
            if st.form_submit_button("Create Account"):
                users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
                new_row = pd.DataFrame([{"UserID": n_u, "Password": n_p, "Role": "Operator"}])
                save_data(pd.concat([users_df, new_row], ignore_index=True), USER_FILE); st.success(f"{n_u} Added")
