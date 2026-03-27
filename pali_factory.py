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
        if users.empty:
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
today = datetime.now().strftime("%Y-%m-%d")

# --- 5. MODULES ---

# TAB 1: PROGRAMME
with tabs[0]:
    st.subheader("Daily Production Schedule")
    prog = get_db("prog")
    prod = get_db("prod")
    if role == "Admin":
        yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_plan = prog[prog['Date'] == yest]
        for idx, row in y_plan.iterrows():
            done = prod[(prod['Date'] == yest) & (prod['Machine'] == row['Machine'])]['KM'].sum()
            if row['Target_Qty'] > done:
                st.warning(f"Pending: {row['Machine']} missed target by {row['Target_Qty'] - done:.2f} KM")
                if st.button(f"Carry Forward {row['Machine']}", key=f"cf_{idx}"):
                    new_cf = pd.DataFrame([{"Date": today, "Shift": "Day", "Time": "08:00", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": row['Target_Qty'] - done, "Instructions": "CARRY-FORWARD", "Status": "Open"}])
                    commit_db(pd.concat([prog, new_cf]), "prog"); st.rerun()
    st.table(prog[prog['Date'] == today])

# TAB 2: ENTRY
with tabs[1]:
    st.subheader("Production Terminal")
    stk = get_db("stock")
    with st.form("p_form", clear_on_submit=True):
        m = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km = st.number_input("KM Produced", min_value=0, value=0)
        mat = st.selectbox("Material", stk['Item'].unique() if not stk.empty else ["Aluminum"])
        cons = st.number_input("Consumed (KG)", min_value=0, value=0)
        scrp = st.number_input("Scrap (KG)", min_value=0, value=0)
        stop = st.text_area("Stoppage Info")
        if st.form_submit_button("Submit"):
            p_logs = get_db("prod")
            new_log = pd.DataFrame([{"Date": today, "Operator": st.session_state.auth["user"], "Machine": m, "Product": "General", "KM": km, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop, "Status": "QC Pending"}])
            commit_db(pd.concat([p_logs, new_log]), "prod")
            st.success("Reported.")

# TAB 3: QC LAB (ADMIN ONLY)
if role == "Admin":
    with tabs[2]:
        st.subheader("🧪 Quality Control Inspection")
        qc_logs = get_db("prod")
        pending_qc = qc_logs[qc_logs['Status'] == "QC Pending"]
        if not pending_qc.empty:
            st.dataframe(pending_qc, use_container_width=True)
            batch_id = st.selectbox("Select Entry ID to Approve", pending_qc.index)
            if st.button("Approve Batch"):
                qc_logs.at[batch_id, 'Status'] = "Passed"
                commit_db(qc_logs, "prod")
                st.success("Batch Passed")
                st.rerun()
        else:
            st.info("No pending inspections.")

# TAB 4: ORDER BOOK (WITH ADD ORDER FEATURE)
order_idx = 3 if role == "Admin" else 2
with tabs[order_idx]:
    st.subheader("📝 Customer Order Book")
    orders = get_db("orders")
    
    if role == "Admin":
        with st.expander("➕ Add New Customer Order"):
            with st.form("new_order_form", clear_on_submit=True):
                oid = st.text_input("Order ID/No.")
                cust = st.text_input("Customer Name")
                item = st.text_input("Item Specification")
                qty = st.number_input("Order Quantity (KM/Mtrs)", min_value=0, value=0)
                date = st.date_input("Deadline", datetime.now())
                if st.form_submit_button("Save Order"):
                    new_ord = pd.DataFrame([{"Order_ID": oid, "Customer": cust, "Item": item, "Qty": qty, "Deadline": str(date)}])
                    orders = pd.concat([orders, new_ord], ignore_index=True)
                    commit_db(orders, "orders")
                    st.success("Order Added Successfully")
                    st.rerun()

    search_q = st.text_input("Search Customer Name")
    if search_q:
        st.dataframe(orders[orders['Customer'].str.contains(search_q, case=False, na=False)], use_container_width=True)
    else:
        st.dataframe(orders, use_container_width=True)

# TAB 5: INVENTORY (ADMIN ONLY)
if role == "Admin":
    with tabs[4]:
        st.subheader("📦 Raw Material Inventory")
        inv_data = get_db("stock")
        st.table(inv_data)
        with st.expander("Update Stock Manually"):
            with st.form("stk_up"):
                item_name = st.selectbox("Item", inv_data['Item'].unique() if not inv_data.empty else ["Aluminum"])
                new_qty = st.number_input("New Quantity", min_value=0, value=0)
                if st.form_submit_button("Update Stock"):
                    old_qty = inv_data.loc[inv_data['Item'] == item_name, 'Quantity'].values[0] if not inv_data.empty else 0
                    inv_data.loc[inv_data['Item'] == item_name, 'Quantity'] = new_qty
                    commit_db(inv_data, "stock")
                    aud = get_db("audit")
                    log = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Admin": st.session_state.auth["user"], "Item": item_name, "Action": "Correction", "Old_Val": old_qty, "New_Val": new_qty}])
                    commit_db(pd.concat([aud, log]), "audit")
                    st.success("Stock Fixed")
                    st.rerun()

# TAB 6: ANALYTICS
if role == "Admin":
    with tabs[5]:
        st.header("📊 Production Analytics")
        p_logs = get_db("prod")
        p_prog = get_db("prog")
        c1, c2 = st.columns(2)
        c1.metric("Total KM", f"{p_logs['KM'].sum():.1f}")
        c2.metric("Total Scrap", f"{p_logs['Scrap'].sum():.1f} KG")
        act = p_logs.groupby('Machine')['KM'].sum()
        tar = p_prog.groupby('Machine')['Target_Qty'].sum()
        summary = pd.DataFrame({"Actual": act, "Target": tar}).fillna(0)
        summary['Efficiency %'] = (summary['Actual'] / (summary['Target'] + 0.1) * 100).round(1)
        st.dataframe(summary, use_container_width=True)

# TAB 7: AUDIT LOG
if role == "Admin":
    with tabs[6]:
        st.subheader("🕵️ System Audit Trail")
        st.dataframe(get_db("audit"), use_container_width=True)

st.sidebar.button("Logoff", on_click=lambda: st.session_state.update(auth={"logged_in": False}))
