import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP", layout="wide")

# --- AUTO-SAVE FILE PATHS ---
PROD_FILE = "factory_production_logs.csv"
ORDER_FILE = "production_orders.csv"
INV_FILE = "inventory_scrap_report.csv"

# --- HELPER FUNCTIONS FOR PERMANENT STORAGE ---
def save_to_file(df, filename):
    # If file exists, append without header. If not, create with header.
    if not os.path.isfile(filename):
        df.to_csv(filename, index=False)
    else:
        df.to_csv(filename, mode='a', header=False, index=False)

def load_data(filename, cols):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame(columns=cols)

# --- INITIALIZE DATA ---
if 'orders' not in st.session_state:
    st.session_state['orders'] = load_data(ORDER_FILE, ["Timestamp", "Machine", "Size", "Target_KM", "Delivery_Date", "Urgency"])

# --- SIDEBAR & AUTH ---
st.sidebar.title("🏢 Pali Cable & Conductors")
role = st.sidebar.selectbox("Access Level", ["Operator", "Admin (Owner)"])
admin_verified = False
if role == "Admin (Owner)":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == "pali123":
        admin_verified = True
    else:
        st.sidebar.warning("Enter password for Admin tools")

# --- MAIN TABS ---
tabs = st.tabs(["📋 Daily Production Order", "🏗️ Machine Entry", "📦 Raw Material & Scrap", "📊 Admin Reports"])

# 1. DAILY PRODUCTION ORDER (Visible & Downloadable by ALL)
with tabs[0]:
    st.header("Daily Production Order (Target)")
    if admin_verified:
        with st.expander("➕ Set New Production Order (Admin Only)"):
            with st.form("order_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    m_order = st.selectbox("Assign Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                    size_order = st.text_input("Cable Size")
                with col2:
                    qty_order = st.number_input("Target KM", min_value=0.0)
                    d_date = st.date_input("Deadline")
                
                if st.form_submit_button("Issue Order"):
                    new_order = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Machine": m_order, "Size": size_order, "Target_KM": qty_order, 
                        "Delivery_Date": d_date, "Urgency": "Urgent" if (d_date - datetime.now().date()).days < 2 else "Normal"
                    }])
                    save_to_file(new_order, ORDER_FILE)
                    st.session_state['orders'] = load_data(ORDER_FILE, []) # Refresh
                    st.success("Order Issued!")

    # Visible to everyone
    current_orders = load_data(ORDER_FILE, ["Timestamp", "Machine", "Size", "Target_KM", "Delivery_Date", "Urgency"])
    st.dataframe(current_orders, use_container_width=True)
    
    # Operators can download this
    csv_order = current_orders.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Order Sheet (For Operators)", csv_order, f"Production_Orders_{datetime.now().date()}.csv")

# 2. MACHINE ENTRY (Operators log their work here)
with tabs[1]:
    st.header("Operator Production Entry")
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Your Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km_done = st.number_input("Finished KM", min_value=0.0)
        op_name = st.text_input("Your Name")
        
        if st.form_submit_button("Submit Production"):
            prod_data = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Machine": m_sel, "Actual_KM": km_done, "Operator": op_name
            }])
            save_to_file(prod_data, PROD_FILE)
            st.success("Production saved to permanent logs!")

# 3. RAW MATERIAL & SCRAP (Admin Updates)
with tabs[2]:
    st.header("Raw Material & Scrap Management")
    if admin_verified:
        with st.form("inv_form", clear_on_submit=True):
            mat_item = st.selectbox("Material Name", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire"])
            col_a, col_b = st.columns(2)
            with col_a:
                stock_update = st.number_input("Stock Received/Used (KG)", value=0.0)
            with col_b:
                scrap_update = st.number_input("Scrap Generated (KG)", min_value=0.0)
            
            if st.form_submit_button("Update Inventory & Scrap"):
                inv_data = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Item": mat_item, "Stock_Movement": stock_update, "Scrap_KG": scrap_update
                }])
                save_to_file(inv_data, INV_FILE)
                st.success("Inventory and Scrap logs updated!")
    else:
        st.info("Log in as Admin to update Stock and Scrap levels.")

# 4. ADMIN REPORTS (Download Center)
with tabs[3]:
    st.header("📊 Factory Performance Reports")
    if admin_verified:
        # Production Report
        st.subheader("1. All-Time Production Log")
        p_df = load_data(PROD_FILE, [])
        st.dataframe(p_df)
        st.download_button("📥 Download Production Report", p_df.to_csv(index=False).encode('utf-8'), "Full_Production_Report.csv")

        # Inventory & Scrap Report
        st.subheader("2. Inventory & Scrap Log")
        i_df = load_data(INV_FILE, [])
        st.dataframe(i_df)
        st.download_button("📥 Download Raw Material & Scrap Report", i_df.to_csv(index=False).encode('utf-8'), "Material_Scrap_Report.csv")
    else:
        st.error("Admin Access Required")
