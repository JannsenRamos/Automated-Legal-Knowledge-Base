import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .report_generator import generate_pdf_report


# 1. INITIALIZATION: Load .env before importing logic that might use it
load_dotenv()

# Import your LICE logic and models
# Ensure these are correctly referenced based on your folder structure
from .logic_helpers import segment_contract_clauses, analyze_contract_risk

app = FastAPI(title="LICE Engine: Legal Intelligence & Compliance Engine")

# CORS Middleware (Preparing for your Streamlit/FastAPI UI in Week 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fetch the DB URL once at startup
DB_URL = os.getenv("SUPABASE_DB_URL")

@app.get("/")
def read_root():
    return {"message": "LICE Engine is live.", "docs": "/docs"}

@app.get("/health")
def health_check():
    """Verifies that the API can 'see' the environment variables."""
    return {
        "status": "healthy",
        "database_configured": bool(DB_URL),
        "jurisdictions_supported": ["HK", "PH"]
    }

@app.post("/analyze_contract")
async def analyze_contract(file: UploadFile = File(...), jurisdiction: str = "HK"):
    content_bytes = await file.read()

    # 1. EXTRACT TEXT & DETECT JURISDICTION
    from .pdf_processor import get_text_and_jurisdiction
    chunks, detected_jurisdiction = get_text_and_jurisdiction(content_bytes, file.filename)
    active_jurisdiction = detected_jurisdiction if detected_jurisdiction != "UNKNOWN" else jurisdiction

    # 2. ANALYZE (Semantic risk scoring via SentenceTransformer)
    report = analyze_contract_risk(chunks, active_jurisdiction, "legal_rules.json")

    # 3. SUMMARY
    critical_clauses = [c for c in report.analysis if c.risk_score >= 8.0]
    summary = {
        "total_clauses": len(report.analysis),
        "critical_count": len(critical_clauses),
        "total_risk": report.total_risk,
        "detected_jurisdiction": active_jurisdiction,
        "is_compliant": len(critical_clauses) == 0
    }

    return {
        "filename": file.filename,
        "summary": summary,
        "analysis": [c.model_dump() for c in report.analysis]
    }
    
from fastapi import Body # Add this import at the top

@app.post("/generate_report")
async def report_endpoint(grouped_analysis: dict = Body(...), filename: str = Body(...)):
    """
    Uses Body(...) to ensure FastAPI correctly parses the incoming JSON payload.
    """
    try:
        path = generate_pdf_report(grouped_analysis, filename)
        return FileResponse(
            path, 
            media_type='application/pdf', 
            filename=f"LICE_Audit_{filename}.pdf"
        )
    except Exception as e:
        print(f"PDF Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))