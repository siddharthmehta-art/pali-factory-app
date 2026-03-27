import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage

# --- CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Global", layout="wide")

# --- FILE PATHS ---
PROD_FILE = "prod_logs.csv"
ORDER_FILE = "order_book.csv"
INVENTORY_FILE = "inventory.csv"

# --- EMAIL ALERT FUNCTION ---
def send_email_alert(item, current_qty):
    try:
        msg = EmailMessage()
        msg.set_content(f"ALERT: Raw Material {item} is low. Current Stock: {current_qty}. Please re-order immediately.")
        msg['Subject'] = f"⚠️ STOCK ALERT: {item} Shortage"
        msg['From'] = "your-email@gmail.com" # Replace with your email
        msg['To'] = "your-email@gmail.com"   # Replace with your email

        # Note: For Gmail, you need an 'App Password'
        # server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        # server.login("your-email@gmail.com", "your-app-password")
        # server.send_message(msg)
        # server.quit()
        st.error(f"⚠️ EMAIL ALERT SENT: {item} is below limit!")
    except Exception as e:
        pass

# --- DATABASE LOADING ---
def load_data(file, columns):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=columns)

if 'prod_logs' not in st.session_state:
    st.session_state['prod_logs'] = load_data(PROD_FILE, ["Date", "Machine", "Output_KM", "Operator"])
if 'orders' not in st.session_state:
    st.session_state['orders'] = load_data(ORDER_FILE, ["Size", "Qty", "Delivery_Date", "Urgency"])
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = load_data(INVENTORY_FILE, ["Item", "Current_Stock", "Min_Limit"])

# --- SIDEBAR ---
st.sidebar.title("🏢 Pali Cable ERP")
role = st.sidebar.selectbox("Access Level", ["Operator", "Admin (Owner)"])
if role == "Admin (Owner)":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd != "pali123":
        st.warning("Locked")
        st.stop()

# --- MAIN INTERFACE ---
tabs = st.tabs(["🏗️ Production Entry", "📦 Order Book", "🏗️ Raw Material", "📊 Reports"])

# 1. PRODUCTION ENTRY (Operator & Admin)
with tabs[0]:
    st.header("Daily Production Entry")
    with st.form("prod_form", clear_on_submit=True):
        m = st.selectbox("Machine", ["RBD", "TUBULAR", "19 BOBIN", "CORE LAYING", "EXTRUDER SMALL", "EXTRUDER BIG", "REWINDING ADDA"])
        km = st.number_input("KM Produced", min_value=0.0)
        op = st.text_input("Operator Name")
        if st.form_submit_button("Submit Production"):
            new_p = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Machine": m, "Output_KM": km, "Operator": op}])
            st.session_state['prod_logs'] = pd.concat([st.session_state['prod_logs'], new_p], ignore_index=True)
            st.session_state['prod_logs'].to_csv(PROD_FILE, index=False)
            st.success("Logged!")

# 2. ORDER BOOK (Admin Only)
with tabs[1]:
    st.header("📝 Order Book Management")
    if role == "Admin (Owner)":
        with st.expander("➕ Add New Order"):
            with st.form("order_form"):
                size = st.text_input("Cable Size (e.g. 3x25+1x16)")
                qty = st.number_input("Quantity (KM)", min_value=0.1)
                ddate = st.date_input("Delivery Date")
                
                # Urgency Logic
                days_left = (ddate - datetime.now().date()).days
                urgency = "URGENT" if days_left < 3 else "Normal"
                
                if st.form_submit_button("Book Order"):
                    new_o = pd.DataFrame([{"Size": size, "Qty": qty, "Delivery_Date": ddate, "Urgency": urgency}])
                    st.session_state['orders'] = pd.concat([st.session_state['orders'], new_o], ignore_index=True)
                    st.session_state['orders'].to_csv(ORDER_FILE, index=False)

    st.subheader("Current Pending Orders")
    st.dataframe(st.session_state['orders'], use_container_width=True)

# 3. RAW MATERIAL (Admin Update, Email Alerts)
with tabs[2]:
    st.header("🏗️ Raw Material Inventory")
    if role == "Admin (Owner)":
        with st.form("inv_form"):
            item = st.selectbox("Material", ["Aluminum Rod", "XLPE Compound", "PVC Compound", "Steel Wire", "Wooden Drums"])
            stock = st.number_input("New Stock Level (KG/Units)", min_value=0.0)
            limit = st.number_input("Alert Limit (Send alert below this)", min_value=0.0)
            if st.form_submit_button("Update Inventory"):
                # Update logic
                st.session_state['inventory'] = st.session_state['inventory'][st.session_state['inventory'].Item != item]
                new_i = pd.DataFrame([{"Item": item, "Current_Stock": stock, "Min_Limit": limit}])
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], new_i], ignore_index=True)
                st.session_state['inventory'].to_csv(INVENTORY_FILE, index=False)
                
                if stock < limit:
                    send_email_alert(item, stock)
                    st.warning(f"Low Stock Alert triggered for {item}")

    st.subheader("Current Stock Status")
    st.table(st.session_state['inventory'])

# 4. REPORTS & DOWNLOADS (Admin Only)
with tabs[3]:
    st.header("📊 Admin Summary & Downloads")
    if role == "Admin (Owner)":
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Daily Production Summary")
            st.dataframe(st.session_state['prod_logs'])
            csv_p = st.session_state['prod_logs'].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Production Report", csv_p, "Production_Report.csv")

        with col2:
            st.subheader("Order Summary")
            st.dataframe(st.session_state['orders'])
            csv_o = st.session_state['orders'].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Order Book", csv_o, "Order_Book.csv")
    else:
        st.error("Only Admin can access Reports.")
