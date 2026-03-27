import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
ORDER_FILE = "production_orders.csv"

# --- DATA LOADING ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = 0 if col in ['Quantity', 'KM', 'Scrap', 'Total_Deduction'] else ""
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    admin_df = pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}])
    save_data(admin_df, USER_FILE)
    users_df = admin_df

if not st.session_state['logged_in']:
    st.title("🔐 Pali Cable ERP - Login")
    with st.form("login"):
        u = st.text_input("User ID")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            match = users_df[(users_df['UserID'] == u) & (users_df['Password'] == p)]
            if not match.empty:
                st.session_state['logged_in'], st.session_state['user_role'], st.session_state['user_id'] = True, match.iloc[0]['Role'], u
                st.rerun()
    st.stop()

# --- SIDEBAR ---
st.sidebar.title(f"User: {st.session_state['user_id']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

tabs = st.tabs(["📋 Daily Production Order", "🏗️ Production & Scrap Entry", "📦 Raw Material Stock", "📊 Reports"])

# 1. DAILY PRODUCTION ORDER (3 COLUMNS ONLY)
with tabs[0]:
    st.header("Daily Production Order")
    order_df = load_data(ORDER_FILE, ["Machine", "Specs", "Quantity", "Order_Date"])
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Create New Order"):
            with st.form("order_form", clear_on_submit=
                         
