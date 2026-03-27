from streamlit_gsheets import GSheetsConnection

# Create connection to your Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# To Read Data
existing_data = conn.read(worksheet="Sheet1")

# To Save Data (Add this inside your 'Submit' button code)
conn.update(worksheet="Sheet1", data=updated_df)
import streamlit as st
import pandas as pd
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cables - ERP", layout="wide")

# --- TITLES ---
st.title("🔌 Pali Cable & Conductors: Digital Control")
st.markdown("---")

# --- DATABASE SETUP (Local Memory) ---
# In a professional setup, we would link this to a CSV or SQL database
if 'production_logs' not in st.session_state:
    st.session_state['production_logs'] = pd.DataFrame(columns=[
        "Timestamp", "Machine", "Production_KM", "Staff_Name", "Status"
    ])

if 'daily_program' not in st.session_state:
    st.session_state['daily_program'] = {
        "RBD": "No Task", "TUBULAR": "No Task", "19 BOBIN": "No Task",
        "CORE LAYING": "No Task", "EXTRUDER SMALL": "No Task",
        "EXTRUDER BIG": "No Task", "REWINDING ADDA": "No Task"
    }

# --- SIDEBAR - LOGIN SYSTEM ---
st.sidebar.header("🔐 Access Control")
user_role = st.sidebar.selectbox("Select Role", ["Staff / Operator", "Admin (Owner)"])

if user_role == "Admin (Owner)":
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    if password != "pali123": # SET YOUR PASSWORD HERE
        st.error("Invalid Admin Password")
        st.stop()
    st.sidebar.success("Admin Verified")

# --- TAB SYSTEM ---
tab1, tab2, tab3 = st.tabs(["📋 Daily Program", "🏗️ Production Entry", "📊 Daily Report"])

# --- TAB 1: DAILY PROGRAM (Only Admin can Update) ---
with tab1:
    st.header("Today's Production Targets")
    if user_role == "Admin (Owner)":
        st.subheader("Set Tasks for Machines")
        cols = st.columns(2)
        machines = list(st.session_state['daily_program'].keys())
        
        for i, m in enumerate(machines):
            with cols[i % 2]:
                new_task = st.text_input(f"Target for {m}:", st.session_state['daily_program'][m])
                st.session_state['daily_program'][m] = new_task
        st.success("Program Updated for All Staff!")
    else:
        # Staff View
        st.info("Check your targets below assigned by Admin.")
        for m, task in st.session_state['daily_program'].items():
            st.write(f"**{m}:** {task}")

# --- TAB 2: PRODUCTION ENTRY (Staff Entry) ---
with tab2:
    st.header("Staff Production Entry")
    with st.form("staff_entry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_machine = st.selectbox("Select Machine", [
                "RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", 
                "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"
            ])
            staff_name = st.text_input("Operator Name")
        with col2:
            prod_km = st.number_input("Production Finished (KM)", min_value=0.0)
            status = st.selectbox("Machine Status", ["Running Smooth", "Maintenance Needed", "Power Issue"])
        
        if st.form_submit_button("Submit Entry"):
            new_data = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Machine": selected_machine,
                "Production_KM": prod_km,
                "Staff_Name": staff_name,
                "Status": status
            }
            st.session_state['production_logs'] = pd.concat([
                st.session_state['production_logs'], pd.DataFrame([new_data])
            ], ignore_index=True)
            st.balloons()
            st.success("Production Logged!")

# --- TAB 3: DAILY REPORT (Admin Only View) ---
with tab3:
    st.header("Daily Production Report")
    if user_role == "Admin (Owner)":
        df = st.session_state['production_logs']
        if not df.empty:
            # Summary Metrics
            total_km = df["Production_KM"].sum()
            st.metric("Total Factory Output Today", f"{total_km} KM")
            
            # Machine-wise breakdown
            st.subheader("Breakdown by Machine")
            machine_summary = df.groupby("Machine")["Production_KM"].sum()
            st.bar_chart(machine_summary)
            
            st.subheader("Full Log Table")
            st.dataframe(df, use_container_width=True)
            
            # CSV Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Full Report", csv, "Pali_Daily_Report.csv", "text/csv")
        else:
            st.warning("No data submitted by staff yet.")
    else:
        st.warning("Only Admin can view the Daily Reports.")
