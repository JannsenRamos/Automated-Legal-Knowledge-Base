import os
from fpdf import FPDF
from datetime import datetime

class LICEReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'LICE: Employment Contract Audit Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Audit Date: {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'R')
        self.ln(10)

    def footer(self):
        """Adds page numbers and a legal disclaimer."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | LICE Engine | Confidential Legal Audit', 0, 0, 'C')

def generate_pdf_report(grouped_analysis, filename):

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, "reports")
    
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        print(f"Created missing reports directory at: {reports_dir}")

    pdf = LICEReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title Section
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Analysis for: {filename}", 0, 1)
    pdf.ln(5)

    # Define risk priorities for the report
    for risk_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        clauses = grouped_analysis.get(risk_level, [])
        if not clauses:
            continue
            
        # Style the risk headers
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"{risk_level} RISKS FOUND: {len(clauses)}", 0, 1)
        
        for i, clause in enumerate(clauses):
            category = clause.get('category', 'N/A').upper()
            text = clause.get('original_text', 'No text found')
            rationale = clause.get('rationale', 'No rationale provided')

            pdf.set_font('Arial', 'B', 10)
            pdf.multi_cell(0, 8, f"Section: {category}")
            
            pdf.set_font('Arial', '', 10)
            pdf.set_fill_color(245, 245, 245)
            pdf.multi_cell(0, 8, f"Contract Text: \"{text}\"", fill=True)
            
            pdf.set_font('Arial', 'I', 10)
            pdf.multi_cell(0, 8, f"Rationale & Citation: {rationale}")
            pdf.ln(5)
            
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"LICE_{timestamp}.pdf"
    report_path = os.path.join(reports_dir, report_filename)
    
    pdf.output(report_path)
    return report_path