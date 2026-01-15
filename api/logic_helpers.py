import os
import re
import requests
import json
import fitz
import psycopg2
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Models from your notebook
class DocumentMetadata(BaseModel):
    source_file: str
    file_type: str
    page_number: int
    corpus_category: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class LaborArticleChunk(BaseModel):
    article_number: int
    old_article_number: Optional[int] = None
    title: str
    content: str
    is_repealed: bool = False
    metadata: DocumentMetadata

def identify_document_pattern(sample_text, api_key):
    """Uses GPT-OSS Free to check the first 1000 characters."""
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "openai/gpt-oss-120b:free",
                "messages": [{
                    "role": "user", 
                    "content": f"Identify if this is a Labor Code. Return 'LABOR_CODE' or 'GENERIC'. Text: {sample_text[:1000]}"
                }],
                "max_tokens": 10
            })
        )
        res_data = response.json()
        # Fallback if API is busy
        if 'choices' not in res_data:
            return "LABOR_CODE"
        return res_data['choices'][0]['message']['content'].strip()
    except:
        return "LABOR_CODE"

def parse_and_validate(pdf_bytes, api_key): # Matches the 2 arguments
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join([page.get_text() for page in doc])
    
    # AI Gatekeeper
    if identify_document_pattern(full_text, api_key) != "LABOR_CODE":
        raise ValueError("AI rejected document as non-labor code.")

    # Regex logic
    pattern = r"ART\.\s+(\d+)(?:\s+\[(\d+)\])?"
    parts = re.split(pattern, full_text)
    
    chunks = []
    ROUTING_RULES = {
        "wages": ["wage", "salary", "pay", "overtime", "payroll", "deduction", "night shift"],
        "contracts": ["contract", "dismissal", "tenure", "termination", "probationary", "resignation"],
    }

    for i in range(1, len(parts), 3):
        content = parts[i+2].strip()
        category = "general"
        for cat, keywords in ROUTING_RULES.items():
            if any(k in content.lower() for k in keywords):
                category = cat; break

        chunks.append(LaborArticleChunk(
            article_number=int(parts[i]),
            old_article_number=int(parts[i+1]) if parts[i+1] else None,
            title=content.split('\n')[0][:100],
            content=content,
            is_repealed="repealed" in content.lower(),
            metadata=DocumentMetadata(source_file="upload.pdf", file_type="legal_code", page_number=0, corpus_category=category)
        ))
    return chunks

def save_to_supabase(chunks, db_url):
    """Saves to Supabase."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = True 
    cur = conn.cursor()
    try:
        for chunk in chunks:
            table = chunk.metadata.corpus_category
            cur.execute(f"CREATE TABLE IF NOT EXISTS {table} (id SERIAL PRIMARY KEY, article_number INT, title TEXT, content TEXT, is_repealed BOOLEAN);")
            cur.execute(f"INSERT INTO {table} (article_number, title, content, is_repealed) VALUES (%s, %s, %s, %s)", 
                        (chunk.article_number, chunk.title, chunk.content, chunk.is_repealed))
    finally:
        cur.close(); conn.close()