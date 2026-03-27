import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- APP CONFIG & STYLING ---
st.set_page_config(page_title="Pali Cable ERP - Master", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- FILE PATHS ---
DB_FILES = {
    "users": "users_db.csv",
    "prod": "production_logs.csv",
    "stock": "stock_inventory.csv",
    "orders": "order_book.csv",
    "prog": "daily_programme.csv"
}

# --- DATA ENGINE (Zero-Flaw Loading) ---
def load_data(key, default_cols):
    filename = DB_FILES[key]
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            # Ensure all required columns exist
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if "Qty" in col or "KM" in col or "Mat" in col else "N/A"
            return df
        except Exception:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, key):
    df.to_csv(DB_FILES[key], index=False)

# --- AUTHENTICATION ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_id': None})

users_df = load_data("users", ["UserID", "Password", "Role"])
if users_df.empty:
    save_data(pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}]), "users")

if not st.session_state['logged_in']:
    st.title("🛡️ Pali Cable ERP - Secure Access")
    with st.container():
        u_id = st.text_input("User ID")
        u_pw = st.text_input("Password", type="password")
        if st.button("Login"):
            match = users_df[(users_df['UserID'] == u_id) & (users_df['Password'] == u_pw)]
            if not match.empty:
                st.session_state.update({'logged_in': True, 'user_role': match.iloc[0]['Role'], 'user_id': u_id})
                st.rerun()
            else:
                st.error("Invalid Credentials")
    st.stop()

# --- HEADER ---
st.sidebar.title(f"Logged in: {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state.update({'logged_in': False})
    st.rerun()

# --- TABS ---
tabs_list = ["📅 Daily Programme", "🏗️ Production", "🧪 QCI Lab", "📝 Orders"]
if st.session_state['user_role'] == "Admin":
    tabs_list.extend(["📦 Inventory", "📊 Analytics"])

tabs = st.tabs(tabs_list)

# 1. DAILY PROGRAMME (Enhanced with Carry-Forward Logic)
with tabs[0]:
    st.header("📅 Production Schedule")
    prog_df = load_data("prog", ["Date", "Shift", "Time", "Machine", "Target_Product", "Target_Qty", "Instructions"])
    prod_logs = load_data("prod", ["Date", "Machine", "KM"])
    
    if st.session_state['user_role'] == "Admin":
        # Automated Carry Forward Check
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_prog = prog_df[prog_df['Date'] == yesterday]
        for _, row in y_prog.iterrows():
            done = prod_logs[(prod_logs['Date'] == yesterday) & (prod_logs['Machine'] == row['Machine'])]['KM'].sum()
            pending = row['Target_Qty'] - done
            if pending > 0:
                st.warning(f"Pending: {row['Machine']} needs {pending:.2f} KM from yesterday.")
                if st.button(f"Carry Forward {row['Machine']}"):
                    new_entry = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00 AM", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": pending, "Instructions": "PENDING ORDER"}])
                    save_data(pd.concat([prog_df, new_entry], ignore_index=True), "prog")
                    st.rerun()

        with st.expander("➕ Set New Schedule"):
            with st.form("prog_entry"):
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Date", datetime.now())
                s = c2.selectbox("Shift", ["Day", "Night"])
                t = c3.text_input("Time", "08:00 AM")
                m = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                prod = st.text_input("Product Name")
                qty = st.number_input("Target KM", min_value=0.1)
                inst = st.text_area("Admin Instructions")
                if st.form_submit_button("Save Plan"):
                    new_p = pd.DataFrame([{"Date": str(d), "Shift": s, "Time": t, "Machine": m, "Target_Product": prod, "Target_Qty": qty, "Instructions": inst}])
                    save_data(pd.concat([prog_df, new_p], ignore_index=True), "prog")
                    st.success("Plan Updated")

    st.subheader("Today's Schedule")
    st.table(prog_df[prog_df['Date'] == datetime.now().strftime("%Y-%m-%d")])

# 2. PRODUCTION ENTRY (Professional Layout)
with tabs[1]:
    st.header("🏗️ Operator Work Entry")
    stock_df = load_data("stock", ["Item", "Quantity"])
    with st.form("work_form", clear_on_submit=True):
        m_sel = st.selectbox("Select Your Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_name = st.text_input("Product Name/Size")
        km_out = st.number_input("Output KM", min_value=0.0)
        st.divider()
        mat = st.selectbox("Material Used", stock_df['Item'].unique() if not stock_df.empty else ["Aluminum", "Copper", "PVC"])
        cons = st.number_input("Consumed KG", min_value=0.0)
        scrp = st.number_input("Scrap Produced KG", min_value=0.0)
        stoppage = st.text_area("Machine Stoppage/Delay Reason (If any)")
        
        if st.form_submit_button("Submit Entry"):
            logs = load_data("prod", ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"])
            new_log = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Operator": st.session_state['user_id'],
                "Machine": m_sel, "Product": p_name, "KM": km_out, 
                "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, 
                "Stoppage_Info": stoppage if stoppage else "None", "Status": "Pending QCI"
            }])
            save_data(pd.concat([logs, new_log], ignore_index=True), "prod")
            # Update Stock
            if mat in stock_df['Item'].values:
                stock_df.loc[stock_df['Item'] == mat, 'Quantity'] -= (cons + scrp)
                save_data(stock_df, "stock")
            st.success("Data Logged Successfully")

# 4. ORDER BOOK (With Pro Search)
with tabs[3]:
    st.header("📝 Customer Orders")
    order_df = load_data("orders", ["Order_ID", "Customer", "Item", "Qty", "Deadline"])
    search = st.text_input("🔍 Search Customer or Product")
    if search:
        st.dataframe(order_df[order_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)], use_container_width=True)
    else:
        st.dataframe(order_df, use_container_width=True)

# 5. ADMIN ANALYTICS (Professional KPI Dashboard)
if st.session_state['user_role'] == "Admin":
    with tabs[5]:
        st.header("📊 Factory Executive Report")
        p_logs = load_data("prod", ["Date", "Operator", "Machine", "KM", "Scrap", "Stoppage_Info"])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Production (KM)", f"{p_logs['KM'].sum():.2f}")
        c2.metric("Total Scrap (KG)", f"{p_logs['Scrap'].sum():.2f}")
        c3.metric("Pending Orders", len(order_df))
        
        st.subheader("Detailed Performance (Operator Traceability)")
        st.dataframe(p_logs, use_container_width=True)
