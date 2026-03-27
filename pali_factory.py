import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Fixed", layout="wide")

# --- FILE PATHS ---
ORDER_FILE = "production_orders.csv"
PROD_FILE = "production_logs.csv"
MAT_SCRAP_FILE = "material_scrap_logs.csv"

# --- HELPER FUNCTIONS ---
def save_to_csv(df, filename):
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
role = st.sidebar.selectbox("User Role", ["Operator", "Admin (Owner)"])
is_admin = False
if role == "Admin (Owner)":
    pwd = st.sidebar.text_input("Admin Password", type="password")
    if pwd == "pali123":
        is_admin = True

# --- MAIN TABS ---
tabs = st.tabs(["📋 View/Set Orders", "🏗️ Production Entry", "♻️ Raw Material & Scrap", "📊 Admin Reports"])

# 1. DAILY PRODUCTION ORDER (Fixed Machine-Specific Columns)
with tabs[0]:
    st.header("Daily Production Order")
    
    if is_admin:
        with st.expander("➕ Create New Machine Order", expanded=True):
            # Using a unique key for the selectbox to prevent lagging
            m_type = st.selectbox("Select Machine", 
                                ["RBD", "TUBULAR", "19 BOBIN STRANDING", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"],
                                key="admin_m_select")
            
            with st.form("order_form", clear_on_submit=True):
                specs = {}
                col1, col2 = st.columns(2)
                
                # MACHINE SPECIFIC LOGIC
                if m_type == "RBD":
                    with col1:
                        specs["WIRE SIZE"] = st.text_input("Wire Size")
                        specs["BOBIN SIZE"] = st.text_input("Bobin Size")
                        specs["METER"] = st.text_input("Meter")
                    with col2:
                        specs["GRADE"] = st.text_input("Grade")
                        specs["NO OF BOBIN"] = st.text_input("No of Bobin")

                elif m_type in ["TUBULAR", "19 BOBIN STRANDING"]:
                    with col1:
                        specs["WIRE SIZE"] = st.text_input("Wire Size")
                        specs["LENGTH"] = st.text_input("Length")
                    with col2:
                        specs["WEIGHT"] = st.text_input("Weight")
                        specs["OD"] = st.text_input("OD")

                elif m_type == "CORE LAYING":
                    with col1: specs["SIZE"] = st.text_input("Size")
                    with col2: specs["LENGTH"] = st.text_input("Length")

                elif m_type in ["EXTRUDER SMALL", "EXTRUDER BIG"]:
                    with col1:
                        specs["SIZE"] = st.text_input("Size")
                        specs["OD"] = st.text_input("OD")
                    with col2:
                        specs["LENGTH"] = st.text_input("Length")
                        specs["QUANTITY"] = st.text_input("Quantity")
                
                else: # REWINDING
                    specs["SIZE"] = st.text_input("Size")
                    specs["REMARK"] = st.text_input("Remark")

                if st.form_submit_button("Submit Order to Floor"):
                    spec_str = " | ".join([f"{k}: {v}" for k, v in specs.items()])
                    new_order = pd.DataFrame([{
                        "Date_Time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Machine": m_type,
                        "Specifications": spec_str
                    }])
                    save_to_csv(new_order, ORDER_FILE)
                    st.success(f"Order for {m_type} added!")

    # Visible to Operators and Admin
    st.subheader("Current Orders for Floor")
    order_df = load_data(ORDER_FILE)
    if not order_df.empty:
        st.dataframe(order_df, use_container_width=True)
        st.download_button("📥 Download Daily Order List", order_df.to_csv(index=False).encode('utf-8'), "Daily_Orders.csv")

# 2. PRODUCTION ENTRY (Operator Access)
with tabs[1]:
    st.header("Daily Production Output")
    with st.form("prod_form", clear_on_submit=True):
        p_m = st.selectbox("Machine Worked On", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        p_out = st.text_input("Total Output (KM/Units)")
        p_name = st.text_input("Operator Name")
        if st.form_submit_button("Submit Production"):
            p_data = pd.DataFrame([{
                "Date_Time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Machine": p_m, "Output": p_out, "Operator": p_name
            }])
            save_to_csv(p_data, PROD_FILE)
            st.success("Production Logged!")

# 3. RAW MATERIAL & SCRAP (Operator Access as requested)
with tabs[2]:
    st.header("Update Raw Material & Scrap")
    with st.form("mat_form", clear_on_submit=True):
        m_item = st.selectbox("Material Name", ["Aluminum Rod", "XLPE", "PVC", "Steel Wire", "Other"])
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_used = st.number_input("Material Used (KG)", min_value=0.0)
        with col_m2:
            m_scrap = st.number_input("Scrap Produced (KG)", min_value=0.0)
        
        m_op = st.text_input("Updated By (Staff Name)")
        
        if st.form_submit_button("Save Material Entry"):
            m_data = pd.DataFrame([{
                "Date_Time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Material": m_item, "Used_KG": m_used, "Scrap_KG": m_scrap, "Operator": m_op
            }])
            save_to_csv(m_data, MAT_SCRAP_FILE)
            st.success("Material & Scrap data saved!")

# 4. ADMIN REPORTS (Admin Access Only)
with tabs[3]:
    st.header("📊 Factory Reports (Admin Only)")
    if is_admin:
        # Show Production Summary
        st.subheader("Daily Production Log")
        all_prod = load_data(PROD_FILE)
        st.dataframe(all_prod)
        if not all_prod.empty:
            st.download_button("Download Production Summary", all_prod.to_csv(index=False).encode('utf-8'), "Full_Production_Report.csv")

        # Show Material Summary
        st.subheader("Raw Material & Scrap Log")
        all_mat = load_data(MAT_SCRAP_FILE)
        st.dataframe(all_mat)
        if not all_mat.empty:
            st.download_button("Download Material/Scrap Report", all_mat.to_csv(index=False).encode('utf-8'), "Material_Scrap_Report.csv")
    else:
        st.error("Admin Login Required for Reports.")
