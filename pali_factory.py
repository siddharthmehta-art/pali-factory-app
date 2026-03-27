import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIG ---
st.set_page_config(page_title="Pali Cable ERP Pro", layout="wide")

# --- DATA FILES (Database) ---
ORDERS_FILE = "orders.csv"
RM_FILE = "raw_material.csv"
PROD_FILE = "production.csv"

# --- HELPER FUNCTIONS ---
def load_df(file, columns):
    if os.path.exists(file): return pd.read_csv(file)
    return pd.DataFrame(columns=columns)

def save_df(df, file):
    df.to_csv(file, index=False)

# --- APP STATE ---
if 'orders' not in st.session_state: st.session_state['orders'] = load_df(ORDERS_FILE, ["Date", "Size", "Qty", "Deadline", "Urgency"])
if 'rm_stock' not in st.session_state: st.session_state['rm_stock'] = load_df(RM_FILE, ["Material", "Current_Qty", "Min_Limit"])

# --- UI TABS ---
st.title("🏭 Pali Cable: Full Auto-Mode ERP")
tab1, tab2, tab3, tab4 = st.tabs(["📦 Order Book", "🏗️ Production", "🏗️ Raw Material", "📊 Admin Dashboard"])

# --- 1. ORDER BOOK ---
with tab1:
    st.header("New Order Entry")
    with st.form("order_form"):
        col1, col2 = st.columns(2)
        size = col1.text_input("Cable Size (e.g. 3x25+1x16)")
        qty = col1.number_input("Quantity (KM/Mtrs)", min_value=0.0)
        d_date = col2.date_input("Delivery Date")
        
        # Auto Urgency Logic
        days_left = (d_date - datetime.now().date()).days
        urgency = "URGENT" if days_left < 3 else "Normal"
        
        if st.form_submit_button("Add Order"):
            new_order = pd.DataFrame([{"Date": datetime.now().date(), "Size": size, "Qty": qty, "Deadline": d_date, "Urgency": urgency}])
            st.session_state['orders'] = pd.concat([st.session_state['orders'], new_order], ignore_index=True)
            save_df(st.session_state['orders'], ORDERS_FILE)
            st.success(f"Order Added! Status: {urgency}")

    st.subheader("Current Order Book")
    st.dataframe(st.session_state['orders'])

# --- 2. RAW MATERIAL & ALERTS ---
with tab3:
    st.header("Raw Material Inventory")
    
    # Pre-set materials for your factory
    materials = ["Aluminum Rod (MT)", "XLPE Compound (KG)", "PVC Compound (KG)", "GI Wire (KG)", "Steel Tape (KG)"]
    
    with st.form("rm_update"):
        mat = st.selectbox("Select Material", materials)
        curr = st.number_input("Total Current Stock", min_value=0.0)
        limit = st.number_input("Alert Limit (Minimum Quantity)", min_value=0.0)
        
        if st.form_submit_button("Update Stock"):
            # Update specific row
            st.session_state['rm_stock'] = st.session_state['rm_stock'][st.session_state['rm_stock'].Material != mat]
            new_rm = pd.DataFrame([{"Material": mat, "Current_Qty": curr, "Min_Limit": limit}])
            st.session_state['rm_stock'] = pd.concat([st.session_state['rm_stock'], new_rm], ignore_index=True)
            save_df(st.session_state['rm_stock'], RM_FILE)
            
            # --- ALERT LOGIC ---
            if curr <= limit:
                st.error(f"⚠️ ALERT: {mat} is SHORT! Sending notification...")
                # Here you can integrate Mailgun or Twilio API for Phone/Email
                # For now, it shows a visible warning on the Admin Dashboard
            else:
                st.success("Stock Updated.")

    st.subheader("Live Stock Status")
    def highlight_shortage(s):
        return ['background-color: #ffcccc' if s.Current_Qty <= s.Min_Limit else '' for _ in s]
    
    st.dataframe(st.session_state['rm_stock'].style.apply(highlight_shortage, axis=1))

# --- 3. ADMIN DASHBOARD (Reports) ---
with tab4:
    st.header("Owner's Control Panel")
    # Password Protection
    pwd = st.text_input("Enter Admin Password", type="password")
    if pwd == "pali123":
        st.subheader("Critical Alerts")
        short_items = st.session_state['rm_stock'][st.session_state['rm_stock'].Current_Qty <= st.session_state['rm_stock'].Min_Limit]
        if not short_items.empty:
            for _, row in short_items.iterrows():
                st.warning(f"ORDER IMMEDIATELY: {row['Material']} is only {row['Current_Qty']} left!")
        else:
            st.success("All Raw Materials are in safe quantities.")
