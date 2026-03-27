import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="Pali Cable ERP Portal", layout="wide", initial_sidebar_state="expanded")

# --- 2. SECURE DATA CORE ---
DB_FILES = {
    "users": "users_db.csv",
    "prod": "production_logs.csv",
    "stock": "stock_inventory.csv",
    "orders": "order_book.csv",
    "prog": "daily_programme.csv",
    "audit": "audit_log.csv"  # NEW: Audit trail for stock changes
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
                if c not in df.columns: df[c] = 0 if any(x in c for x in ["Qty", "KM", "Val"]) else "N/A"
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
    with st.container():
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Secure Login"):
            match = users[(users['UserID'] == u) & (users['Password'] == p)]
            if not match.empty:
                st.session_state.auth = {"logged_in": True, "user": u, "role": match.iloc[0]['Role']}
                st.rerun()
            else: st.error("Authentication Failed")
    st.stop()

# --- 4. NAVIGATION LOGIC (Role-Based Filtering) ---
if st.session_state.auth["role"] == "Admin":
    tab_names = ["📅 Daily Programme", "🏗️ Work Entry", "🧪 QC Lab", "📝 Orders", "📦 Inventory", "📊 BI Analytics", "🕵️ Audit Log"]
else:
    tab_names = ["📅 Daily Programme", "🏗️ Work Entry", "📝 Orders"]

tabs = st.tabs(tab_names)

# --- 5. TAB CONTENT ---

# TAB 1: DAILY PROGRAMME
with tabs[0]:
    st.subheader("Daily Production Schedule")
    prog = get_db("prog")
    prod = get_db("prod")
    
    if st.session_state.auth["role"] == "Admin":
        yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_plan = prog[prog['Date'] == yest]
        for idx, row in y_plan.iterrows():
            actual = prod[(prod['Date'] == yest) & (prod['Machine'] == row['Machine'])]['KM'].sum()
            pending = row['Target_Qty'] - actual
            if pending > 0:
                st.warning(f"⚠️ Machine {row['Machine']} missed target by {pending:.2f} KM")
                if st.button(f"Carry Forward {row['Machine']}", key=f"cf_{idx}"):
                    new_cf = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": pending, "Instructions": "CARRY-FORWARD", "Status": "Open"}])
                    commit_db(pd.concat([prog, new_cf]), "prog")
                    st.rerun()

        with st.expander("➕ Set New Schedule"):
            with st.form("new_schedule"):
                c1, c2, c3 = st.columns(3)
                d_in, s_in, t_in = c1.date_input("Date", datetime.now()), c2.selectbox("Shift", ["Day", "Night"]), c3.text_input("Time", "08:00 AM")
                m_in = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                p_in, q_in = st.text_input("Product Size"), st.number_input("Target KM", min_value=0.0)
                if st.form_submit_button("Publish"):
                    entry = pd.DataFrame([{"Date": str(d_in), "Shift": s_in, "Time": t_in, "Machine": m_in, "Target_Product": p_in, "Target_Qty": q_in, "Instructions": "", "Status": "Open"}])
                    commit_db(pd.concat([prog, entry]), "prog")
                    st.rerun()

    st.dataframe(prog[prog['Date'] == datetime.now().strftime("%Y-%m-%d")], use_container_width=True)

# TAB 2: WORK ENTRY
with tabs[1]:
    st.subheader("Operator Data Entry")
    stock = get_db("stock")
    with st.form("entry_form", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km, mat = st.number_input("Actual KM Produced", min_value=0.0), st.selectbox("Material", stock['Item'].unique() if not stock.empty else ["Aluminum"])
        cons, scrp = st.number_input("Consumed (KG)", min_value=0.0), st.number_input("Scrap (KG)", min_value=0.0)
        stop = st.text_area("Stoppage Reason")
        if st.form_submit_button("Submit"):
            logs = get_db("prod")
            new_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state.auth["user"], "Machine": m_sel, "KM": km, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop, "Status": "QC Pending"}])
            commit_db(pd.concat([logs, new_log]), "prod")
            if mat in stock['Item'].values:
                stock.loc[stock['Item'] == mat, 'Quantity'] -= (cons + scrp)
                commit_db(stock, "stock")
            st.success("Log Submitted.")

# TAB 4: ORDER BOOK
order_idx = tab_names.index("📝 Orders")
with tabs[order_idx]:
    st.subheader("Global Order Search")
    orders = get_db("orders")
    q = st.text_input("Search Orders...")
    st.dataframe(orders[orders.apply(lambda r: q.lower() in str(r).lower(), axis=1)] if q else orders, use_container_width=True)

# ADMIN MODULES (SECURED)
if st.session_state.auth["role"] == "Admin":
    # QC LAB
    with tabs[tab_names.index("🧪 QC Lab")]:
        st.subheader("Quality Control Approvals")
        p_log = get_db("prod")
        pending = p_log[p_log['Status'] == "QC Pending"]
        if not pending.empty:
            batch = st.selectbox("Select Batch", pending['Product'].unique())
            if st.button("Verify & Approve"):
                p_log.loc[p_log['Product'] == batch, 'Status'] = "Approved"
                commit_db(p_log, "prod")
                st.rerun()

    # INVENTORY (With Audit Logging)
    with tabs[tab_names.index("📦 Inventory")]:
        st.subheader("Inventory Management")
        curr_stock = get_db("stock")
        st.table(curr_stock)
        with st.expander("🛠️ Manual Stock Correction"):
            with st.form("stock_fix"):
                item_to_fix = st.selectbox("Item", curr_stock['Item'].unique())
                new_q = st.number_input("Corrected Quantity", min_value=0.0)
                if st.form_submit_button("Update Master Stock"):
                    old_q = curr_stock.loc[curr_stock['Item'] == item_to_fix, 'Quantity'].values[0]
                    curr_stock.loc[curr_stock['Item'] == item_to_fix, 'Quantity'] = new_q
                    commit_db(curr_stock, "stock")
                    # LOG THE AUDIT
                    audits = get_db("audit")
                    log_entry = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Admin": st.session_state.auth["user"], "Item": item_to_fix, "Action": "Manual Correction", "Old_Val": old_q, "New_Val": new_q}])
                    commit_db(pd.concat([audits, log_entry]), "audit")
                    st.success("Stock Updated & Audited.")

    # AUDIT LOG TAB
    with tabs[tab_names.index("🕵️ Audit Log")]:
        st.subheader("System Change History")
        st.dataframe(get_db("audit"), use_container_width=True)

# --- 6. LOGOFF ---
st.sidebar.button("System Logoff", on_click=lambda: st.session_state.update(auth={"logged_in": False}))
