import os
import re
import requests
import json
import fitz
import psycopg2
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LegalMetadata(BaseModel):
    source_file: str
    jurisdiction: str    # "PH" or "HK"
    corpus_category: str # "wages", "contracts", etc.

class LegalOrdinanceChunk(BaseModel):
    section_id: str      # "Art. 1" or HK Section "10A"
    title: str
    content: str
    is_repealed: bool
    metadata: LegalMetadata

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
    
def parse_sensitive_legal_text(pdf_bytes, filename):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join([page.get_text() for page in doc])
    full_text = full_text.replace('\xa0', ' ')

    # 1. Detection
    is_hk = "Hong Kong" in full_text[:1000] or "Cap. 57" in full_text[:1000]
    pattern = re.compile(r"(?m)^(\d+[A-Z]*)\.\s+(.*)") if is_hk else re.compile(r"(?i)ART\.?\s*(\d+)")
    jurisdiction = "HK" if is_hk else "PH"

    chunks = []
    matches = list(pattern.finditer(full_text))

    # 2. Capture Preamble (Text before the first match)
    if matches and matches[0].start() > 0:
        preamble = full_text[:matches[0].start()].strip()
        if len(preamble) > 5:
            chunks.append(LegalOrdinanceChunk(
                section_id="PREAMBLE",
                title="Introductory Provisions",
                content=preamble,
                is_repealed=False,
                metadata=LegalMetadata(source_file=filename, jurisdiction=jurisdiction, corpus_category="meta")
            ))

    # 3. Capture all sections without gaps
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        content = full_text[start:end].strip()
        
        # Identification based on jurisdiction
        sec_id = match.group(1)
        title = match.group(2) if is_hk else content.split('\n')[0][:100]

        chunks.append(LegalOrdinanceChunk(
            section_id=sec_id,
            title=title,
            content=content,
            is_repealed="repealed" in content.lower(),
            metadata=LegalMetadata(source_file=filename, jurisdiction=jurisdiction, corpus_category="general")
        ))

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