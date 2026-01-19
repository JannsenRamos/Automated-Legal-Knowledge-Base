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
    """Uses GPT-OSS Free to identify document type: PHILIPPINES, HONG_KONG, or GENERIC."""
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
                        "Task: Determine the jurisdiction of this legal labor document. "
                        "Respond with ONLY ONE of these: 'PHILIPPINES', 'HONG_KONG', or 'GENERIC'. "
                        "Look for: Republic Act numbers (PH), Labor Code of the Philippines (PH), "
                        "Employment Ordinance (HK), Hong Kong legal references (HK). "
                        f"Text: {sample_text[:1000]}"
                    )
                }],
                "max_tokens": 50
            })
        )
        res_data = response.json()
        
        # Pull the content and clean it
        ai_reply = res_data['choices'][0]['message']['content'].strip().upper()
        print(f"DEBUG: AI identified jurisdiction as: '{ai_reply}'")
        
        # Check for jurisdiction keywords
        if "HONG_KONG" in ai_reply or "HK" in ai_reply:
            return "HONG_KONG"
        elif "PHILIPPINES" in ai_reply or "PHILIPPINE" in ai_reply:
            return "PHILIPPINES"
        elif "LABOR" in ai_reply:
            return "PHILIPPINES"  # Default to Philippines if labor content detected
            
        return "GENERIC"
    except Exception as e:
        print(f"Router Error (Passing through to Regex): {e}")
        return "PHILIPPINES"  # Default fallback
    
def parse_and_validate(pdf_bytes, api_key):
    # 1. Open and extract text
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join([page.get_text() for page in doc])
    
    # 2. Text Normalization: Remove non-breaking spaces (\xa0)
    full_text = full_text.replace('\xa0', ' ').replace('\t', ' ')
    
    # AI Gatekeeper - Identify jurisdiction
    jurisdiction = identify_document_pattern(full_text, api_key)
    if jurisdiction == "GENERIC":
        raise ValueError("AI rejected document as non-labor code.")
    
    print(f"DEBUG: Identified jurisdiction: {jurisdiction}")
    
    # 3. Route to appropriate parser
    if jurisdiction == "HONG_KONG":
        return parse_hong_kong_ordinance(full_text)
    else:  # PHILIPPINES
        return parse_philippine_code(full_text)

def parse_philippine_code(full_text):
    """Parse Philippine Labor Code with ART. pattern."""
    pattern = re.compile(r"(?i)ART\.?\s*(\d+)(?:\s*\[(\d+)\])?")
    jurisdiction = "PH"
    
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
    
    print(f"DEBUG: Extracted {len(chunks)} Philippine articles.")
    return chunks

def parse_hong_kong_ordinance(full_text):
    """Parse Hong Kong Employment Ordinance and related labor laws."""
    # HK pattern: Captures Section ID and the Title on the same line
    pattern = re.compile(r"(?m)^(\d+[A-Z]*)\.\s+(.*)")
    jurisdiction = "HK"
    
    parts = re.split(pattern, full_text)
    
    if len(parts) <= 1:
        print(f"DEBUG: HK parsing - No section matches. Text preview: {full_text[500:1000]}")
        return []

    chunks = []
    HK_ROUTING_RULES = {
        "wages": ["wage", "salary", "pay", "remuneration", "bonus", "commission", "overtime", "rest day"],
        "leave": ["leave", "annual leave", "sick leave", "maternity", "paternity", "holiday"],
        "contracts": ["contract", "employment", "termination", "dismissal", "resignation", "probation"],
        "safety": ["safety", "accident", "compensation", "injury", "health"],
    }

    # Re-looping with the 2-part split structure (section_id, content)
    for i in range(1, len(parts), 2):
        section_id = parts[i]
        content = parts[i+1].strip() if (i+1) < len(parts) else ""
        
        if not content or not section_id: 
            continue

        # Determine category based on keywords
        category = "general"
        for cat, keywords in HK_ROUTING_RULES.items():
            if any(k in content.lower() for k in keywords):
                category = cat
                break

        chunks.append(LaborArticleChunk(
            article_number=int(''.join(filter(str.isdigit, section_id))) if any(c.isdigit() for c in section_id) else 0,
            old_article_number=None,
            title=f"Section {section_id}"[:100],
            content=content,
            is_repealed="repealed" in content.lower() or "amended" in content.lower(),
            metadata=DocumentMetadata(
                source_file="upload.pdf", 
                file_type="ordinance", 
                page_number=0, 
                corpus_category=category
            )
        ))
    
    print(f"DEBUG: Extracted {len(chunks)} Hong Kong sections.")
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
            
            # 2. Check if article already exists
            cur.execute(
                f"SELECT id FROM {table} WHERE article_number = %s AND old_article_number IS NOT DISTINCT FROM %s",
                (chunk.article_number, chunk.old_article_number)
            )
            
            if cur.fetchone():
                # Update existing article
                cur.execute(
                    f"""UPDATE {table} 
                       SET title = %s, content = %s, is_repealed = %s, created_at = CURRENT_TIMESTAMP
                       WHERE article_number = %s AND old_article_number IS NOT DISTINCT FROM %s""",
                    (chunk.title, chunk.content, chunk.is_repealed, chunk.article_number, chunk.old_article_number)
                )
            else:
                # Insert new article
                cur.execute(
                    f"""INSERT INTO {table} (article_number, old_article_number, title, content, is_repealed) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (chunk.article_number, chunk.old_article_number, chunk.title, chunk.content, chunk.is_repealed)
                )
    finally:
        cur.close()
        conn.close()