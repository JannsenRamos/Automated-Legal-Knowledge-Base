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
    """
    Takes the grouped analysis and outputs a formatted PDF file.
    """
    # Ensure a reports directory exists
    if not os.path.exists("reports"):
        os.makedirs("reports")

    pdf = LICEReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title Section
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Analysis for: {filename}", 0, 1)
    pdf.ln(5)

    # Define risk priorities for the report
    priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    for risk_level in priorities:
        clauses = grouped_analysis.get(risk_level, [])
        if not clauses:
            continue
            
        # Color Coding: Red for Critical, Orange for High
        if risk_level == "CRITICAL": pdf.set_text_color(220, 20, 60)
        elif risk_level == "HIGH": pdf.set_text_color(255, 140, 0)
        else: pdf.set_text_color(0, 0, 0)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"{risk_level} RISKS FOUND: {len(clauses)}", 0, 1)
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0) # Reset to black
        
        for i, clause in enumerate(clauses):
            pdf.set_font('Arial', 'B', 10)
            pdf.multi_cell(0, 8, f"Section: {clause.category.upper()}")
            
            pdf.set_font('Arial', '', 10)
            pdf.set_fill_color(245, 245, 245) # Light grey background for the quote
            pdf.multi_cell(0, 8, f"Contract Text: \"{clause.original_text}\"", fill=True)
            
            pdf.set_font('Arial', 'I', 10)
            pdf.multi_cell(0, 8, f"Rationale & Citation: {clause.rationale}")
            pdf.ln(5)
            
    report_filename = f"reports/LICE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(report_filename)
    return report_filename