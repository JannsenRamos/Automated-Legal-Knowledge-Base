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
        await file.seek(0)
        content = await file.read()
        
        # Pull the key from the environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        db_url = os.getenv("SUPABASE_DB_URL")
        
        # FIX: Pass BOTH content and api_key
        chunks = parse_and_validate(content, api_key)
        
        save_to_supabase(chunks, db_url)
        
        return {
            "success": True, 
            "articles": [c.model_dump() for c in chunks]
        }
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))