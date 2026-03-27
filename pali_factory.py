import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP", layout="wide")

# --- FILE PATHS ---
# We use relative paths so it works on both Mac and Cloud
USER_FILE = "users_db.csv"
ORDER_FILE = "production_orders.csv"
PROD_FILE = "production_logs.csv"

# --- STABILIZED DATA LOADING ---
def load_data(filename, cols):
    if os.path.exists(filename):
        try:
            return pd.read_csv(filename)
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- INITIALIZE SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Load Users
users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    users_df = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    save_data(users_df, USER_FILE)

# --- LOGIN SCREEN ---
if not st.session_state['logged_in']:
    st.title("🔐 Pali Cable ERP - Login")
    with st.form("login_form"):
        u_id = st.text_input("User ID")
        u_pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user_match = users_df[(users_df['UserID'] == u_id) & (users_df['Password'] == u_pw)]
            if not user_match.empty:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = user_match.iloc[0]['Role']
                st.session_state['user_id'] = u_id
                st.rerun()
            else:
                st.error("Invalid ID or Password")
    st.stop()

# --- MAIN APP (After Login) ---
st.sidebar.title(f"Welcome, {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["📋 Production Orders", "🏗️ Production & Scrap Entry", "📊 Admin Reports", "👤 User Setup"])

# 1. PRODUCTION ORDERS (Machine Specific)
with tabs[0]:
    st.header("Daily Production Orders")
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Set New Order"):
            m_type = st.selectbox("Select Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
            
            # Machine Specific Columns
            with st.form("machine_spec_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                specs = {}
                if m_type == "RBD":
                    specs = {"Wire": col1.text_input("Wire Size"), "Bobbin": col2.text_input("Bobbin Size"), "Meter": col1.text_input("Meter"), "Grade": col2.text_input("Grade"), "No_of_Bobbin": col1.text_input("No of Bobbin")}
                elif m_type in ["TUBULAR", "19 BOBIN"]:
                    specs = {"Wire": col1.text_input("Wire Size"), "Length": col2.text_input("Length"), "Weight": col1.text_input("Weight"), "OD": col2.text_input("OD")}
                elif m_type == "CORE LAYING":
                    specs = {"Size": col1.text_input("Size"), "Length": col2.text_input("Length")}
                elif m_type == "EXTRUDER":
                    specs = {"Size": col1.text_input("Size"), "OD": col2.text_input("OD"), "Length": col1.text_input("Length"), "Qty": col2.text_input("Quantity")}
                
                if st.form_submit_button("Submit Order"):
                    spec_str = str(specs)
                    new_order = pd.DataFrame([{"Timestamp": datetime.now(), "Machine": m_type, "Details": spec_str}])
                    orders_df = load_data(ORDER_FILE, ["Timestamp", "Machine", "Details"])
                    orders_df = pd.concat([orders_df, new_order], ignore_index=True)
                    save_data(orders_df, ORDER_FILE)
                    st.success("Order Placed!")

    # Show Orders to Everyone
    st.dataframe(load_data(ORDER_FILE, ["Timestamp", "Machine", "Details"]), use_container_width=True)

# 2. PRODUCTION & SCRAP (Operators)
with tabs[1]:
    st.header("Daily Work Entry")
    with st.form("work_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
        c1, c2 = st.columns(2)
        km = c1.number_input("Finished KM", min_value=0.0)
        scrp = c2.number_input("Scrap (KG)", min_value=0.0)
        
        if st.form_submit_button("Submit Work"):
            new_log = pd.DataFrame([{"Date": datetime.now().date(), "Machine": m_sel, "KM": km, "Scrap": scrp, "User": st.session_state['user_id']}])
            logs_df = load_data(PROD_FILE, ["Date", "Machine", "KM", "Scrap", "User"])
            logs_df = pd.concat([logs_df, new_log], ignore_index=True)
            save_data(logs_df, PROD_FILE)
            st.success("Production logged!")

# 3. ADMIN REPORTS
with tabs[2]:
    if st.session_state['user_role'] == "Admin":
        st.header("Factory Reports")
        st.subheader("Production Summary")
        st.dataframe(load_data(PROD_FILE, []))
        st.subheader("Raw Material & Scrap Summary")
        # You can add logic here to sum up the scrap per machine
    else:
        st.warning("Admin Access Only")

# 4. USER SETUP (Admin Only)
with tabs[3]:
    if st.session_state['user_role'] == "Admin":
        st.header("Add New Staff Members")
        with st.form("new_user"):
            new_id = st.text_input("Staff ID")
            new_pw = st.text_input("Staff Password")
            if st.form_submit_button("Create ID"):
                new_u = pd.DataFrame([{"UserID": new_id, "Password": new_pw, "Role": "Operator"}])
                users_df = pd.concat([users_df, new_u], ignore_index=True)
                save_data(users_df, USER_FILE)
                st.success(f"ID Created for {new_id}")
