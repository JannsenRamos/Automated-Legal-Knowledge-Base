import streamlit as st
import requests
import os

# 1. Page Configuration & Styling
st.set_page_config(
    page_title="LICE Engine: Legal Audit",
    layout="wide"
)

# Custom CSS for a professional "Legal Tech" look
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title(" LICE: Legal Intelligence & Compliance Engine")
st.markdown("### Specialized Audit for OFW Employment Contracts")
st.divider()

# 2. Configuration & State Management
API_BASE_URL = "http://127.0.0.1:8000"

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

# 3. Sidebar Settings
with st.sidebar:
    st.header("Audit Settings")
    jurisdiction = st.selectbox("Target Jurisdiction", ["HK", "PH"], help="Determines which statutory baseline to use for the audit.")
    st.info("LICE compares your contract against local labor ordinances in real-time.")

# 4. File Upload Section
uploaded_file = st.file_uploader("Upload Contract (PDF or Text)", type=['pdf', 'txt'])

if uploaded_file:
    # Trigger Analysis
    if st.button("Run Comprehensive Audit"):
        with st.spinner("LICE is classifying clauses and verifying statutory compliance..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            params = {"jurisdiction": jurisdiction}
            
            try:
                response = requests.post(f"{API_BASE_URL}/analyze_contract", files=files, params=params)
                
                if response.status_code == 200:
                    # Store results in session state so they persist
                    st.session_state.analysis_results = response.json()
                else:
                    st.error(f"Analysis failed. Backend Error: {response.text}")
            except Exception as e:
                st.error(f"Could not connect to the LICE Engine. Ensure FastAPI is running. Error: {e}")

# 5. Display Results (Only if analysis has been run)
if st.session_state.analysis_results:
    res = st.session_state.analysis_results
    
    # DEFENSIVE CHECK: Ensure keys exist to prevent the KeyError you encountered
    if "summary" in res and "analysis" in res:
        summary = res["summary"]
        analysis = res["analysis"]

        # A. High-Level Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Clauses Scanned", summary.get("total_clauses", 0))
        m2.metric("Critical Violations", summary.get("critical_count", 0), delta_color="inverse")
        
        status = "NON-COMPLIANT" if not summary.get("is_compliant") else "✅ COMPLIANT"
        m3.subheader(f"System Status: {status}")

        st.divider()

        # B. Risk Breakdown by Priority
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            clauses = analysis.get(level, [])
            if not clauses:
                continue
            
            color = "red" if level == "CRITICAL" else "orange" if level == "HIGH" else "blue"
            with st.expander(f"{level} PRIORITY ITEMS ({len(clauses)})", expanded=(level == "CRITICAL")):
                for item in clauses:
                    st.markdown(f"**Category:** `{item['category'].upper()}`")
                    st.markdown(f"> \"{item['original_text']}\"")
                    st.warning(f"**Rationale:** {item['rationale']}")
                    st.divider()

        # C. The PDF Report Generation Bridge
        st.markdown("Formal Audit Report")
        if st.button("Generate & Download PDF"):
            with st.spinner("Compiling legal citations into PDF..."):
                report_payload = {
                    "grouped_analysis": analysis,
                    "filename": uploaded_file.name
                }
                report_resp = requests.post(f"{API_BASE_URL}/generate_report", json=report_payload)
                
                if report_resp.status_code == 200:
                    st.download_button(
                        label="Save Audit PDF",
                        data=report_resp.content,
                        file_name=f"LICE_Audit_{uploaded_file.name}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Failed to generate PDF. Check backend report_generator logs.")
    else:
        st.error("Engine Data Mismatch: The API response format is missing 'summary' or 'analysis' keys.")
        st.json(res) # Show raw data for debugging