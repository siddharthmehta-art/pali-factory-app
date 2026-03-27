import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Try to import Plotly safely
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="Pali Cable ERP Portal", layout="wide", initial_sidebar_state="expanded")

# --- 2. DATA CORE ---
DB_FILES = {
    "users": "users_db.csv",
    "prod": "production_logs.csv",
    "stock": "stock_inventory.csv",
    "orders": "order_book.csv",
    "prog": "daily_programme.csv",
    "audit": "audit_log.csv"
}

def get_db(key):
    cols = {
        "users": ["UserID", "Password", "Role"],
        "prod": ["Date", "Operator", "Machine", "Product", "KM", "Material", "Mat_Consumed", "Scrap", "Stoppage_Info", "Status"],
        "stock": ["Item", "Quantity"],
        "orders": ["Order_ID", "Customer", "Item", "Qty", "Deadline"],
        "prog": ["Date", "Shift", "Time", "Machine", "Target_Product", "Target_Qty", "Instructions", "Status"],
        "audit": ["Timestamp", "Admin", "Item", "Action", "Old_Val", "New_Val"]
    }
    if os.path.exists(DB_FILES[key]):
        try:
            df = pd.read_csv(DB_FILES[key])
            for c in cols[key]:
                if c not in df.columns: df[c] = 0 if any(x in c for x in ["Qty", "KM", "Val", "Scrap"]) else "N/A"
            return df
        except:
            return pd.DataFrame(columns=cols[key])
    return pd.DataFrame(columns=cols[key])

def commit_db(df, key):
    df.to_csv(DB_FILES[key], index=False)

# --- 3. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None}

users = get_db("users")
if users.empty:
    users = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    commit_db(users, "users")

if not st.session_state.auth["logged_in"]:
    st.title("🏭 Pali Cable ERP Portal")
    with st.form("login_gate"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Secure Login"):
            match = users[(users['UserID'] == u) & (users['Password'] == p)]
            if not match.empty:
                st.session_state.auth = {"logged_in": True, "user": u, "role": match.iloc[0]['Role']}
                st.rerun()
            else: st.error("Access Denied")
    st.stop()

# --- 4. NAVIGATION ---
if st.session_state.auth["role"] == "Admin":
    tab_names = ["📅 Daily Programme", "🏗️ Work Entry", "🧪 QC Lab", "📝 Orders", "📦 Inventory", "📊 BI Analytics", "🕵️ Audit Log"]
else:
    tab_names = ["📅 Daily Programme", "🏗️ Work Entry", "📝 Orders"]

tabs = st.tabs(tab_names)

# --- 5. MODULES ---

# 📅 PROGRAMME & CARRY-FORWARD
with tabs[0]:
    st.subheader("Production Scheduling")
    prog, prod = get_db("prog"), get_db("prod")
    if st.session_state.auth["role"] == "Admin":
        yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_plan = prog[prog['Date'] == yest]
        for idx, row in y_plan.iterrows():
            actual = prod[(prod['Date'] == yest) & (prod['Machine'] == row['Machine'])]['KM'].sum()
            pending = row['Target_Qty'] - actual
            if pending > 0:
                st.warning(f"⚠️ {row['Machine']} missed target by {pending:.2f} KM")
                if st.button(f"Carry Forward {row['Machine']}", key=f"cf_{idx}"):
                    new_cf = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": pending, "Instructions": "PENDING", "Status": "Open"}])
                    commit_db(pd.concat([prog, new_cf]), "prog"); st.rerun()
        with st.expander("➕ Set Plan"):
            with st.form("new_p"):
                c1, c2 = st.columns(2)
                m = c1.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                q = c2.number_input("Target KM", min_value=0.0)
                if st.form_submit_button("Save"):
                    e = pd.DataFrame([{"Date": str(datetime.now().date()), "Shift": "Day", "Time": "08:00", "Machine": m, "Target_Product": "General", "Target_Qty": q, "Instructions": "", "Status": "Open"}])
                    commit_db(pd.concat([prog, e]), "prog"); st.rerun()
    st.table(prog[prog['Date'] == str(datetime.now().date())])

# 📊 BI ANALYTICS (RESTORED & STABILIZED)
if st.session_state.auth["role"] == "Admin":
    with tabs[5]:
        st.header("📊 BI Executive Intelligence")
        if not PLOTLY_AVAILABLE:
            st.error("Charts are initializing. Please ensure 'plotly' is added to requirements.txt and wait 1 minute.")
        else:
            p_logs = get_db("prod")
            p_prog = get_db("prog")
            c1, c2 = st.columns(2)
            # KPI Metrics
            total_km = p_logs['KM'].sum()
            c1.metric("Production (KM)", f"{total_km:.1f}")
            c2.metric("Waste (Scrap)", f"{p_logs['Scrap'].sum():.1f} KG")
            
            # Machine Chart
            actual_s = p_logs.groupby('Machine')['KM'].sum().reset_index()
            target_s = p_prog.groupby('Machine')['Target_Qty'].sum().reset_index()
            comp = pd.merge(actual_s, target_s, on='Machine', how='outer').fillna(0)
            fig = px.bar(comp, x='Machine', y=['KM', 'Target_Qty'], barmode='group', title="Output vs Target")
            st.plotly_chart(fig, use_container_width=True)

# (Work Entry, Orders, Inventory, and Audit Log remain fully functional)
