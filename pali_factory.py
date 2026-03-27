import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. SYSTEM CONFIGURATION (SAP UI Style) ---
st.set_page_config(page_title="Pali Cable ERP Portal", layout="wide", initial_sidebar_state="expanded")

# Professional CSS for a Clean Corporate Look
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { border: 1px solid #d1d8e0; padding: 10px; border-radius: 8px; background: white; }
    .stAlert { border-radius: 8px; }
    div[data-baseweb="tab-list"] { gap: 8px; }
    div[data-baseweb="tab"] { 
        background-color: #e4e7eb; border-radius: 4px 4px 0 0; padding: 10px 20px;
    }
    div[data-baseweb="tab"][aria-selected="true"] { 
        background-color: #004a99; color: white; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SECURE DATA CORE ---
DB_FILES = {
    "users": "users_db.csv",
    "prod": "production_logs.csv",
    "stock": "stock_inventory.csv",
    "orders": "order_book.csv",
    "prog": "daily_programme.csv"
}

def get_db(key):
    cols = {
        "users": ["UserID", "Password", "Role"],
        "prod": ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"],
        "stock": ["Item", "Quantity"],
        "orders": ["Order_ID", "Customer", "Item", "Qty", "Deadline"],
        "prog": ["Date", "Shift", "Time", "Machine", "Target_Product", "Target_Qty", "Instructions", "Status"]
    }
    if os.path.exists(DB_FILES[key]):
        df = pd.read_csv(DB_FILES[key])
        # Auto-fix missing columns
        for c in cols[key]:
            if c not in df.columns: df[c] = 0 if "Qty" in c or "KM" in c else "N/A"
        return df
    return pd.DataFrame(columns=cols[key])

def commit_db(df, key):
    df.to_csv(DB_FILES[key], index=False)

# --- 3. AUTHENTICATION (The Security Gate) ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None}

users = get_db("users")
if users.empty:
    users = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    commit_db(users, "users")

if not st.session_state.auth["logged_in"]:
    st.title("🏭 Pali Cable ERP Portal")
    with st.container():
        c1, c2 = st.columns([1, 2])
        with c1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Secure Login"):
                match = users[(users['UserID'] == u) & (users['Password'] == p)]
                if not match.empty:
                    st.session_state.auth = {"logged_in": True, "user": u, "role": match.iloc[0]['Role']}
                    st.rerun()
                else: st.error("Authentication Failed")
    st.stop()

# --- 4. NAVIGATION ---
st.sidebar.image("https://img.icons8.com/fluency/96/factory.png", width=80)
st.sidebar.title(f"Portal: {st.session_state.auth['user']}")
st.sidebar.info(f"Role: {st.session_state.auth['role']}")

if st.sidebar.button("Logoff System"):
    st.session_state.auth = {"logged_in": False, "user": None, "role": None}
    st.rerun()

# --- 5. FUNCTIONAL MODULES ---
tabs = st.tabs(["📅 Daily Programme", "🏗️ Work Entry", "🧪 QC Lab", "📝 Orders", "📦 Inventory", "📊 BI Analytics"])

# MODULE 1: DAILY PROGRAMME & CARRY-FORWARD
with tabs[0]:
    st.subheader("Production Scheduling & Carry-Forward")
    prog = get_db("prog")
    prod = get_db("prod")
    
    if st.session_state.auth["role"] == "Admin":
        # Professional Carry Forward Logic
        yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_plan = prog[prog['Date'] == yest]
        for idx, row in y_plan.iterrows():
            actual = prod[(prod['Date'] == yest) & (prod['Machine'] == row['Machine'])]['KM'].sum()
            pending = row['Target_Qty'] - actual
            if pending > 0:
                st.warning(f"⚠️ PENDING: Machine {row['Machine']} missed target by {pending:.2f} KM")
                if st.button(f"Carry Forward {row['Machine']} to Today", key=f"cf_{idx}"):
                    new_cf = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00",
                        "Machine": row['Machine'], "Target_Product": row['Target_Product'],
                        "Target_Qty": pending, "Instructions": "SYSTEM CARRY-FORWARD", "Status": "Open"
                    }])
                    commit_db(pd.concat([prog, new_cf]), "prog")
                    st.rerun()

        with st.expander("➕ Create New Schedule"):
            with st.form("new_schedule"):
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("Date", datetime.now())
                s = c2.selectbox("Shift", ["Day", "Night"])
                t = c3.text_input("Start Time", "08:00 AM")
                m = st.selectbox("Select Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                prod_name = st.text_input("Product Specification")
                t_qty = st.number_input("Target Quantity (KM)", min_value=0.0)
                note = st.text_area("Admin Notes")
                if st.form_submit_button("Post to Schedule"):
                    entry = pd.DataFrame([{"Date": str(d), "Shift": s, "Time": t, "Machine": m, "Target_Product": prod_name, "Target_Qty": t_qty, "Instructions": note, "Status": "Open"}])
                    commit_db(pd.concat([prog, entry]), "prog")
                    st.success("Programme Published")

    st.dataframe(prog[prog['Date'] == datetime.now().strftime("%Y-%m-%d")], use_container_width=True)

# MODULE 2: WORK ENTRY (Operator Traceability)
with tabs[1]:
    st.subheader("Operator Data Terminal")
    stock = get_db("stock")
    with st.form("op_entry", clear_on_submit=True):
        m_sel = st.selectbox("Assigned Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_spec = st.text_input("Product Size/Batch")
        km = st.number_input("Actual KM Produced", min_value=0.0)
        st.divider()
        mat = st.selectbox("Primary Material", stock['Item'].unique() if not stock.empty else ["Aluminum", "Copper", "PVC"])
        c_kg = st.number_input("Consumed (KG)", min_value=0.0)
        s_kg = st.number_input("Scrap (KG)", min_value=0.0)
        delay = st.text_area("Reason for Machine Idle/Delay")
        if st.form_submit_button("Submit Production Data"):
            logs = get_db("prod")
            new_log = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state.auth["user"],
                "Machine": m_sel, "Product": p_spec, "KM": km, "Material": mat, 
                "Mat_Consumed": c_kg, "Scrap": s_kg, "Stoppage_Info": delay if delay else "Smooth", "Status": "QC Pending"
            }])
            commit_db(pd.concat([logs, new_log]), "prod")
            # Stock Logic
            if mat in stock['Item'].values:
                stock.loc[stock['Item'] == mat, 'Quantity'] -= (c_kg + s_kg)
                commit_db(stock, "stock")
            st.success("Entry Saved and Traceable to User.")

# MODULE 4: ORDER BOOK (Searchable Grid)
with tabs[3]:
    st.subheader("Global Order Search")
    orders = get_db("orders")
    search = st.text_input("🔎 Search by Customer or Item...")
    if search:
        st.dataframe(orders[orders.apply(lambda r: search.lower() in str(r).lower(), axis=1)], use_container_width=True)
    else:
        st.dataframe(orders, use_container_width=True)

# MODULE 6: BI ANALYTICS (Admin Only)
with tabs[5]:
    if st.session_state.auth["role"] != "Admin":
        st.error("Access Restricted to Management Only.")
    else:
        st.subheader("Executive KPI Dashboard")
        d_logs = get_db("prod")
        d_prog = get_db("prog")
        
        c1, c2, c3, c4 = st.columns(4)
        total_km = d_logs['KM'].sum()
        total_scrp = d_logs['Scrap'].sum()
        efficiency = (total_km / d_prog['Target_Qty'].sum() * 100) if d_prog['Target_Qty'].sum() > 0 else 0
        
        c1.metric("Gross Production", f"{total_km:.1f} KM")
        c2.metric("Waste (Scrap)", f"{total_scrp:.1f} KG")
        c3.metric("Plant Efficiency", f"{efficiency:.1f}%")
        c4.metric("Active Operators", d_logs['Operator'].nunique())
        
        st.subheader("Operator Efficiency Scorecard")
        st.dataframe(d_logs[["Date", "Operator", "Machine", "KM", "Stoppage_Info"]], use_container_width=True)
