import streamlit as st
from supabase import create_client
from functions import is_valid_email,add_to_cart,remove_from_cart,generate_unique_order_id,check_quantity,check_role,quantity_check,products_fetch,fetch_product_details,update_or_add_inventory,fetch_products,fetch_orders,predict_orders,fetch_orders_data,plot_overall_sales,plot_product_sales
from gotrue.errors import AuthApiError
from datetime import datetime,timezone
import pandas as pd

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

st.header("SwiftShopper")

if 'role' not in st.session_state:
    st.session_state['role'] = " "

if 'email' not in st.session_state:
    st.session_state['email'] = " "

if "cart" not in st.session_state:
    st.session_state.cart = {}

# If user is not logged in, show Register/Login/Forgot Password tabs
if st.session_state['email'] == " ":
    option = st.selectbox("What are you?",("Customer", "Retailer"))

    if option=="Customer":
        tab1, tab2 = st.tabs(["Register", "Login"])
        
        # Register tab
        with tab1:
            with st.form(key="register"):
                email_id = st.text_input(label="Enter email*", help="Enter your email")
                password = st.text_input(label="Enter password*", type="password", help="At least enter 6 characters")
                name = st.text_input(label="Enter Your Name*", help="Your Full name")
                st.markdown("**required*")
                submit = st.form_submit_button("Submit")
                if submit:
                    if not email_id or not password or not name:
                        st.warning("Enter all the mandatory fields")
                    elif not is_valid_email(email_id):
                        st.error("Enter a proper email")
                    else:
                        try:
                            supabase.auth.sign_up({"email": email_id, "password": password})
                            supabase.table("customers").insert([{"customer_email": email_id, "customer_name": name}]).execute()
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
                            st.session_state['role'] = "Customer"
                            st.rerun()
                        except AuthApiError as e:
                            if "Email not confirmed" in str(e):
                                st.warning("Error: Email not confirmed. Please confirm your email before logging in.")
                            else:
                                st.warning(f"AuthApiError: {e}")
                        except Exception as e:
                            st.warning(f"An unexpected error occurred during login: {e}")
    
    elif option=="Retailer":
        st.markdown("""
                    <h2>Retailer Login</h2>
                    """,unsafe_allow_html=True)
        with st.form(key="retailer_login"):
            email = st.text_input(label="Email*",help="Enter the email you have used while registering")
            password = st.text_input(label="Password*",help="Enter the respective password",type="password")
            st.markdown("**required*")
            submit = st.form_submit_button("Login")
            if submit:
                if not email or not password:
                    st.error("Enter all the mandatory fields")
                elif not is_valid_email(email):
                    st.error("Enter a proper email")
                elif not check_role(email):
                    st.warning("Invalid Login")
                else:
                    try:
                        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state['email'] = email
                        st.session_state['role'] = "Retailer"
                        st.rerun()
                    except AuthApiError as e:
                        if "Email not confirmed" in str(e):
                            st.warning("Error: Email not confirmed. Please confirm your email before logging in.")
                        else:
                            st.warning(f"AuthApiError: {e}")
                    except Exception as e:
                        st.warning(f"An unexpected error occurred during login: {e}")

if st.session_state['role'] == "Customer":
    with st.sidebar:
        logout = st.button("Logout")
        if logout:
            supabase.auth.sign_out()
            st.session_state['email'] = " "
            st.session_state['cart'] = {}
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

    response_name = supabase.table("customers").select("customer_name").eq("customer_email", email).execute()
    st.session_state['name'] = response_name.data[0]["customer_name"]
    name = st.session_state['name']
    st.markdown(f"<h3>Welcome back, {name}</h3>",unsafe_allow_html=True)
    response_id = supabase.table("customers").select("customer_id").eq("customer_email", email).execute()
    st.session_state['id'] = response_id.data[0]["customer_id"]
    customer_id = st.session_state['id']
    # Initialize session state for the cart


    response = supabase.table("products").select("*").execute()
    products = []
    for res in response:
        products.append(res[1])
    # print(type(res))
    products = products[0]

# Search bar
    search_query = st.text_input("Search for a product:")

    # Filter products based on the search query
    filtered_products = [
        product for product in products
        if search_query.lower() in product["name"].lower()
    ]

    # Display "Cart" section with counter
    st.sidebar.header("🛒 Your Cart")
    total_price = 0
    if st.session_state.cart:
        for item, details in st.session_state.cart.items():
            st.sidebar.write(f"{item}: {details['quantity']} unit(s) - ₹{details['price']} each")
            total_price += details['quantity'] * details['price']
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if col1.button(f"➕ Add {item}", key=f"add-{item}-sidebar"):
                    product_id = next(p['id'] for p in products if p['name'] == item)
                    add_to_cart(product_id, products)
            with col2:
                if col2.button(f"➖ Remove {item}", key=f"remove-{item}-sidebar"):
                    product_id = next(p['id'] for p in products if p['name'] == item)
                    remove_from_cart(product_id, products)
    else:
        st.sidebar.write("Your cart is empty.")

    if total_price > 0:
        st.sidebar.write(f"**Total Price: ₹{total_price}**")
        checkout = st.sidebar.button("Checkout")
        if checkout:
            order_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            data = st.session_state.cart
            for item_name, item_details in data.items():
                quantity = item_details['quantity']
                order_id = generate_unique_order_id()
                initial_quantity = quantity_check(item_name)
                updated_quantity = initial_quantity - quantity
                supabase.table("orders").insert([{"order_id":order_id ,"customer_id": customer_id, "date_of_purchase": order_time, "name":item_name, "quantity":quantity, "status":"Placed"}]).execute()
                supabase.table("products").update({"quantity":updated_quantity}).ilike("name", item_name).execute()
            st.session_state.cart = {}
            st.success(f"Order placed successfully!")
            st.rerun()

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
                st.image(product["image_link"], use_container_width=True)
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

elif st.session_state['role'] == "Retailer":
    st.sidebar.title("Options")
    action = st.sidebar.selectbox(
        "Select Action", 
        ["View Products", "Add Inventory", "View Orders", "Predict Orders","Visualisation"]
    )

    # View Products
    if action == "View Products":
        st.header("Product List")
        products = fetch_products()
        if not products.empty:
            st.dataframe(products)
        else:
            st.write("No products found.")

    # Add Inventory
    elif action == "Add Inventory":
        # Fetch products and add "Other" option
        product_list = products_fetch()
        product_list.insert(0, " ") 
        product_list.append("Other")

        # Dropdown to select product
        selected_product = st.selectbox("Select Product", product_list, index=0, help="Select a product from the list or choose 'Other' to add a new product.")

        if selected_product == "Other":
            # Adding a new product
            name = st.text_input("Enter New Product Name")
            unit = st.text_input("Unit (e.g., kg, pcs, etc.)")
            quantity = st.number_input("Quantity", min_value=1, step=1)
            image_link = st.text_input("Image Link (URL)")
            price = st.number_input("Price per Unit", min_value=0, step=1)
            description = st.text_area("Product Description")
            if st.button("Add Inventory"):
                if name.strip():
                    update_or_add_inventory(name, unit, quantity, image_link, price, description)
        elif selected_product:
            # Existing product selected
            product_details = fetch_product_details(selected_product)
            if product_details:
                st.write(f"**Unit:** {product_details['unit']}")
                st.write(f"**Price per Unit:** {product_details['price']}")
                st.write(f"**Image Link:** {product_details['image_link']}")
                st.write(f"**Description:** {product_details['description']}")
                st.write(f"**Current Quantity:** {product_details['quantity']}")
                
                quantity = st.number_input("Quantity to Add", min_value=1, step=1)
                if st.button("Update Inventory"):
                    update_or_add_inventory(
                        name=selected_product,
                        unit=product_details["unit"],
                        quantity=quantity,
                        image_link=product_details["image_link"],
                        price=product_details["price"],
                        description=product_details["description"],
                    )
                    
        else:
            st.info("Please select a product or choose 'Other' to add a new product.")

    # View Orders
    elif action == "View Orders":
        st.header("Order List")
        orders = fetch_orders()
        if not orders.empty:
            st.dataframe(orders)
        else:
            st.write("No orders found.")


    # Predict Orders
    elif action == "Predict Orders":
        orders = fetch_orders()
        if not orders.empty:
            if "quantity" in orders.columns:
                predictions = predict_orders(orders)
                st.subheader("Predicted Orders")
                st.write(pd.DataFrame(predictions.items(), columns=["Product Name", "Predicted Quantity"]))
            else:
                st.error("Order data does not contain the required 'quantity' column.")
        else:
            st.write("No orders found for prediction.")
    
    elif action == "Visualisation":
        st.header("Sales Visualization")

        orders_data = fetch_orders_data()

        if not orders_data.empty:
            # Sales type selection
            sales_type = st.selectbox("Select Sales Type", ["","Product-Wise Sales", "Overall Sales"])
            granularity = st.selectbox("Select Granularity", ["","Yearly", "Monthly"])

            if granularity == "Yearly": 
                if sales_type == "Product-Wise Sales":
                    year = st.selectbox("Select Year", range(2000, 2101),placeholder="Choose a value")
                    plot_product_sales(orders_data, granularity="Yearly", year=year)
                else:
                    plot_overall_sales(orders_data, granularity="Yearly")
            elif granularity == "Monthly":
                year = st.selectbox("Select Year", range(2000, 2101),placeholder="Choose a value")
                month_mapping = {
                "January": "01",
                "February": "02",
                "March": "03",
                "April": "04",
                "May": "05",
                "June": "06",
                "July": "07",
                "August": "08",
                "September": "09",
                "October": "10",
                "November": "11",
                "December": "12"
                }
                #selected_month_name = st.selectbox("Select Month", list(month_mapping.keys()))
            #month = month_mapping[selected_month_name]
            
                if sales_type == "Product-Wise Sales":
                    selected_month_name = st.selectbox("Select Month", list(month_mapping.keys()))
                    month = month_mapping[selected_month_name]
                    plot_product_sales(orders_data, granularity="Monthly", year=year, month=month)
                else:
                    plot_overall_sales(orders_data, granularity="Monthly", year=year)
        else:
            st.warning("No orders data available.")