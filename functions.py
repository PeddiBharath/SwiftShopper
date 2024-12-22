import re
import streamlit as st

def is_valid_email(email):
    email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(email_regex, email)

# Function to add product to the cart
def add_to_cart(product_id,products):
    product = next((p for p in products if p["id"] == product_id), None)
    if product:
        if product["name"] in st.session_state.cart:
            st.session_state.cart[product["name"]]["quantity"] += 1
        else:
            st.session_state.cart[product["name"]] = {
                "price": product["price"],
                "quantity": 1
            }

# Function to remove product from the cart
def remove_from_cart(product_id,products):
    product = next((p for p in products if p["id"] == product_id), None)
    if product and product["name"] in st.session_state.cart:
        st.session_state.cart[product["name"]]["quantity"] -= 1
        if st.session_state.cart[product["name"]]["quantity"] <= 0:
            del st.session_state.cart[product["name"]]