import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from logic_helpers import parse_and_validate, save_to_supabase


env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI()

@app.get("/api/health")
def health():
    return {
        "status": "Backend Active",
        "env_check": {
            # These should now return 'true' after the fix
            "api_key_loaded": bool(os.getenv("OPENROUTER_API_KEY")),
            "db_url_loaded": bool(os.getenv("SUPABASE_DB_URL"))
        }
    }

# 2. YOUR PARSER ROUTE
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        db_url = os.getenv("SUPABASE_DB_URL")
        
        # 1. READ THE FILE BYTES
        file_content = await file.read() 
        
        # 2. PASS BYTES TO PARSER
        # Ensure your logic_helpers.py can handle bytes/stream!
        chunks = parse_and_validate(file_content, api_key)
        save_to_supabase(chunks, db_url)
        
        return {"success": True, "count": len(chunks)}
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}") # This prints to your terminal logs
        raise HTTPException(status_code=400, detail=str(e))