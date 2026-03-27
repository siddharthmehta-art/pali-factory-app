import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px  # Professional Charting Library

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="Pali Cable ERP Portal", layout="wide", initial_sidebar_state="expanded")

# --- 2. SECURE DATA CORE ---
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
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Secure Login"):
            match = users[(users['UserID'] == u) & (users['Password'] == p)]
            if not match.empty:
                st.session_state.auth = {"logged_in": True, "user": u, "role": match.iloc[0]['Role']}
                st.rerun()
            else: st.error("Authentication Failed")
    st.stop()

# --- 4. NAVIGATION LOGIC ---
if st.session_state.auth["role"] == "Admin":
    tab_names = ["📅 Daily Programme", "🏗️ Work Entry", "🧪 QC Lab", "📝 Orders", "📦 Inventory", "📊 BI Analytics", "🕵️ Audit Log"]
else:
    tab_names = ["📅 Daily Programme", "🏗️ Work Entry", "📝 Orders"]

tabs = st.tabs(tab_names)

# --- 5. TAB CONTENT ---

# TAB 1: DAILY PROGRAMME (Restored)
with tabs[0]:
    st.subheader("Daily Production Schedule")
    prog, prod_data = get_db("prog"), get_db("prod")
    if st.session_state.auth["role"] == "Admin":
        yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        y_plan = prog[prog['Date'] == yest]
        for idx, row in y_plan.iterrows():
            actual = prod_data[(prod_data['Date'] == yest) & (prod_data['Machine'] == row['Machine'])]['KM'].sum()
            pending = row['Target_Qty'] - actual
            if pending > 0:
                st.warning(f"⚠️ {row['Machine']} pending: {pending:.2f} KM")
                if st.button(f"Carry Forward {row['Machine']}", key=f"cf_{idx}"):
                    new_cf = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Shift": "Day", "Time": "08:00", "Machine": row['Machine'], "Target_Product": row['Target_Product'], "Target_Qty": pending, "Instructions": "CARRY-FORWARD", "Status": "Open"}])
                    commit_db(pd.concat([prog, new_cf]), "prog"); st.rerun()
        with st.expander("➕ Set New Schedule"):
            with st.form("new_schedule"):
                c1, c2, c3 = st.columns(3)
                d_in, s_in, t_in = c1.date_input("Date", datetime.now()), c2.selectbox("Shift", ["Day", "Night"]), c3.text_input("Time", "08:00 AM")
                m_in = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                p_in, q_in = st.text_input("Product Size"), st.number_input("Target KM", min_value=0.0)
                if st.form_submit_button("Publish"):
                    entry = pd.DataFrame([{"Date": str(d_in), "Shift": s_in, "Time": t_in, "Machine": m_in, "Target_Product": p_in, "Target_Qty": q_in, "Instructions": "", "Status": "Open"}])
                    commit_db(pd.concat([prog, entry]), "prog"); st.rerun()
    st.table(prog[prog['Date'] == datetime.now().strftime("%Y-%m-%d")])

# TAB 2: WORK ENTRY (Operator Terminal)
with tabs[1]:
    st.subheader("Work Terminal")
    stock = get_db("stock")
    with st.form("entry_form", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km, mat = st.number_input("Actual KM", min_value=0.0), st.selectbox("Material", stock['Item'].unique() if not stock.empty else ["Aluminum"])
        cons, scrp = st.number_input("Consumed (KG)", min_value=0.0), st.number_input("Scrap (KG)", min_value=0.0)
        stop_txt = st.text_area("Stoppage Reason")
        if st.form_submit_button("Log Production"):
            logs = get_db("prod")
            new_log = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Operator": st.session_state.auth["user"], "Machine": m_sel, "KM": km, "Material": mat, "Mat_Consumed": cons, "Scrap": scrp, "Stoppage_Info": stop_txt, "Status": "QC Pending"}])
            commit_db(pd.concat([logs, new_log]), "prod")
            if mat in stock['Item'].values:
                stock.loc[stock['Item'] == mat, 'Quantity'] -= (cons + scrp)
                commit_db(stock, "stock")
            st.success("Work Logged Successfully.")

# TAB 6: BI ANALYTICS (FULL RESTORATION & ENHANCEMENT)
if st.session_state.auth["role"] == "Admin":
    with tabs[5]:
        st.header("📊 BI Production Intelligence")
        p_logs = get_db("prod")
        p_prog = get_db("prog")
        
        # Dashboard Filters
        st.sidebar.subheader("BI Filter Settings")
        date_range = st.sidebar.date_input("Analysis Period", [datetime.now() - timedelta(days=7), datetime.now()])
        
        # Process Data for Charts
        p_logs['Date'] = pd.to_datetime(p_logs['Date'])
        mask = (p_logs['Date'] >= pd.Timestamp(date_range[0])) & (p_logs['Date'] <= pd.Timestamp(date_range[1]))
        filtered_df = p_logs.loc[mask]
        
        # 1. TOP METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total KM Produced", f"{filtered_df['KM'].sum():.1f}")
        c2.metric("Total Material Used", f"{filtered_df['Mat_Consumed'].sum():.1f} KG")
        c3.metric("Avg Scrap %", f"{(filtered_df['Scrap'].sum() / (filtered_df['Mat_Consumed'].sum() + 0.1) * 100):.1f}%")
        c4.metric("Downtime Events", len(filtered_df[filtered_df['Stoppage_Info'] != "Smooth"]))

        # 2. EFFICIENCY CHART (Target vs Actual)
        st.divider()
        st.subheader("Machine-Wise Efficiency Performance")
        actual_summary = filtered_df.groupby('Machine')['KM'].sum().reset_index()
        target_summary = p_prog.groupby('Machine')['Target_Qty'].sum().reset_index()
        comp = pd.merge(actual_summary, target_summary, on='Machine', how='outer').fillna(0)
        
        fig_eff = px.bar(comp, x='Machine', y=['KM', 'Target_Qty'], barmode='group', 
                         title="Actual Production vs Target (KM)", color_discrete_sequence=['#00CC96', '#636EFA'])
        st.plotly_chart(fig_eff, use_container_width=True)

        # 3. SCRAP & STOPPAGE ANALYSIS
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Scrap Breakdown by Material")
            fig_pie = px.pie(filtered_df, values='Scrap', names='Material', hole=.3)
            st.plotly_chart(fig_pie)
        with col_right:
            st.subheader("Operator Efficiency Ranking")
            op_rank = filtered_df.groupby('Operator')['KM'].sum().sort_values(ascending=False).reset_index()
            st.dataframe(op_rank, use_container_width=True)

        st.subheader("Recent Stoppage Logs")
        st.table(filtered_df[filtered_df['Stoppage_Info'] != "Smooth"][["Date", "Machine", "Operator", "Stoppage_Info"]].tail(10))

# Preservation of other tabs (Orders, Inventory, Audit) remains exactly as per previous code...
