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
    """Uses GPT-OSS Free with improved prompt and fuzzy matching."""
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
                    "content": (
                        "Task: Determine if the following text is from a Philippine Labor Code. "
                        "Respond with ONLY the word 'LABOR_CODE' if it is, or 'GENERIC' if it is not. "
                        f"Text: {sample_text[:1000]}"
                    )
                }],
                "max_tokens": 500
            })
        )
        res_data = response.json()
        
        # Pull the content and clean it
        ai_reply = res_data['choices'][0]['message']['content'].strip().upper()
        print(f"DEBUG: AI said: '{ai_reply}'") # See the exact response in terminal
        
        # FUZZY MATCH: If it contains 'LABOR_CODE', let it through
        if "LABOR_CODE" in ai_reply:
            return "LABOR_CODE"
            
        return "GENERIC"
    except Exception as e:
        print(f"Router Error (Passing through to Regex): {e}")
        return "LABOR_CODE" # If AI is down, trust the Regex instead
    
def parse_and_validate(pdf_bytes, api_key):
    # 1. Open and extract text
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join([page.get_text() for page in doc])
    
    # 2. Text Normalization: Remove non-breaking spaces (\xa0)
    full_text = full_text.replace('\xa0', ' ').replace('\t', ' ')
    
    # AI Gatekeeper
    if identify_document_pattern(full_text, api_key) != "LABOR_CODE":
        raise ValueError("AI rejected document as non-labor code.")

    # 3. Robust Regex Pattern
    # (?i) = Case-insensitive
    # ART\.?\s* = Matches "ART", "ART.", "Art", "Art." followed by optional space
    # (\d+) = Captures the article number
    # (?:\s*\[(\d+)\])? = Captures optional old article number in brackets
    pattern = r"(?i)ART\.?\s*(\d+)(?:\s*\[(\d+)\])?"
    
    parts = re.split(pattern, full_text)
    
    # Validation check for the split
    if len(parts) <= 1:
        print(f"DEBUG: Still no matches. Text preview: {full_text[500:1000]}")
        return []

    chunks = []
    ROUTING_RULES = {
        "wages": ["wage", "salary", "pay", "overtime", "payroll", "deduction", "night shift"],
        "contracts": ["contract", "dismissal", "tenure", "termination", "probationary", "resignation"],
    }

    # Re-looping with the 3-part split structure
    for i in range(1, len(parts), 3):
        art_num = parts[i]
        old_num = parts[i+1]
        content = parts[i+2].strip() if (i+2) < len(parts) else ""
        
        if not content: continue

        # Determine category based on keywords
        category = "general"
        for cat, keywords in ROUTING_RULES.items():
            if any(k in content.lower() for k in keywords):
                category = cat
                break

        chunks.append(LaborArticleChunk(
            article_number=int(art_num),
            old_article_number=int(old_num) if old_num else None,
            title=content.split('\n')[0][:100],
            content=content,
            is_repealed="repealed" in content.lower(),
            metadata=DocumentMetadata(
                source_file="upload.pdf", 
                file_type="legal_code", 
                page_number=0, 
                corpus_category=category
            )
        ))
    
    print(f"DEBUG: Extracted {len(chunks)} articles.")
    return chunks

def save_to_supabase(chunks, db_url):
    """Saves to Supabase and automatically creates tables based on notebook categories."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = True 
    cur = conn.cursor()
    try:
        for chunk in chunks:
            # Use the corpus_category from metadata to determine the table name
            table = chunk.metadata.corpus_category
            
            # 1. Create the table with the specific columns from your notebook
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id SERIAL PRIMARY KEY, 
                    article_number INT, 
                    old_article_number INT, 
                    title TEXT, 
                    content TEXT, 
                    is_repealed BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 2. Insert the data including the old_article_number mapping
            cur.execute(
                f"INSERT INTO {table} (article_number, old_article_number, title, content, is_repealed) VALUES (%s, %s, %s, %s, %s)", 
                (chunk.article_number, chunk.old_article_number, chunk.title, chunk.content, chunk.is_repealed)
            )
    finally:
        cur.close()
        conn.close()