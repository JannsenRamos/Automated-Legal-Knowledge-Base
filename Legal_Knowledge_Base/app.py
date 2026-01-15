import streamlit as st
import pandas as pd
import psycopg2
from logic import parse_and_validate, save_to_supabase, OPENROUTER_API_KEY, SUPABASE_DB_URL

st.set_page_config(page_title="Labor Law Cloud", page_icon="⚖️", layout="wide")

st.title("⚖️ Labor Law AI Cloud Digitizer")

uploaded_pdf = st.file_uploader("Upload PDF", type="pdf")

if uploaded_pdf and st.button("🔍 Validate Document"):
    try:
        with st.spinner("AI Gatekeeper is verifying..."):
            results = parse_and_validate(uploaded_pdf, OPENROUTER_API_KEY)
            st.session_state['results'] = results
            st.success(f"Verified {len(results)} articles.")
            with st.expander("👁️ JSON Structure Preview"):
                st.json(results[0][1].model_dump())
    except ValueError as e: st.error(str(e))

if 'results' in st.session_state and st.button("💾 Commit to Cloud"):
    save_to_supabase(st.session_state['results'])
    st.success("Data stored permanently in Supabase!")
    del st.session_state['results']

st.divider()
st.subheader("🌐 Cloud Explorer")
table = st.selectbox("Table:", ["wages", "contracts", "general"])
if st.button("Fetch"):
    conn = psycopg2.connect(SUPABASE_DB_URL)
    df = pd.read_sql_query(f"SELECT art_num, title FROM {table} LIMIT 10", conn)
    conn.close(); st.dataframe(df, use_container_width=True)