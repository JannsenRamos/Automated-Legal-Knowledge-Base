from fpdf import FPDF
from datetime import datetime
from api import FullContractReport

class LICEReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "LICE: Legal Intelligence & Compliance Audit", border=False, ln=1, align="C")
        self.set_draw_color(0, 80, 180)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | Generated on {datetime.now().strftime('%Y-%m-%d')}", align="C")

def generate_pdf_report(report_data: FullContractReport, filename: str):
    """
    MLE Logic: Converts the Pydantic analysis object into a formal PDF artifact.
    """
    pdf = LICEReport()
    pdf.add_page()
    
    # 1. Executive Summary
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Audit Report: {filename}", ln=1)
    
    pdf.set_font("Arial", "", 12)
    status = "NON-COMPLIANT" if report_data.total_risk > 15 else "COMPLIANT"
    pdf.cell(0, 10, f"System Status: {status}", ln=1)
    pdf.cell(0, 10, f"Total Risk Weight: {report_data.total_risk}", ln=1)
    pdf.ln(5)

    # 2. Detailed Findings
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, "Detailed Clause Analysis", ln=1, fill=True)
    pdf.ln(5)

    for item in report_data.analysis:
        # Categorization and Risk
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"Category: {item.category.upper()}", ln=1)
        
        # Risk Score Highlight
        if item.risk_score > 5.0:
            pdf.set_text_color(255, 0, 0) # Red for high risk
        else:
            pdf.set_text_color(0, 0, 0)
            
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 8, f"Risk Score: {item.risk_score} (Confidence: {item.confidence*100:.1f}%)", ln=1)
        pdf.set_text_color(0, 0, 0) # Reset to black

        # The 'Why' (Legal Reference)
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 6, f"Legal Reference: {item.violation_type}")
        
        # Extracted Text
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 5, f"Extracted Text: \"{item.extracted_text[:300]}...\"")
        
        pdf.ln(5)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1', errors='ignore')