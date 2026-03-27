import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Global", layout="wide")

# --- FILE PATHS (Stored on Cloud or Mac) ---
USER_FILE = "users_db.csv"
ORDER_FILE = "production_orders.csv"
PROD_FILE = "production_logs.csv"
INV_FILE = "material_scrap_logs.csv"

# --- CORE FUNCTIONS ---
def save_data(df, filename):
    if not os.path.isfile(filename):
        df.to_csv(filename, index=False)
    else:
        df.to_csv(filename, mode='a', header=False, index=False)

def load_data(filename, cols):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame(columns=cols)

# --- USER MANAGEMENT ---
if 'users' not in st.session_state:
    # Default Admin: ID=admin, Pass=pali123
    st.session_state['users'] = load_data(USER_FILE, ["UserID", "Password", "Role"])
    if st.session_state['users'].empty:
        admin_df = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
        save_data(admin_df, USER_FILE)
        st.session_state['users'] = admin_df

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Pali Cable ERP - Login")
    user_id = st.text_input("User ID")
    user_pass = st.text_input("Password", type="password")
    if st.button("Login"):
        user_db = st.session_state['users']
        match = user_db[(user_db['UserID'] == user_id) & (user_db['Password'] == user_pass)]
        if not match.empty:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = match.iloc[0]['Role']
            st.session_state['user_id'] = user_id
            st.rerun()
        else:
            st.error("Invalid Credentials")
    st.stop()

# --- APP HEADER ---
st.title(f"🏭 Pali Cable ERP - {st.session_state['user_role']} Dashboard")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["📋 Production Orders", "🏗️ Daily Production & Scrap", "📦 Inventory Report", "🛠️ Admin Tools"])

# 1. PRODUCTION ORDERS (Admin Creates, All View/Download)
with tabs[0]:
    st.header("Daily Production Order (Floor Target)")
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Issue Machine-Specific Order"):
            with st.form("order_form", clear_on_submit=True):
                m_type = st.selectbox("Select Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
                
                # FIXED: Dynamic logic to prevent lagging and data mismatch
                col1, col2 = st.columns(2)
                specs = {}
                if m_type == "RBD":
                    specs = {"Wire": col1.text_input("Wire Size"), "Bobbin": col2.text_input("Bobbin Size"), 
                             "Meter": col1.text_input("Meter"), "Grade": col2.text_input("Grade"), "No_of_Bobbin": col1.text_input("No of Bobbin")}
                elif m_type in ["TUBULAR", "19 BOBIN"]:
                    specs = {"Wire": col1.text_input("Wire Size"), "Length": col2.text_input("Length"), 
                             "Weight": col1.text_input("Weight"), "OD": col2.text_input("OD")}
                elif m_type == "CORE LAYING":
                    specs = {"Size": col1.text_input("Size"), "Length": col2.text_input("Length")}
                elif m_type == "EXTRUDER":
                    specs = {"Size": col1.text_input("Size"), "OD": col2.text_input("OD"), 
                             "Length": col1.text_input("Length"), "Qty": col2.text_input("Quantity")}
                
                d_date = st.date_input("Deadline")
                if st.form_submit_button("Submit Order"):
                    spec_str = " | ".join([f"{k}:{v}" for k,v in specs.items()])
                    new_order = pd.DataFrame([{"Timestamp": datetime.now(), "Machine": m_type, "Specs": spec_str, "Deadline": d_date}])
                    save_data(new_order, ORDER_FILE)
                    st.success("Order Created")

    order_data = load_data(ORDER_FILE, ["Timestamp", "Machine", "Specs", "Deadline"])
    st.dataframe(order_data, use_container_width=True)
    st.download_button("📥 Download Orders", order_data.to_csv(index=False), "Orders.csv")

# 2. PRODUCTION & SCRAP ENTRY (Operator & Admin)
with tabs[1]:
    st.header("Daily Production & Scrap Log")
    with st.form("daily_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine Worked On", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER", "REWINDING"])
        c1, c2, c3 = st.columns(3)
        out_km = c1.number_input("Finished KM", min_value=0.0)
        scrap_kg = c2.number_input("Scrap Generated (KG)", min_value=0.0)
        mat_used = c3.selectbox("Material Used", ["Aluminum", "XLPE", "PVC", "Steel"])
        
        if st.form_submit_button("Submit Production & Scrap"):
            entry = pd.DataFrame([{"Timestamp": datetime.now(), "Machine": m_sel, "KM": out_km, 
                                   "Scrap": scrap_kg, "Material": mat_used, "User": st.session_state['user_id']}])
            save_data(entry, PROD_FILE)
            st.success("Saved successfully!")

# 3. INVENTORY REPORT (Admin View Only)
with tabs[2]:
    st.header("📊 Production & Material Summary")
    if st.session_state['user_role'] == "Admin":
        prod_log = load_data(PROD_FILE, [])
        st.dataframe(prod_log)
        st.download_button("📥 Download Summary Report", prod_log.to_csv(index=False), "Production_Report.csv")
    else:
        st.warning("Admin Access Only")

# 4. ADMIN TOOLS (Create User IDs)
with tabs[3]:
    if st.session_state['user_role'] == "Admin":
        st.header("👤 User Management")
        with st.form("user_form"):
            new_id = st.text_input("New Operator ID")
            new_pass = st.text_input("New Password")
            if st.form_submit_button("Create User"):
                new_u = pd.DataFrame([{"UserID": new_id, "Password": new_pass, "Role": "Operator"}])
                save_data(new_u, USER_FILE)
                st.session_state['users'] = load_data(USER_FILE, [])
                st.success(f"User {new_id} Created!")
    else:
        st.error("Admin Only")
