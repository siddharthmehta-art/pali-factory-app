import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. CONFIG ---
st.set_page_config(page_title="Pali Cable ERP", layout="wide")

# --- 2. DATA ENGINE ---
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
        df = pd.read_csv(DB_FILES[key])
        for c in cols[key]:
            if c not in df.columns: df[c] = 0 if any(x in c for x in ["Qty", "KM", "Scrap"]) else "N/A"
        return df
    return pd.DataFrame(columns=cols[key])

def commit_db(df, key):
    df.to_csv(DB_FILES[key], index=False)

# --- 3. LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None, "role": None}

if not st.session_state.auth["logged_in"]:
    st.title("🏭 Pali Cable ERP Portal")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        users = get_db("users")
        if users.empty: # Default Admin if file is missing
            users = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
            commit_db(users, "users")
        match = users[(users['UserID'] == u) & (users['Password'] == p)]
        if not match.empty:
            st.session_state.auth = {"logged_in": True, "user": u, "role": match.iloc[0]['Role']}
            st.rerun()
    st.stop()

# --- 4. NAVIGATION ---
role = st.session_state.auth["role"]
if role == "Admin":
    tab_names = ["📅 Programme", "🏗️ Entry", "🧪 QC Lab", "📝 Orders", "📦 Inventory", "📊 Analytics", "🕵️ Audit"]
else:
    tab_names = ["📅 Programme", "🏗️ Entry", "📝 Orders"]

tabs = st.tabs(tab_names)

# --- 5. MODULES ---

# TAB 1: PROGRAMME & CARRY FORWARD
with tabs[0]:
    st.subheader("Daily Production Schedule")
    prog = get_db("prog")
    prod = get_db("prod")
    today = datetime.now().strftime("%Y-%m-%d")
    
    if role == "Admin":
        yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_plan = prog[prog['Date'] == yest]
        for idx, row in y_plan.iterrows():
            done = prod[(prod['Date'] == yest) & (prod['Machine'] == row['Machine'])]['KM'].sum()
            if row['Target_Qty'] > done:
                st.warning(f"Pending: {row['Machine']} missed target by {row['Target_Qty'] - done:.2f} KM")
                if st.button(f"Carry Forward {row['Machine']}", key=f"cf_{idx}"):
                    new_cf = pd.DataFrame([{"Date": today, "Shift": "Day", "Time": "08:00", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": row['Target_Qty'] - done, "Instructions": "PENDING", "Status": "Open"}])
                    commit_db(pd.concat([prog, new_cf]), "prog"); st.rerun()

    st.table(prog[prog['Date'] == today])

# TAB 2: WORK ENTRY
with tabs[1]:
    st.subheader("Production Terminal")
    stk = get_db("stock")
    with st.form("p_form", clear_on_submit=True):
        m = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km = st.number_input("KM Produced", min_value=0.0)
        mat = st.selectbox("Material", stk['Item'].unique() if not stk.empty else ["Aluminum"])
        cons = st.number_input("Consumed (KG)", min_value=0.0)
        scrp = st.number_input("Scrap (KG)", min_value=0.0)
        stop = st.text_area("Stoppage Info")
        if st.form_submit_button("Submit"):
            p_logs = get_db("prod")
            new_log = pd.DataFrame([{"Date": today, "Operator": st.session_state.auth["user"], "Machine": m, "Product": "General", "KM": km, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop, "Status": "QC Pending"}])
            commit_db(pd.concat([p_logs, new_log]), "prod")
            st.success("Reported.")

# TAB 6: ANALYTICS (RESTORED - NO EXTERNAL LIBRARIES)
if role == "Admin":
    with tabs[5]:
        st.header("📊 Production Analytics")
        p_logs = get_db("prod")
        p_prog = get_db("prog")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total KM", f"{p_logs['KM'].sum():.1f}")
        c2.metric("Total Scrap", f"{p_logs['Scrap'].sum():.1f} KG")
        
        st.subheader("Machine-wise Efficiency Summary")
        actual_s = p_logs.groupby('Machine')['KM'].sum()
        target_s = p_prog.groupby('Machine')['Target_Qty'].sum()
        summary = pd.DataFrame({"Actual": actual_s, "Target": target_s}).fillna(0)
        summary['Efficiency %'] = (summary['Actual'] / (summary['Target'] + 0.1) * 100).round(1)
        st.dataframe(summary, use_container_width=True)

# TAB 7: AUDIT LOG
if role == "Admin":
    with tabs[6]:
        st.subheader("System Change History")
        st.dataframe(get_db("audit"), use_container_width=True)

st.sidebar.button("Logoff", on_click=lambda: st.session_state.update(auth={"logged_in": False}))
