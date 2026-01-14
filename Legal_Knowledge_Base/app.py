import streamlit as st
import pandas as pd
import sqlite3
import os
from logic import run_full_pipeline, DB_PATH

# 1. PAGE CONFIG
st.set_page_config(page_title="Labor Law Digitizer", page_icon="⚖️", layout="wide")

# 2. FIXED THEME CSS
st.markdown("""
    <style>
    .main { background-color: #fdfaf5; color: #002b47; font-family: 'Georgia', serif; }
    .stTitle { border-bottom: 3px solid #a87a4d; padding-bottom: 10px; }
    .ai-label { background-color: #002b47; color: #a87a4d; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True) # FIXED: Changed from unsafe_allow_index to unsafe_allow_html

st.title("⚖️ Labor Law AI Digitizer")
st.caption("Professional Document Analysis & SQL Storage System")

# 3. SIDEBAR & EXECUTION
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenRouter API Key", type="password")

uploaded_pdf = st.file_uploader("Upload Labor Code PDF", type="pdf")

if st.button("🚀 Process Labor Code") and uploaded_pdf:
    if not api_key:
        st.error("Please provide an API Key.")
    else:
        with st.spinner("AI Router is analyzing document..."):
            count, doc_type = run_full_pipeline(uploaded_pdf, api_key)
            st.markdown(f"### 🤖 AI Routing: <span class='ai-label'>{doc_type}</span>", unsafe_allow_html=True)
            st.success(f"Parsing Complete: {count} articles saved.")

st.divider()

# 4. DATABASE EXPLORER
st.subheader("📁 Categorized Table Viewer")
table_to_view = st.selectbox("Select specialized table:", ["wages", "contracts", "general"])

if st.button("Refresh View"):
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT article_number, title, is_repealed FROM {table_to_view}", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)