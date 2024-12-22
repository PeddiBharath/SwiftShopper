import streamlit as st
from supabase import create_client
from concurrent.futures import ThreadPoolExecutor
from functions import is_valid_email,add_to_cart,remove_from_cart
from gotrue.errors import AuthApiError

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

st.header("SwiftShopper")

# Initialize session state for email
if 'email' not in st.session_state:
    st.session_state['email'] = " "

if "cart" not in st.session_state:
    st.session_state.cart = {}

# If user is not logged in, show Register/Login/Forgot Password tabs
if st.session_state['email'] == " ":
    tab1, tab2 = st.tabs(["Register", "Login"])
    
    # Register tab
    with tab1:
        with st.form(key="register"):
            email_id = st.text_input(label="Enter email*", help="Enter your email")
            password = st.text_input(label="Enter password*", type="password", help="At least enter 6 characters")
            st.markdown("**required*")
            submit = st.form_submit_button("Submit")
            if submit:
                if not email_id or not password:
                    st.warning("Enter all the mandatory fields")
                elif not is_valid_email(email_id):
                    st.error("Enter a proper email")
                else:
                    try:
                        supabase.auth.sign_up({"email": email_id, "password": password})
                        st.success("Thanks for signing up! Check your email and confirm the email")
                    except Exception as e:
                        st.error(f"An unexpected error occurred during registration: {e}")

    # Login tab
    with tab2:
        with st.form(key="login"):
            email_id = st.text_input(label="Enter email*", help="Enter your email")
            password = st.text_input(label="Enter password*", type="password", help="Enter the password used while registering")
            st.markdown("**required*")
            submit = st.form_submit_button("Submit")
            if submit:
                if not email_id or not password:
                    st.warning("Enter all the mandatory fields")
                elif not is_valid_email(email_id):
                    st.error("Enter a proper email")
                else:
                    try:
                        session = supabase.auth.sign_in_with_password({"email": email_id, "password": password})
                        st.session_state['email'] = email_id
                        st.rerun()
                    except AuthApiError as e:
                        if "Email not confirmed" in str(e):
                            st.warning("Error: Email not confirmed. Please confirm your email before logging in.")
                        else:
                            st.warning(f"AuthApiError: {e}")
                    except Exception as e:
                        st.warning(f"An unexpected error occurred during login: {e}")
                    


else:
    with st.sidebar:
        logout = st.button("Logout")
        if logout:
            supabase.auth.sign_out()
            st.session_state['email'] = " "
            st.rerun()
    m = st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: rgb(204, 49, 49);
        width: 100%; /* Default to full width */
        max-width: 700px; /* Maximum width */
        padding: 10px 20px;
        border: none;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 12px;
    }
    </style>""", unsafe_allow_html=True)

    email = st.session_state['email']

    # Initialize session state for the cart


    response = supabase.table("products").select("*").execute()
    products = []
    for res in response:
        products.append(res[1])
    # print(type(res))
    products = products[0]
# List of products
# '''
# products = [
#     {"name": "Toor Dal", "image_url": "https://gonefarmers.com/cdn/shop/products/image_09da0cb2-0322-4220-ba90-dfb1da774c62_1024x1024@2x.jpg?v=1583506991"},
#     {"name": "Urad Dal", "image_url": "https://martoo.com/wp-content/uploads/2022/02/Urad-Dal.png"},
#     {"name": "Maida", "image_url": "https://m.media-amazon.com/images/I/41Hr5RnnAcL.jpg"}
# ]
# '''
    
    # st.markdown(products)

# Search bar
    search_query = st.text_input("Search for a product:")

    # Filter products based on the search query
    filtered_products = [
        product for product in products
        if search_query.lower() in product["name"].lower()
    ]

    # Display "Cart" section with counter
    st.sidebar.header("🛒 Your Cart")
    if st.session_state.cart:
        for item, details in st.session_state.cart.items():
            st.sidebar.write(f"{item}: {details['quantity']} unit(s) - ₹{details['price']} each")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if col1.button(f"➕ Add {item}", key=f"add-{item}-sidebar"):
                    product_id = next(p['id'] for p in products if p['name'] == item)
                    add_to_cart(product_id,products)
                    st.rerun()
            with col2:
                if col2.button(f"➖ Remove {item}", key=f"remove-{item}-sidebar"):
                    product_id = next(p['id'] for p in products if p['name'] == item)
                    remove_from_cart(product_id,products)
                    st.rerun()
    else:
        st.sidebar.write("Your cart is empty.")


# Display products
    if search_query:
        if filtered_products:
            for product in filtered_products:
                st.header(product["name"])
                st.image(product["image_link"])
                st.markdown(f"""
                    <div style="font-size:20px; font-weight:bold; color:#2a9d8f; background-color:#f0f8ff; padding:10px; border-radius:8px;">
                        **Product Description:**
                    </div>
                    <div style="font-size:18px; font-style:italic; color:#264653; padding:10px; border-left:4px solid #e76f51;">
                        {product['description']}
                    </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Add {product['name']} to Cart", key=f"add-{product['id']}"):
                        add_to_cart(product['id'], products)
                        st.success(f"{product['name']} added to cart!")
                        st.rerun()
                with col2:
                    if st.button(f"Remove {product['name']} from Cart", key=f"remove-{product['id']}"):
                        remove_from_cart(product['id'], products)
                        st.warning(f"{product['name']} removed from cart!")
                        st.rerun()
        else:
            st.write("No products found.")
    else:
        cols = st.columns(3)
        for idx, product in enumerate(products):
            with cols[idx % 3]:  # Dynamically distribute products across columns
                st.header(product["name"])
                st.image(product["image_link"], use_column_width=True)
                st.write(product["description"])
                st.write(f"Price: ₹{product['price']} per {product['unit']}")
                st.write(f"Available: {product['quantity']} {product['unit']}(s)")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Add {product['name']}", key=f"add-{product['id']}"):
                        add_to_cart(product["id"],products)
                        st.success(f"{product['name']} added to cart!")
                with col2:
                    if st.button(f"Remove {product['name']}", key=f"remove-{product['id']}"):
                        remove_from_cart(product["id"],products)
                        st.warning(f"{product['name']} removed from cart!")

st.markdown(st.session_state.cart)
 