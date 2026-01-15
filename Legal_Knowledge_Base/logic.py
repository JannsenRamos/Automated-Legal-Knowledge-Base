import os, re, psycopg2, fitz
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 1. SETUP
load_dotenv('api_keys.env')
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL") 

# 2. DATA MODELS
class LaborArticleChunk(BaseModel):
    article_number: int
    old_article_number: Optional[int] = None
    title: str
    content: str
    is_repealed: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# SELECTIVE INDEXING RULES
ROUTING_RULES = {
    "wages": ["wage", "salary", "pay", "overtime", "payroll", "deduction"],
    "contracts": ["contract", "dismissal", "termination", "probationary"],
}

# 3. GATEKEEPER & PARSING
def parse_and_validate(uploaded_file, api_key):
    # EXCEPTION: File Format Check
    if not uploaded_file.name.lower().endswith('.pdf'):
        raise ValueError("Unsupported format. Please upload a PDF.")

    llm = ChatOpenAI(model="openai/gpt-oss-120b:free", api_key=api_key, base_url="https://openrouter.ai/api/v1")
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    
    # EXCEPTION: AI Content Check
    sample = doc[0].get_text()[:800]
    prompt = f"Is this a Labor Code or Legal Text? Reply 'VALID' or 'INVALID'. Sample: {sample}"
    if "INVALID" in llm.invoke(prompt).content.upper():
        raise ValueError("AI rejected content: This is not a legal document.")

    # PARSING ENGINE
    pattern = r"ART\.\s+(\d+)(?:\s+\[(\d+)\])?"
    full_text = "".join([p.get_text() for p in doc])
    parts = re.split(pattern, full_text)
    
    validated_chunks = []
    for i in range(1, len(parts), 3):
        try:
            art_num, old_num, content = parts[i], parts[i+1], parts[i+2].strip()
            # Category Routing
            category = "general"
            for cat, kw in ROUTING_RULES.items():
                if any(k in content.lower() for k in kw): category = cat; break

            # SCHEMA VALIDATION
            chunk = LaborArticleChunk(
                article_number=int(art_num),
                old_article_number=int(old_num) if old_num else None,
                title=content.split('\n')[0][:100],
                content=content,
                is_repealed="repealed" in content.lower()
            )
            validated_chunks.append((category, chunk))
        except (ValidationError, ValueError): continue
            
    return validated_chunks

# 4. SUPABASE COMMIT
def save_to_supabase(data_list):
    conn = psycopg2.connect(SUPABASE_DB_URL)
    cursor = conn.cursor()
    for category, chunk in data_list:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {category} (id SERIAL PRIMARY KEY, art_num INT, title TEXT, full_json JSONB)")
        cursor.execute(f"INSERT INTO {category} (art_num, title, full_json) VALUES (%s, %s, %s)",
                       (chunk.article_number, chunk.title, chunk.model_dump_json()))
    conn.commit()
    cursor.close(); conn.close()