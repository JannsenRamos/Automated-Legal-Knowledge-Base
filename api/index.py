import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException

# Package-aware import to find your helpers
try:
    from api.logic_helpers import parse_and_validate, save_to_supabase
except ImportError:
    from logic_helpers import parse_and_validate, save_to_supabase

# Robust .env loading
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI()

@app.get("/api/health")
def health():
    return {
        "status": "Backend Active",
        "env_check": {
            "api_key_loaded": bool(os.getenv("OPENROUTER_API_KEY")),
            "db_url_loaded": bool(os.getenv("SUPABASE_DB_URL"))
        }
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 1. Read the file into memory once
        pdf_bytes = await file.read()
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        db_url = os.getenv("SUPABASE_DB_URL")
        
        # 2. Reset the file pointer for the next operation (Optional but safe)
        await file.seek(0)
        
        # 3. Pass the bytes to your notebook logic
        # Inside parse_and_validate, we use fitz.open(stream=pdf_bytes)
        chunks = parse_and_validate(pdf_bytes, api_key)
        
        if not chunks:
            # This is where your current error is triggering
            print("WARNING: Regex found 0 articles. Check the PDF text content.")
            raise HTTPException(status_code=400, detail="Regex failed to find articles.")

        save_to_supabase(chunks, db_url)
        return {"success": True, "articles": [c.model_dump() for c in chunks]}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))