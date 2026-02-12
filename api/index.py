import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from generate_report.report_generator import generate_pdf_report


# 1. INITIALIZATION: Load .env before importing logic that might use it
load_dotenv()

# Import your LICE logic and models
# Ensure these are correctly referenced based on your folder structure
from .logic_helpers import segment_contract_clauses, audit_contract

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
    text = content_bytes.decode('utf-8', errors='ignore')
    
    # 1. SEGMENT & CLASSIFY
    clauses = segment_contract_clauses(text, jurisdiction)

    # 2. AUDIT (This creates the 'results' list)
    results = audit_contract(clauses, DB_URL)

    # 3. GROUPING (This creates the 'grouped_analysis' variable)
    grouped_analysis = {
        "CRITICAL": [c for c in results if c.risk_score == "CRITICAL"],
        "HIGH": [c for c in results if c.risk_score == "HIGH"],
        "MEDIUM": [c for c in results if c.risk_score == "MEDIUM"],
        "LOW": [c for c in results if c.risk_score == "LOW"]
    }

    # 4. SUMMARY (This creates the 'summary' variable)
    summary = {
        "total_clauses": len(results),
        "critical_count": len(grouped_analysis["CRITICAL"]),
        "is_compliant": len(grouped_analysis["CRITICAL"]) == 0
    }

    # 5. RETURN (Now the variables are defined!)
    return {
        "filename": file.filename,
        "summary": summary,
        "analysis": grouped_analysis
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