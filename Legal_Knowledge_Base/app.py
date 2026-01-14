import streamlit as st
import pandas as pd
import sqlite3
import os
from logic import run_full_pipeline, DB_PATH, OPENROUTER_API_KEY

# 1. PAGE CONFIG
st.set_page_config(page_title="Labor Law Digitizer", page_icon="⚖️", layout="wide")

# 2. THEME CSS (FIXED unsafe_allow_html)
st.markdown("""
    <style>
    .main { background-color: #fdfaf5; color: #002b47; font-family: 'Georgia', serif; }
    .stTitle { border-bottom: 3px solid #a87a4d; padding-bottom: 10px; }
    .ai-label { background-color: #002b47; color: #a87a4d; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True) # FIXED

st.title("Labor Law AI Digitizer")
st.caption("Professional Decoupled Document Parsing System")

# 3. SIDEBAR & API KEY PROTECTION
with st.sidebar:
    st.header("Settings")
    # If the key is found in api_keys.env, we hide the input field
    if OPENROUTER_API_KEY:
        st.success("API Key Loaded from Environment")
        api_key = OPENROUTER_API_KEY
    else:
        # Field only appears if key is missing from the .env file
        api_key = st.text_input("OpenRouter API Key", type="password", help="Key not found in api_keys.env. Enter manually.")

# 4. MAIN INTERFACE
uploaded_pdf = st.file_uploader("Upload Labor Code PDF", type="pdf")

if st.button("Run AI Analysis") and uploaded_pdf:
    if not api_key:
        st.error("No API key found. Please check your api_keys.env file or enter it in the sidebar.")
    else:
        with st.spinner("AI Router is classifying document..."):
            count, doc_type = run_full_pipeline(uploaded_pdf, api_key)
            st.markdown(f"### 🤖 AI Routing: <span class='ai-label'>{doc_type}</span>", unsafe_allow_html=True)
            st.success(f"Parsing Complete: {count} articles saved across categorized tables.")

st.divider()

# 5. DATABASE EXPLORER
st.subheader("Categorized Table Viewer")
table_to_view = st.selectbox("Select specialized table:", ["wages", "contracts", "general"])

if st.button("Refresh View"):
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT article_number, title, is_repealed FROM {table_to_view}", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)