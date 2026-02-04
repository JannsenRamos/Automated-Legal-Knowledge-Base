from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from .logic_helpers import extract_legal_text, segment_contract_clauses, audit_contract

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to LICE: Legal Intelligence & Compliance Engine", "docs": "/docs"}

# Enable CORS for your local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze_contract")
async def analyze_contract(file: UploadFile = File(...), jurisdiction: str = "HK"):
    """
    The main LICE endpoint: Upload a contract, get a Risk Audit.
   
    """
    try:
        # 1. Read the uploaded file
        content = await file.read()
        
        # 2. Trigger the Hybrid Ingestion (with Tesseract Fallback)
        print(f"Processing upload: {file.filename}")
        raw_text = extract_legal_text(content, file.filename)
        
        # 3. Segment into Semantic Clauses
        clauses = segment_contract_clauses(raw_text, jurisdiction)
        
        # 4. Run the Audit against Supabase Baseline
        db_url = os.getenv("SUPABASE_DB_URL")
        audited_results = audit_contract(clauses, db_url)
        
        # 5. Return JSON to the Frontend
        return {
            "filename": file.filename,
            "jurisdiction": jurisdiction,
            "total_clauses": len(audited_results),
            "analysis": [res.dict() for res in audited_results]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "LICE Engine Online", "jurisdiction": ["PH", "HK"]}