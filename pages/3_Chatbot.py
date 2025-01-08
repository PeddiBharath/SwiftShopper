import streamlit as st
import google.generativeai as genai
from functions import process_user_input
import pandas as pd
from supabase import create_client
from functions import extract_python_code,chat_with_data_api

genai.configure(api_key=st.secrets["GEMINI_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

st.title('Chatbot')

if st.session_state['role'] == "Customer":
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is your query?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            stream = process_user_input(model, prompt)
            response = st.write(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

elif st.session_state['role'] == "Retailer":
    response = supabase.table("orders").select("*").execute()
    data = response.data
    df = pd.DataFrame(data)
    prompt = f"""You are a python expert. You will be given questions for
        manipulating an input dataframe.
        The available columns are: {df.columns}.
        Use them for extracting the relevant data.
        IMPORTANT: Only use Plotly for plotting. Do not use Matplotlib.
    """

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "system", "content": prompt}]
    
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        elif message["role"] == "assistant":
            with st.chat_message(message["role"]):
                if "import plotly" in message["content"]:
                    code = extract_python_code(message["content"])
                    code = code.replace("fig.show()", "")
                    code += """st.plotly_chart(fig, theme='streamlit', use_container_width=True)"""
                    exec(code)
                st.markdown(message["content"])
    
    if prompt := st.chat_input("What is your query?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            res = chat_with_data_api(df)
        st.session_state.messages.append({"role": "assistant", "content": res})
    
else:
    st.header("Login First")

    

    