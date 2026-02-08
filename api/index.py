import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
    """
    Main Analysis Endpoint:
    1. Receives File -> 2. Segments/Classifies -> 3. Audits against Supabase
    """
    # Defensive check for the error you encountered
    if not DB_URL:
        raise HTTPException(
            status_code=500, 
            detail="Server Config Error: SUPABASE_DB_URL is missing from .env"
        )

    print(f"Processing upload: {file.filename}")
    
    try:
        # Read the file content
        content_bytes = await file.read()
        
        # Determine decoding based on file extension
        filename = file.filename.lower()
        if filename.endswith(".txt"):
            text = content_bytes.decode('utf-8', errors='ignore')
        else:
            text = content_bytes.decode('utf-8', errors='ignore') 
            # For PDFs, you would implement the logic from logic_helpers to extract text
        clauses = segment_contract_clauses(text, jurisdiction)

        # This compares each block to the laws in my database and returns a list of results with compliance status and deviation notes
        results = audit_contract(clauses, DB_URL)

        return {
            "filename": file.filename,
            "jurisdiction": jurisdiction,
            "clause_count": len(results),
            "analysis": results
        }

    except Exception as e:
        print(f"Analysis Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")