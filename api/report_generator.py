from fpdf import FPDF
import io
from datetime import datetime

def generate_pdf_report(report_data, filename):
    """
    World-class PDF report generator for LICE.
    Implements dynamic layout calculations to prevent text overflow.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- 1. HEADER SECTION ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LICE: Legal Intelligence & Compliance Audit", new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    # --- 2. SUMMARY SECTION ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Audit Report: {filename}", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    # Synchronize Status Label with Risk Score
    # 0-2: Low, 2-5: Medium, 5-8: High, 8+: Critical
    total_risk = report_data.total_risk
    if total_risk >= 8.0:
        status_text = "CRITICAL VIOLATION"
        status_color = (200, 0, 0)
    elif total_risk >= 5.0:
        status_text = "HIGH RISK"
        status_color = (255, 140, 0)
    else:
        status_text = "COMPLIANT / LOW RISK"
        status_color = (0, 128, 0)

    pdf.set_text_color(*status_color)
    pdf.cell(0, 10, f"System Status: {status_text}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_text_color(0, 0, 0) # Reset to black
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total Risk Weight: {total_risk:.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # --- 3. DETAILED CLAUSE ANALYSIS ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Detailed Clause Analysis", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    for item in report_data.analysis:
        # A. Category Header
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(pdf.epw, 8, f"Category: {item.category.upper()}", new_x="LMARGIN", new_y="NEXT")
        
        # B. Risk & Confidence Metrics
        risk_color = (200, 0, 0) if item.risk_score > 5.0 else (0, 100, 0)
        pdf.set_text_color(*risk_color)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(pdf.epw, 6, f"Risk Score: {item.risk_score} (Confidence: {item.confidence*100:.1f}%)", 
                 new_x="LMARGIN", new_y="NEXT")
        
        # C. Statutory Reference
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 9)
        # Using multi_cell for legal refs that might be long
        pdf.multi_cell(pdf.epw, 6, f"Statutory Reference: {item.violation_type}", new_x="LMARGIN", new_y="NEXT")
        
        # D. Rationale
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(pdf.epw, 5, f"Rationale: {item.rationale}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # E. THE FIX: Extracted Text (The Blockquote)
        # We ensure it stays within the 'Effective Page Width' (epw)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_fill_color(248, 249, 250)
        
        # Add 5mm left padding for the blockquote indent
        pdf.set_x(pdf.get_x() + 5)
        
        # Width is epw minus the 5mm indent and 5mm right buffer
        quote_width = pdf.epw - 10
        
        # Multi-cell automatically handles word wrapping to prevent horizontal overflow
        pdf.multi_cell(
            w=quote_width,
            h=5,
            txt=f"Contract Evidence: \"{item.extracted_text.strip()}\"",
            border=0,
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT"
        )
        
        # F. Divider
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 10 + pdf.epw, pdf.get_y())
        pdf.ln(5)

    # --- 4. FOOTER ---
    pdf.set_y(-25)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, "Disclaimer: This AI-generated audit is for informational purposes only and does not constitute formal legal advice. Please consult with the POEA, DMW, or a qualified attorney.", align='C')

    # Return as bytes for Streamlit download button
    return bytes(pdf.output(dest="S"))