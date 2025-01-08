import re
import streamlit as st
import random
from supabase import create_client
import json
import re
from datetime import datetime ,timezone
import pandas as pd
import calendar
import matplotlib.pyplot as plt
from openai import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import AgentType
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.schema.output_parser import OutputParserException
from io import BytesIO
import base64
import pandas as pd

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
openai_api_key = st.secrets["OPENAI_API_KEY"]

supabase = create_client(url, key)

# customer_id = st.session_state['id']

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
    st.rerun()

# Function to remove product from the cart
def remove_from_cart(product_id,products):
    product = next((p for p in products if p["id"] == product_id), None)
    if product and product["name"] in st.session_state.cart:
        st.session_state.cart[product["name"]]["quantity"] -= 1
        if st.session_state.cart[product["name"]]["quantity"] <= 0:
            del st.session_state.cart[product["name"]]
    st.rerun()

def generate_unique_order_id():
    while True:
        order_id = random.randint(100000, 999999)  # Generate a random 6-digit order ID
        # Check if this order ID already exists
        existing_order = supabase.table("orders").select("order_id").eq("order_id", order_id).execute()
        if not existing_order.data:  # If no matching order ID, it's unique
            return order_id

def quantity_check(item_name):
    response = supabase.table("products").select("quantity").ilike("name", item_name).execute()
    available_quantity = response.data[0]["quantity"]
    return available_quantity

def products_to_list(item_name):
    # st.write(supabase)
    response = supabase.table("products").select("name").execute()
    products = []
    # st.write(response)
    for res in response.data:
        products.append(res["name"].lower())
    if item_name.lower() in products:
        #st.write("Product available")
        return True
    return False

def check_role(email):
    result = (
        supabase.table("retailer").select("retailer_email").eq("retailer_email", email).execute()
    )
    if result.data:
        return True
    else:
        return False

def check_quantity(item_name, quantity_needed):
    response = supabase.table("products").select("quantity").ilike("name", item_name).execute()
    available_quantity = response.data[0]["quantity"]
    if available_quantity > quantity_needed:
        #st.write("Quantity availabale")
        return [True,available_quantity]
    return [False,available_quantity]

def generate_unique_order_id():
    while True:
        order_id = random.randint(100000, 999999)  # Generate a random 6-digit order ID
        # Check if this order ID already exists
        existing_order = supabase.table("orders").select("order_id").eq("order_id", order_id).execute()
        if not existing_order.data:  # If no matching order ID, it's unique
            return order_id
        
def update_order(item_name,quantity):
    customer_id = st.session_state['id']
    order_id = generate_unique_order_id()  # Generate unique order ID
    current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    status = "Placed"

    order_response = supabase.table("orders").insert({
        "order_id": order_id,
        "customer_id": customer_id,
        "date_of_purchase": current_date,
        "name": item_name,
        "quantity": quantity,
        "status": status
    }).execute()
    
    return f"Your order has been placed successfully with Order ID: {order_id}."


def place_an_order(response_dict):
    item_name = response_dict.get("Item_name", "")
    quantity_str = response_dict["Quantity"]
    if isinstance(quantity_str, str):
        quantity = int("".join(filter(str.isdigit, quantity_str)))
    else:
        quantity = quantity_str  # If it's already an integer, use it as is.
    #quantity= int("".join(filter(str.isdigit, quantity_str)))
    print("placing order")
    if products_to_list(item_name):
        check=check_quantity(item_name, quantity)
        if check[0]:
            # Reduce the product quantity in the database
            initial_quantity=check[1]
            updated_quantity=initial_quantity-quantity
            response = supabase.table("products").update({
            "quantity":updated_quantity}).ilike("name", item_name).execute()
            res=update_order(item_name,quantity)
            return res
        else:
            return "The required quantity of product is not available"
    else:
        return "The product is not available"
    
def cancel_an_order(response_dict):
    customer_id = st.session_state['id']
    
    if not customer_id:
        return "Customer ID is required to cancel an order. Please log in."
    order_id=response_dict.get("Order_id",0)
    if order_id:
        response=supabase.table("orders").select("*").eq("customer_id", customer_id).eq("order_id",order_id).execute()
    else:
        response = supabase.table("orders").select("*").eq("customer_id", customer_id).eq("status","Placed").order("date_of_purchase", desc=True).limit(1).execute()
    #st.write(response.data)
        
    if len(response.data) > 0:
        last_order = response.data[0] 
        order_id = last_order["order_id"]
        status = last_order["status"]

        if status == "delivered":
            return f"Order ID {order_id} cannot be cancelled as it is already delivered."
        
        cancel_response = supabase.table("orders").update({"status": "cancelled"}).eq("order_id", order_id).execute()
        
        return f"Order ID {order_id} has been successfully cancelled."
    else:
        return "No orders found for the user or an error occurred."
    
def retrieve_order_info():
    customer_id = st.session_state['id']
    if not customer_id:
        return "User ID is required to retrieve order information. Please log in."
    
    response = (
        supabase.table("orders")
        .select("*")
        .eq("customer_id", customer_id)
        .order("date_of_purchase", desc=True)
        .limit(3)
        .execute()
    )

    if len(response.data) > 0:
        orders = response.data
        order_details = []
        for order in orders:
            order_details.append({
                "Order ID": order["order_id"],
                "Item Name": order["name"],
                "Quantity": order["quantity"],
                "Order Date": order["date_of_purchase"],
                "Status": order["status"],
            })

        return order_details
    else:
        return "No orders found for this user."
    
def meal_planning(response_dict):
    # Extract ingredients from assistant_reply
    ingredients = response_dict.get("Ingredients", [])
    
    if not ingredients:
        return "No ingredients found in the response."

    # Format the ingredient details
    ingredient_details = []
    for ingredient in ingredients:
        item = ingredient.get("Item", "Unknown item")
        quantity = ingredient.get("Quantity", "Unknown quantity")
        ingredient_details.append({"Item": item, "Quantity": quantity})

    return ingredient_details

def multiple_orders(response_dict):
    print("Processing multiple orders")
    items = response_dict.get("Items", [])
    not_available_items = []  # List to track unavailable items
    order_results = []        # List to track results of successful orders

    if not items:
        return "No items provided for placing orders."

    for item in items:
        # Extract item name and quantity dynamically from the dictionary
        for key, value in item.items():
            if "Item_name" in key:
                item_name = value
            if "Quantity" in key:
                quantity_str = value

        # Create a single-order response dictionary and reuse the place_an_order logic
        single_order_dict = {"Item_name": item_name, "Quantity": quantity_str}
        result = place_an_order(single_order_dict)

        if "not available" in result.lower():
            not_available_items.append(item_name)
        else:
            order_results.append(f"Item: {item_name}, Result: {result}")

    # Final message with successful orders and unavailable items
    success_message = "\n".join(order_results) if order_results else "No orders placed successfully."
    not_available_message = f"Unavailable items: {', '.join(not_available_items)}" if not_available_items else "All items were available."

    return f"{success_message}\n{not_available_message}"

SYSTEM_PROMPT="""
The chatbot should respond politely to user greetings like "hello", "hi", "hey", etc. 
When a greeting is detected, respond with: "Hello! How may I help you today?"
You need to consider the punctuation marks and understand the user prompt and give output as mentioned
If the user input is related to order management,The system is designed to understand user commands related to order management, such as placing an order, cancelling an order, or retrieving order information. Based on the user input, the system should extract relevant information and format it in a structured way.
For any irrelevant input that doesn't match these categories, respond with: "Please enter relevant text."
Action Identification and Expected Output
1. Placing an Order

Synonyms: "place", "create", "order", "buy", "make","need","want", etc.
Extracted Information:
Item Name: The name of the item the user wants to order.
Action: "Place order".
Quantity: The number of items the user wants to order.
{
  "Item_name": "<name of the item being ordered>",
  "Action": "Place order",
  "Quantity": <quantity being ordered> with units
}
2. Placing multiple items order 
Synonyms: "place", "create", "order", "buy", "make","need","want", etc
you need to check whether there are multiple items in a prompt if the user prompt contains multiple items the output should be in the form as mentioned below
if there are more than one item in prompt the action should be in Place Multiple orders
Item Name: The name of the item the user wants to order.
Action: "Place multiple order".
Quantity: The quantity of specific item the user wants to order.
{
  "Action": "Place multiple orders",
  ""Items":[
      "Item_name 1": "<name of the item being ordered>",
       "Quantity 1": <quantity being ordered> with units
      "Item_name 2": "<name of the item being ordered>",
      "Quantity 2": <quantity being ordered> with units
      "Item_name 3": "<name of the item being ordered>",
      "Quantity 3": <quantity being ordered> with units
  ]
}

3.Cancelling an Order

Synonyms: "cancel", "remove", "delete", "stop", "abort", etc.
Extracted Information:
Action: "Cancel order".
No item name or quantity is required.

{
    "Order_id":"id number given by user"
  "Action": "Cancel order"
}
4.Retrieving Order Information

Synonyms: "retrieve", "check", "status", "view", "get","give" etc.
Extracted Information:
Action: "Retrieve order information".
No item name or quantity is required.
{
  "Action": "Retrieve information"
}
5.Meal Planning 
Synonyms: "prepare", "make", "create", "bake", "cook".
Extracted Information:"
Action:"Meal prepare recipe"
Item: Each individual ingredient or item needed for the event.
Quantity: The required quantity of each ingredient/item.give all the quantities in kilograms for solids and litres for liquids
It should return numerical quantities approximately not vague values
it should list all the ingredients seperately with respective quantities with units(grams, kilograms,litres,millilitres)
{
    "Action":"Meal recipe"
  "Ingredients": [
    {"Item": "<ingredient1>", "Quantity": <quantity1>with units},
    {"Item": "<ingredient2>", "Quantity": <quantity2>with units},
    {"Item": "<ingredient3>", "Quantity": <quantity3>with units}
  ]
}

"""
def process_user_input(model,user_prompt):
    response = model.generate_content(f"{SYSTEM_PROMPT}\nUser: {user_prompt}")
    assistant_reply = response.text.strip()
    print(f"Assistant Reply: {assistant_reply}")
    print(type(assistant_reply))
    if assistant_reply == "Hello! How may I help you today?":
        return assistant_reply
    elif assistant_reply=="Please enter relevant text.":
        return assistant_reply
    else:
        if isinstance(response, str):
            response = assistant_reply
        else:
            response = str(assistant_reply)
        pattern = r'"(\w+)":\s*("[^"]*"|\d+)'
        matches = re.findall(pattern, response)
        response_dict = {key: json.loads(value) if value.isdigit() else value.strip('"') for key, value in matches}
        #matches = re.sub(r",\s*([\}\]])", r"\1", assistant_reply)
        #print(matches)
        #response_dict=json.loads(matches)
        pattern = r'"(\w+(?:_\w+)?)":\s*(?:(\[[^\]]*\])|("[^"]*")|(\d+))'
        matches = re.findall(pattern, response)
        response_dict = {}
        for match in matches:
            key = match[0]
            value = match[1] or match[2] or match[3]
            if value:
                if value.startswith('['):  
                    response_dict[key] = json.loads(value)
                elif value.isdigit():  
                    response_dict[key] = int(value)
                else:  
                    response_dict[key] = value.strip('"')
        print(response_dict)
        #print(type(response_dict))
        if response_dict["Action"]=="Place order":
            return place_an_order(response_dict)
        elif response_dict["Action"]=="Cancel order":
            return cancel_an_order(response_dict)
        elif response_dict["Action"]=="Retrieve information":
            return retrieve_order_info()
        elif response_dict["Action"]=="Meal recipe":
            return meal_planning(response_dict)
        elif response_dict["Action"]=="Place multiple orders":
            return multiple_orders(response_dict)
        else:
            return 'No valid response'

def products_fetch():
    """Fetches the list of existing products from the database."""
    response = supabase.table("products").select("name").execute()
    return [item["name"] for item in response.data]

def fetch_product_details(name):
    """Fetches details of a specific product."""
    response = supabase.table("products").select("unit, price, image_link, description, quantity").eq("name", name).execute()
    if  response.data:
        return response.data[0]
    
def update_or_add_inventory(name, unit, quantity, image_link, price, description):
    """Checks if the product exists; updates quantity if yes, else adds a new row."""
        # Check if the product already exists
    response = supabase.table("products").select("id, quantity").eq("name", name).execute()
    if response.data:
        # Product exists, update the quantity
        product_id = response.data[0]["id"]
        existing_quantity = response.data[0]["quantity"]
        new_quantity = existing_quantity + quantity
        update_response = supabase.table("products").update({"quantity": new_quantity}).eq("id", product_id).execute()
        return st.success(f"Inventory updated successfully! New quantity: {new_quantity}")
        
    else:
        # Product does not exist, add a new row
        add_response = supabase.table("products").insert({
            "name": name,
            "unit": unit,
            "quantity": quantity,
            "image_link": image_link,
            "price": price,
            "description": description,
        }).execute()
        return st.success(f"{name} is added successfully into Inventory!")
    
def fetch_products():
    response = supabase.table("products").select("*").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def fetch_orders():
    response = supabase.table("orders").select("*").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def predict_orders(data):
    predictions = {}
    
    for item in data["name"].unique():
        # Filter data for the current item
        item_data = data[data["name"] == item]
        
        # Check if the data has fewer than 3 entries
        if len(item_data) < 3:
            # Use the quantity from the most recent day
            avg_quantity = item_data["quantity"].iloc[-1]
        else:
            # Calculate the rolling mean for the last 3 entries
            avg_quantity = item_data["quantity"].rolling(3).mean().iloc[-1]
        
        # Store the result in the predictions dictionary
        predictions[item] = max(0, int(avg_quantity))  # Ensure non-negative predictions
    
    return predictions

def fetch_orders_data():
    """Fetch orders data."""
    response = supabase.table("orders").select("*").execute()
    if not response.data:
        return pd.DataFrame()  # Return empty DataFrame if no data
    orders_data = pd.DataFrame(response.data)
    orders_data['name'] = orders_data['name'].str.lower()
    
    orders_data['date_of_purchase'] = pd.to_datetime(orders_data['date_of_purchase'], errors='coerce')
    return orders_data

def plot_product_sales(orders_data, granularity, year=None, month=None):
    month_name = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }
    
    if granularity == "Yearly" and year:
        filtered_data = orders_data[orders_data['date_of_purchase'].dt.year == year]
        if filtered_data.empty:
            st.warning("No data available for the selected criteria.")
            return
        else:
            #st.write(filtered_data)
            sales_data = filtered_data.groupby('name')['quantity'].sum()
            st.subheader(f"Product-Wise Sales ({granularity})")
            fig, ax = plt.subplots(figsize=(10, 6))
            sales_data.plot(kind='bar', color='skyblue', ax=ax)
            ax.set_xlabel("Product")
            ax.set_ylabel("Quantity Sold")
            ax.set_title(f"Product-Wise Sales ({granularity} {year})")
            plt.xticks(rotation=45)
            st.pyplot(fig)
    elif granularity == "Monthly" and year and month:
        # Filter by selected year and month
        filtered_data = orders_data[
            (orders_data['date_of_purchase'].dt.year == year) & 
            (orders_data['date_of_purchase'].dt.month == int(month))
        ]
        if filtered_data.empty:
            st.warning("No data available for the selected criteria.")
            return
        else:
            sales_data = filtered_data.groupby('name')['quantity'].sum()
            st.subheader(f"Product-Wise Sales ({granularity} {year} {month_name[month]})")
            fig, ax = plt.subplots(figsize=(10, 6))
            sales_data.plot(kind='bar', color='skyblue', ax=ax)
            ax.set_xlabel("Product")
            ax.set_ylabel("Quantity Sold")
            ax.set_title(f"Product-Wise Sales")
            plt.xticks(rotation=45)
            st.pyplot(fig)
    else:
        filtered_data = orders_data

def plot_overall_sales(orders_data, granularity, year=None, month=None):
    month_name = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }
    """Plot overall sales."""
    if granularity == "Yearly":
        yearly_sales = orders_data.groupby(orders_data['date_of_purchase'].dt.year)['quantity'].sum()
        start_year = 2010  # Define the starting year
        end_year = 2050    # Define the ending year
        all_years = pd.Series(0, index=range(start_year, end_year + 1))  # Create a series with all years set to 0
        yearly_sales = all_years.add(yearly_sales, fill_value=0)  # Add the actual sales data, filling missing years with 0
        #st.write(yearly_sales)
        if yearly_sales.empty:
            st.warning("No data available for the selected criteria.")
            return
        st.subheader("Overall Sales by Year")
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the line graph
        ax.plot(yearly_sales.index, yearly_sales.values, marker='o', color='blue', label='Total Sales')

        # Set axis labels and title
        ax.set_xlabel("Year")
        ax.set_ylabel("Total Quantity Sold")
        ax.set_title("Sales Trend Over the Years")

        # Add grid and legend
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()

        # Display the plot in Streamlit
        st.pyplot(fig)


    elif granularity == "Monthly" and year:
        monthly_sales = orders_data[orders_data['date_of_purchase'].dt.year == year]
        monthly_sales = monthly_sales.groupby(orders_data['date_of_purchase'].dt.month)['quantity'].sum()
        if monthly_sales.empty:
            st.warning("No data available for the selected criteria.")
            return
        all_months = pd.Series(0, index=range(1, 13))
        monthly_sales = all_months.add(monthly_sales, fill_value=0)
        monthly_sales.index = monthly_sales.index.map(lambda x: calendar.month_name[x])
        st.subheader(f"Overall Sales by Month ({year})")
        fig, ax = plt.subplots(figsize=(10, 6))
        monthly_sales.plot(kind='bar', color='blue', ax=ax)

        # Set axis labels and title
        ax.set_xlabel("Month")
        ax.set_ylabel("Total Quantity Sold")
        ax.set_title(f"Overall Sales by Month ({year})")
        plt.xticks(rotation=45)  # Rotate month names for better readability
        st.pyplot(fig)

def extract_python_code(text):
    pattern = r'```python\s(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if not matches:
        return None
    else:
        return matches[0]
    

def plot_matplotlib_code(code):
    buf = BytesIO()
    exec(code)
    plt.savefig(buf, format="png")
    buf.seek(0)
    image = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return f"data:image/png;base64,{image}"


def chat_with_data_api(df):
    # Check if 'date_of_purchase' exists in the DataFrame
    if "date_of_purchase" in df.columns:
        # Convert 'date_of_purchase' to datetime format, handling errors by coercing invalid entries to NaT
        df['date_of_purchase'] = pd.to_datetime(df['date_of_purchase'], errors='coerce')  # Invalid dates become NaT

        # Check if there are any NaT values after conversion
        if df['date_of_purchase'].isnull().any():
            st.warning("Some date values could not be parsed and are now NaT. These rows may be skipped in analysis.")
        
        # Only proceed with .dt accessor if the column is datetime
        if pd.api.types.is_datetime64_any_dtype(df['date_of_purchase']):
            # Proceed with extracting year and month
            df['year'] = df['date_of_purchase'].dt.year  # Extracting year
            df['month'] = df['date_of_purchase'].dt.month  # Extracting month
        else:
            st.warning("The 'date_of_purchase' column is not in a valid datetime format.")
    else:
        st.warning("The 'date_of_purchase' column is not found in the DataFrame.")

    # Rest of your code logic for interacting with OpenAI
    api_key = openai_api_key
    model = "gpt-3.5-turbo"
    max_tokens = 256
    temperature = 0.0
    top_p = 0.5

    if "plot" in st.session_state.messages[-1]["content"].lower():
        code_prompt = """
            Generate the code <code> for plotting the previous data in plotly,
            in the format requested. The solution should be given using plotly
            and only plotly. Do not use matplotlib.
            Return the code <code> in the following
            format ```python <code>```
        """
        st.session_state.messages.append({
            "role": "assistant",
            "content": code_prompt
        })
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=st.session_state.messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        code = extract_python_code(response.choices[0].message.content)
        if code is None:
            st.warning(
                "Couldn't find data to plot in the chat. "
                "Check if the number of tokens is too low for the data at hand. "
                "I.e. if the generated code is cut off, this might be the case.",
                icon="🚨"
            )
            return "Couldn't plot the data"
        else:
            code = code.replace("fig.show()", "")
            code += """st.plotly_chart(fig, theme='streamlit', use_container_width=True)"""  # noqa: E501
            st.write(f"```{code}")
            exec(code)
            return response.choices[0].message.content
    else:
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            openai_api_key=api_key
        )

        pandas_df_agent = create_pandas_dataframe_agent(
            llm,
            df,
            verbose=True,
            return_intermediate_steps=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            handle_parsing_errors=False,
            allow_dangerous_code=True
        )

        try:
            answer = pandas_df_agent(st.session_state.messages)
            if answer["intermediate_steps"]:
                action = answer["intermediate_steps"][-1][0].tool_input["query"]
                st.write(f"Executed the code ```{action}```")
                
                if "matplotlib" in action:
                    # Generate the plot and return the image
                    image_data = plot_matplotlib_code(action)
                    st.image(image_data)
                    return "Matplotlib plot generated."
                    
            return answer["output"]
        except OutputParserException:
            error_msg = """OutputParserException error occured in LangChain agent.
                Refine your query."""
            return error_msg
        except:  # noqa: E722
            answer = "Unknown error occured in LangChain agent. Refine your query"
            return answer
