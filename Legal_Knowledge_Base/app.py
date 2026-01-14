import streamlit as st
import pandas as pd
import sqlite3
import os
from logic import run_full_pipeline, DB_PATH, OPENROUTER_API_KEY

# 1. PAGE CONFIG
st.set_page_config(page_title="Labor Law Digitizer", page_icon="⚖️", layout="wide")

# 2. LEGAL THEME CSS
st.markdown("""
    <style>
    .main { background-color: #fdfaf5; color: #002b47; font-family: 'Georgia', serif; }
    .stTitle { border-bottom: 3px solid #a87a4d; padding-bottom: 10px; }
    .ai-label { background-color: #002b47; color: #a87a4d; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ Labor Law AI Digitizer")
st.caption("Professional Decoupled Document Parsing System")

# 3. SIDEBAR & KEY PROTECTION
with st.sidebar:
    st.header("Settings")
    if OPENROUTER_API_KEY:
        st.success("✅ API Key Loaded from Environment")
        api_key = OPENROUTER_API_KEY
    else:
        api_key = st.text_input("OpenRouter API Key", type="password")

# 4. MAIN INTERFACE
uploaded_pdf = st.file_uploader("Upload Labor Code PDF", type="pdf")

if st.button("🚀 Run AI Analysis") and uploaded_pdf:
    if not api_key:
        st.error("Missing API Key! Please check your api_keys.env.")
    else:
        with st.spinner("AI Router is classifying document..."):
            count, doc_type = run_full_pipeline(uploaded_pdf, api_key)
            st.markdown(f"### 🤖 AI Routing Result: <span class='ai-label'>{doc_type}</span>", unsafe_allow_html=True)
            st.success(f"Parsing Complete: {count} articles saved across specialized tables.")

st.divider()

# 5. DATABASE EXPLORER
st.subheader("📁 Categorized Table Viewer")
if os.path.exists(DB_PATH):
    table_to_view = st.selectbox("Select specialized table:", ["wages", "contracts", "general"])
    if st.button("Refresh View"):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT article_number, title, is_repealed, content FROM {table_to_view}", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
else:
    st.info("No database found yet. Run the parser to generate data.")