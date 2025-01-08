import streamlit as st
from supabase import create_client
import pandas as pd
from functions import fetch_orders

# Initialize connection to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)


# Set up Streamlit header
st.header("Past Orders")

if st.session_state['role'] == "Customer":
    # Fetch customer_id from session state
    customer_id = st.session_state['id']

    # Query the Supabase orders table for the given customer
    response = supabase.table("orders").select("*").eq("customer_id", customer_id).execute()

    data = response.data
    if data:
        df = pd.DataFrame(data)

        # Convert date_of_purchase to datetime using ISO format
        df['date_of_purchase'] = pd.to_datetime(df['date_of_purchase'], errors='coerce')

        # Format the datetime to a readable string format
        df['date_of_purchase'] = df['date_of_purchase'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Display the dataframe
        st.write(df)
    else:
        st.write("No orders found for this customer.")

elif st.session_state['role'] == "Retailer":
    st.header("Order List")
    orders = fetch_orders()
    if not orders.empty:
        st.dataframe(orders)
    else:
        st.write("No orders found.")
else:
    st.header("Login First")
