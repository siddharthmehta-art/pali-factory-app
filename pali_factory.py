import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Tech Specs", layout="wide")

# --- PERMANENT FILE PATHS ---
ORDER_FILE = "machine_orders.csv"
PROD_FILE = "daily_production_logs.csv"
INV_FILE = "raw_material_scrap.csv"

# --- STORAGE FUNCTIONS ---
def save_data(df, filename):
    if not os.path.isfile(filename):
        df.to_csv(filename, index=False)
    else:
        df.to_csv(filename, mode='a', header=False, index=False)

def load_data(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

# --- SIDEBAR & AUTH ---
st.sidebar.title("🏢 Pali Cable & Conductors")
role = st.sidebar.selectbox("Select Role", ["Operator", "Admin (Owner)"])
admin_verified = False
if role == "Admin (Owner)":
    pwd = st.sidebar.text_input("Admin Password", type="password")
    if pwd == "pali123":
        admin_verified = True

# --- MAIN TABS ---
tabs = st.tabs(["📋 Machine Wise Orders", "🏗️ Production Entry", "📦 Raw Material & Scrap", "📊 Admin Reports"])

# 1. DAILY PRODUCTION ORDER (Machine-Specific Inputs)
with tabs[0]:
    st.header("Daily Production Order (Target)")
    
    if admin_verified:
        with st.expander("➕ Create New Order (Admin Only)"):
            with st.form("order_form", clear_on_submit=True):
                m_type = st.selectbox("Select Machine for Order", 
                                    ["RBD", "TUBULAR", "19 BOBIN STRANDING", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
                
                # Dynamic Specification Columns based on Machine Selection
                col1, col2, col3 = st.columns(3)
                
                specs = {}
                with col1:
                    if m_type == "RBD":
                        specs["Wire Size"] = st.text_input("Wire Size")
                        specs["Bobbin Size"] = st.text_input("Bobbin Size")
                    elif m_type in ["TUBULAR", "19 BOBIN STRANDING"]:
                        specs["Wire Size"] = st.text_input("Wire Size")
                        specs["Length"] = st.text_input("Length")
                    elif m_type == "CORE LAYING":
                        specs["Size"] = st.text_input("Size")
                        specs["Length"] = st.text_input("Length")
                    elif m_type in ["EXTRUDER SMALL", "EXTRUDER BIG"]:
                        specs["Size"] = st.text_input("Size")
                        specs["OD"] = st.text_input("OD")
                    else: # Rewinding
                        specs["Size"] = st.text_input("Size")

                with col2:
                    if m_type == "RBD":
                        specs["Meter"] = st.text_input("Meter")
                        specs["Grade"] = st.text_input("Grade")
                    elif m_type in ["TUBULAR", "19 BOBIN STRANDING"]:
                        specs["Weight"] = st.text_input("Weight")
                        specs["OD"] = st.text_input("OD")
                    elif m_type in ["EXTRUDER SMALL", "EXTRUDER BIG"]:
                        specs["Length"] = st.text_input("Length")
                        specs["Quantity"] = st.text_input("Quantity")

                with col3:
                    if m_type == "RBD":
                        specs["No of Bobbin"] = st.text_input("No of Bobbin")
                    delivery_date = st.date_input("Delivery Deadline")

                if st.form_submit_button("Issue Machine Order"):
                    # Combine all specs into a single string for the table
                    spec_summary = " | ".join([f"{k}: {v}" for k, v in specs.items()])
                    new_order = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Machine": m_type,
                        "Technical_Specs": spec_summary,
                        "Deadline": delivery_date
                    }])
                    save_data(new_order, ORDER_FILE)
                    st.success(f"Order for {m_type} sent to floor!")

    # Display Current Orders (Downloadable for everyone)
    order_history = load_data(ORDER_FILE)
    if not order_history.empty:
        st.subheader("Current Floor Orders")
        st.dataframe(order_history, use_container_width=True)
        st.download_button("📥 Download Daily Order Sheet", order_history.to_csv(index=False).encode('utf-8'), "Production_Orders.csv")
    else:
        st.info("No active production orders.")

# 2. PRODUCTION ENTRY (Remains same but saves automatically)
with tabs[1]:
    st.header("Machine Production Entry")
    with st.form("prod_entry", clear_on_submit=True):
        m_sel = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km_done = st.number_input("Output (KM/Units)", min_value=0.0)
        op_name = st.text_input("Operator Name")
        if st.form_submit_button("Submit Work"):
            prod_entry = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Machine": m_sel, "Actual_Output": km_done, "Operator": op_name
            }])
            save_data(prod_entry, PROD_FILE)
            st.success("Log saved!")

# 3. RAW MATERIAL & SCRAP
with tabs[2]:
    st.header("Raw Material & Scrap Update")
    if admin_verified:
        with st.form("inv_form", clear_on_submit=True):
            item = st.selectbox("Material", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire", "Other"])
            stock_change = st.number_input("Stock Movement (KG)", value=0.0)
            scrap_kg = st.number_input("Scrap Generated (KG)", min_value=0.0)
            if st.form_submit_button("Update Stock & Scrap"):
                inv_entry = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Item": item, "Movement": stock_change, "Scrap": scrap_kg
                }])
                save_data(inv_entry, INV_FILE)
                st.success("Inventory records updated!")
    else:
        st.info("Admin login required to update stock/scrap.")

# 4. ADMIN REPORTS
with tabs[3]:
    st.header("📊 Performance Reports")
    if admin_verified:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Production History")
            p_logs = load_data(PROD_FILE)
            st.dataframe(p_logs)
            if not p_logs.empty:
                st.download_button("Download Production Summary", p_logs.to_csv(index=False).encode('utf-8'), "Production_Report.csv")
        
        with col_b:
            st.subheader("Material & Scrap Report")
            i_logs = load_data(INV_FILE)
            st.dataframe(i_logs)
            if not i_logs.empty:
                st.download_button("Download Material Report", i_logs.to_csv(index=False).encode('utf-8'), "Material_Scrap_Report.csv")
    else:
        st.error("Access Restricted")
