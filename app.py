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

# ── Custom CSS ─────────────────────────────────────────────────────────────────
# Split into two calls: Streamlit's parser can choke on <link>+<style> in one block
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

_CSS = """
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.lice-hero {
    background: linear-gradient(135deg, #0f1b36 0%, #1a3363 60%, #1e4d8c 100%);
    border-radius: 16px;
    padding: 42px 48px;
    margin-bottom: 32px;
    color: white;
}
.lice-hero h1 { font-size: 2.4rem; font-weight: 700; margin: 0 0 6px 0; letter-spacing: -0.5px; }
.lice-hero p  { font-size: 1.05rem; opacity: 0.8; margin: 0 0 20px 0; }
.lice-hero ul { margin: 0; padding-left: 20px; opacity: 0.9; line-height: 2; }

[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 18px 22px;
    border: 1px solid #e8edf4;
    border-left: 4px solid #1a3363;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

[data-testid="stExpander"] {
    border: 1px solid #e8edf4;
    border-radius: 12px;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-left: 8px;
}
.badge-low      { background:#d4edda; color:#155724; }
.badge-medium   { background:#fff3cd; color:#856404; }
.badge-high     { background:#ffe0b2; color:#7c4700; }
.badge-critical { background:#f8d7da; color:#721c24; }

.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #6c757d;
    margin-bottom: 12px;
}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def risk_tier(score: float) -> tuple[str, str]:
    """Return (label, badge_class) for a given numeric risk score."""
    if score >= 8:
        return "Critical", "badge-critical"
    elif score >= 5:
        return "High", "badge-high"
    elif score >= 2:
        return "Medium", "badge-medium"
    else:
        return "Low", "badge-low"

def avg_status(avg: float) -> tuple[str, str]:
    """Return (status_label, streamlit_color) for display in the header."""
    if avg > 8:
        return "CRITICAL VIOLATION", "red"
    elif avg > 5:
        return "HIGH RISK", "orange"
    elif avg > 2:
        return "MEDIUM RISK", "blue"
    else:
        return "LOW RISK / COMPLIANT", "green"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ LICE Engine")
    st.caption("Legal Intelligence & Compliance Engine")
    st.divider()

    # Placeholder — will be replaced after analysis
    jurisdiction_display = st.empty()

    if "detected_jurisdiction" not in st.session_state:
        jurisdiction_display.selectbox(
            "Target Jurisdiction",
            ["HK", "PH"],
            help="This will be auto-detected from the uploaded document.",
            key="sidebar_jur"
        )
    else:
        jurisdiction_display.success(
            f"🌐 Auto-Detected: **{st.session_state.detected_jurisdiction}**"
        )

    st.divider()
    st.markdown("### 🗺️ Risk Score Legend")
    st.markdown("""
    | Range | Tier |
    |---|---|
    | 0 – 2 | 🟢 Low / Compliant |
    | 2 – 5 | 🟡 Medium Risk |
    | 5 – 8 | 🟠 High Risk |
    | 8 – 10 | 🔴 Critical |
    """)
    st.caption("Score = (1 − Similarity) × Severity Weight")


# ── Hero / Welcome Section ────────────────────────────────────────────────────
if "report" not in st.session_state or not st.session_state.report:
    st.markdown("""
    <div class="lice-hero">
        <h1>⚖️ LICE — Legal Intelligence &amp; Compliance Engine</h1>
        <p>Hybrid risk modeling for OFW employment contracts</p>
        <ul>
            <li>Upload a PDF or text contract to begin automated clause analysis</li>
            <li>Jurisdiction is auto-detected (HK Cap. 57 or PH Labor Code)</li>
            <li>Each clause is scored against statutory labor floors via semantic similarity</li>
            <li>Download a formal audit PDF report when analysis is complete</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:linear-gradient(90deg,#0f1b36,#1a3363);border-radius:12px;
                padding:20px 32px;margin-bottom:24px;color:white;">
        <h2 style="margin:0;font-size:1.5rem;font-weight:700;">
            ⚖️ LICE — Legal Intelligence &amp; Compliance Engine
        </h2>
        <p style="margin:4px 0 0;opacity:0.75;font-size:0.9rem;">
            Hybrid Risk Modeling for OFW Employment Contracts
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── File Upload ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("📄 Upload Contract (PDF or Text)", type=['pdf', 'txt'])

if uploaded_file:
    if st.button("🔍 Run Risk Analysis", use_container_width=False, type="primary"):
        with st.spinner("Analyzing document…"):
            file_bytes = uploaded_file.read()
            raw_text, jurisdiction = get_text_and_jurisdiction(file_bytes, uploaded_file.name)
            st.session_state.detected_jurisdiction = jurisdiction
            report = analyze_contract_risk(raw_text, jurisdiction, "legal_rules.json")
            st.session_state.report = report
        st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
if "report" in st.session_state and st.session_state.report:
    report = st.session_state.report

    # ── A. Key Metrics ──
    n_clauses = len(report.analysis)
    avg_risk   = report.total_risk / n_clauses if n_clauses else 0
    compliance = max(0, 100 - int(report.total_risk))
    status_label, status_color = avg_status(avg_risk)

    m1, m2, m3 = st.columns(3)
    m1.metric("Compliance Score",  f"{compliance}%")
    m2.metric("Total Risk Weight", f"{report.total_risk:.2f}")
    m3.metric("Avg Risk / Clause", f"{avg_risk:.2f}")

    st.markdown(f"### Overall Audit Status: :{status_color}[{status_label}]")
    st.divider()

    # ── B. Visualizations ──
    df_data = [
        {
            "Category":   c.category,
            "Risk":       c.risk_score,
            "Confidence": c.confidence,
            "Tier":       risk_tier(c.risk_score)[0],
        }
        for c in report.analysis
    ]
    df = pd.DataFrame(df_data)

    # Risk tier counts for donut
    tier_order  = ["Low", "Medium", "High", "Critical"]
    tier_colors = {"Low": "#28a745", "Medium": "#ffc107",
                   "High": "#fd7e14", "Critical": "#dc3545"}
    tier_counts = (
        df["Tier"]
        .value_counts()
        .reindex(tier_order, fill_value=0)
        .reset_index()
    )
    tier_counts.columns = ["Tier", "Count"]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<p class="section-label">Risk by Clause</p>', unsafe_allow_html=True)
        fig_bar = px.bar(
            df, x="Category", y="Risk", color="Risk",
            color_continuous_scale=["#28a745", "#ffc107", "#fd7e14", "#dc3545"],
            title="Weighted Risk Score by Clause Category",
        )
        fig_bar.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            margin=dict(t=48, b=0, l=0, r=0),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown('<p class="section-label">Risk Distribution</p>', unsafe_allow_html=True)
        fig_donut = px.pie(
            tier_counts, names="Tier", values="Count",
            color="Tier", hole=0.5,
            color_discrete_map=tier_colors,
            category_orders={"Tier": tier_order},
            title="Clause Risk Tier Distribution",
        )
        fig_donut.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            margin=dict(t=48, b=0, l=0, r=0),
        )
        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_donut, use_container_width=True)

    st.divider()

    # ── C. Confidence scatter (full width) ──
    st.markdown('<p class="section-label">Model Confidence</p>', unsafe_allow_html=True)
    fig_scatter = px.scatter(
        df, x="Category", y="Confidence", size="Risk", color="Tier",
        color_discrete_map=tier_colors,
        title="Model Confidence vs Detected Risk",
        size_max=30,
    )
    fig_scatter.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Inter",
        margin=dict(t=48, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # ── D. Detailed Clause Audit Trail ──
    st.markdown("### 📋 Detailed Clause Analysis")
    for item in report.analysis:
        tier_label, badge_cls = risk_tier(item.risk_score)
        expander_title = (
            f"{item.category.upper()}  —  Risk: {item.risk_score:.2f}"
            f'  <span class="badge {badge_cls}">{tier_label}</span>'
        )
        with st.expander(item.category.upper()):
            st.markdown(
                f'**{item.category.upper()}** &nbsp; '
                f'<span class="badge {badge_cls}">{tier_label}</span> &nbsp; '
                f'Risk Score: **{item.risk_score:.2f}**',
                unsafe_allow_html=True,
            )
            st.divider()
            st.markdown("**Extracted Contract Text:**")
            st.caption(f'"{item.extracted_text}"')
            st.info(f"**Legal Reference:** {item.violation_type}")
            st.markdown("**Model Confidence:**")
            st.progress(item.confidence)
            st.caption(f"{item.confidence * 100:.1f}%")
            if item.rationale:
                st.markdown("**AI Rationale:**")
                st.markdown(f"> {item.rationale}")

    st.divider()

    # ── E. PDF Download (single-button flow) ──
    st.markdown("### 📥 Export Audit Report")
    fname = uploaded_file.name if uploaded_file else "contract"
    pdf_bytes = generate_pdf_report(report, fname)
    st.download_button(
        label="⬇️ Download Formal Audit Report (PDF)",
        data=pdf_bytes,
        file_name=f"LICE_Audit_{fname}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )