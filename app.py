import streamlit as st
import pandas as pd
import plotly.express as px
from api import extract_legal_text, analyze_contract_risk, get_text_and_jurisdiction
from api import generate_pdf_report

st.set_page_config(
    page_title="LICE Engine: Legal Audit",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a professional "Legal Tech" look
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .stExpander { border: 1px solid #e0e0e0; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("LICE: Legal Intelligence & Compliance Engine")
st.markdown("### Hybrid Risk Modeling for OFW Employment Contracts")
st.divider()

# 2. Sidebar Settings
with st.sidebar:
    st.header("Configuration")
    jurisdiction = st.selectbox(
        "Target Jurisdiction", 
        ["HK", "PH"], 
        help="Select the statutory baseline (e.g., HK Cap. 57 vs PH Labor Code)."
    )
    st.info("The system uses Semantic Similarity to detect deviations from mandatory labor floors.")

# 3. File Upload Section
uploaded_file = st.file_uploader("Upload Contract (PDF or Text)", type=['pdf', 'txt'])

if uploaded_file:
    if st.button("Run Risk Analysis"):
        with st.spinner("Analyzing document context..."):
            file_bytes = uploaded_file.read()
            
            # 1. Automatic Detection
            raw_text, jurisdiction = get_text_and_jurisdiction(file_bytes, uploaded_file.name)
            
            # 2. Inform the user
            st.info(f"Detected Jurisdiction: **{jurisdiction}**")
            
            # 3. Analyze
            report = analyze_contract_risk(raw_text, jurisdiction, "legal_rules.json")
            st.session_state.report = report

# 4. Display Results (Using the Pydantic Object)
if 'report' in st.session_state and st.session_state.report:
    report = st.session_state.report
    
    # A. High-Level Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Compliance Score", f"{max(0, 100 - int(report.total_risk))}%")
    m2.metric("Total Risk Weight", f"{report.total_risk:.2f}")
    
    status = "HIGH RISK" if report.total_risk > 15 else "LOW RISK"
    m3.subheader(f"Status: {status}")

    st.divider()

    # B. DATA SCIENCE VISUALIZATION (Showcase your DS skill)
    col1, col2 = st.columns([1, 1])
    
    # Convert list of Pydantic objects to a DataFrame for Plotly
    df_data = [
        {"Category": c.category, "Risk": c.risk_score, "Confidence": c.confidence} 
        for c in report.analysis
    ]
    df = pd.DataFrame(df_data)

    with col1:
        st.write("### Risk Heatmap")
        fig = px.bar(df, x="Category", y="Risk", color="Risk",
                     color_continuous_scale="Reds", title="Weighted Risk by Clause")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("### Extraction Confidence")
        fig2 = px.scatter(df, x="Category", y="Confidence", size="Risk", color="Category",
                          title="Model Confidence vs. Detected Risk")
        st.plotly_chart(fig2, use_container_width=True)

    # C. DETAILED AUDIT TRAIL
    st.write("### Detailed Clause Analysis")
    for item in report.analysis:
        with st.expander(f"Category: {item.category.upper()} (Risk: {item.risk_score})"):
            st.markdown(f"**Extracted Text:**")
            st.caption(f"\"{item.extracted_text}\"")
            st.info(f"**Legal Reference:** {item.violation_type}")
            st.progress(item.confidence)
            st.caption(f"Model Confidence: {item.confidence*100:.1f}%")

    # D. REPORT GENERATION
    # Inside app.py (bottom section)
    if st.button("Download Formal Audit Report"):
        pdf_bytes = generate_pdf_report(report, uploaded_file.name)
        st.download_button(
            label="Save PDF",
            data=pdf_bytes,
            file_name=f"LICE_Audit_{uploaded_file.name}.pdf",
            mime="application/pdf"
        )