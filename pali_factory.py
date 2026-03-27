import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Pali Cable ERP - Tech QCI", layout="wide")

# --- FILE PATHS ---
USER_FILE = "users_db.csv"
PROD_FILE = "production_logs.csv"
STOCK_FILE = "stock_inventory.csv"
ORDER_BOOK_FILE = "order_book.csv"
FIN_GOODS_FILE = "finished_goods_stock.csv"

# --- DATA LOADING ---
def load_data(filename, default_cols):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            for col in default_cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_data(df, filename):
    df.to_csv(filename, index=False)

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

users_df = load_data(USER_FILE, ["UserID", "Password", "Role"])
if users_df.empty:
    save_data(pd.DataFrame([{"UserID": "admin", "Password": "pali123", "Role": "Admin"}]), USER_FILE)

if not st.session_state['logged_in']:
    st.title("🔐 Pali Cable ERP - Login")
    with st.form("login"):
        u, p = st.text_input("User ID"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            match = users_df[(users_df['UserID'] == u) & (users_df['Password'] == p)]
            if not match.empty:
                st.session_state.update({"logged_in": True, "user_role": match.iloc[0]['Role'], "user_id": u})
                st.rerun()
    st.stop()

# --- TABS ---
tabs = st.tabs(["📝 Order Book", "🏗️ Production Entry", "📦 Raw Material", "🧪 QCI & Dispatch", "📊 Reports"])

# 1. ORDER BOOK & MANUAL FINISHED GOODS
with tabs[0]:
    st.header("Order Book Management")
    orders = load_data(ORDER_BOOK_FILE, ["Customer", "Item", "Quantity", "Delivery_Date", "Status"])
    
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Add New Customer Order"):
            with st.form("new_order"):
                cust = st.text_input("Customer Name")
                item = st.text_input("Item Description")
                qty = st.number_input("Order Quantity (KM/Mtrs)", min_value=0.0)
                d_date = st.date_input("Delivery Date")
                if st.form_submit_button("Book Order"):
                    new_o = pd.DataFrame([{"Customer": cust, "Item": item, "Quantity": qty, "Delivery_Date": d_date, "Status": "Pending"}])
                    save_data(pd.concat([orders, new_o], ignore_index=True), ORDER_BOOK_FILE)
                    st.rerun()
    
    st.subheader("Current Order Book")
    st.dataframe(orders, use_container_width=True)

    st.divider()
    st.header("📦 Finished Goods Stock (In-House)")
    fg_stock = load_data(FIN_GOODS_FILE, ["Item", "Quantity", "Location"])
    if st.session_state['user_role'] == "Admin":
        with st.expander("➕ Manually Add Finished Goods to Stock"):
            with st.form("fg_form"):
                fg_item = st.text_input("Finished Item Name")
                fg_qty = st.number_input("Quantity in Stock", min_value=0.0)
                fg_loc = st.text_input("Storage Location (e.g. Godown A)")
                if st.form_submit_button("Add to FG Stock"):
                    new_fg = pd.DataFrame([{"Item": fg_item, "Quantity": fg_qty, "Location": fg_loc}])
                    save_data(pd.concat([fg_stock, new_fg], ignore_index=True), FIN_GOODS_FILE)
                    st.rerun()
    st.table(fg_stock)

# 2. PRODUCTION ENTRY (Remains same for machine tracking)
with tabs[1]:
    st.header("Daily Machine Production")
    # ... (Previous production entry code remains here for machine-wise tracking)

# 3. RAW MATERIAL STOCK
with tabs[2]:
    st.header("Raw Material Inventory")
    rm_stock = load_data(STOCK_FILE, ["Item", "Quantity"])
    st.table(rm_stock)

# 4. QCI TESTING & DISPATCH
with tabs[3]:
    st.header("🧪 Quality Control Inspection (QCI)")
    prod_logs = load_data(PROD_FILE, ["Date", "Machine", "Product", "KM", "Status"])
    pending = prod_logs[prod_logs['Status'] != "Passed QCI"]

    if not pending.empty:
        with st.form("qci_technical_test"):
            target_batch = st.selectbox("Select Batch for Testing", pending['Product'].unique())
            st.subheader("Technical Test Checklist")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Insulation Tests (PVC/XLPE)**")
                t_tensile = st.checkbox("Tensile Strength Test")
                t_hotset = st.checkbox("Hot Set Test")
                t_elongation = st.checkbox("Elongation Test")
            with c2:
                st.markdown("**Conductor Tests (Al/Cu)**")
                t_cr = st.checkbox("Conductor Resistance (CR) Test")
                t_breaking = st.checkbox("Breaking Load Test")
            
            qc_remarks = st.text_area("QC Inspector Remarks")
            
            if st.form_submit_button("Verify & Approve for Ready Stock"):
                if all([t_tensile, t_hotset, t_elongation, t_cr, t_breaking]):
                    prod_logs.loc[prod_logs['Product'] == target_batch, 'Status'] = "Passed QCI"
                    save_data(prod_logs, PROD_FILE)
                    
                    # Automatically add passed item to Finished Goods Stock
                    new_ready = pd.DataFrame([{"Item": target_batch, "Quantity": "From Prod", "Location": "Ready Bay"}])
                    save_data(pd.concat([fg_stock, new_ready], ignore_index=True), FIN_GOODS_FILE)
                    
                    st.success(f"BATCH {target_batch} PASSED ALL TESTS. Moved to Ready Stock.")
                else:
                    st.error("Cannot Pass: One or more technical tests failed.")
    else:
        st.info("No items pending QCI.")

# 5. REPORTS
with tabs[4]:
    st.header("Factory Performance Reports")
    # ... (Download and visualization logic)
