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
    
def parse_sensitive_legal_text(pdf_bytes, filename):
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
    """
    Saves unified legal chunks to the 'labor_ordinances' table.
    Ensures that data for both PH and HK jurisdictions are stored correctly.
    """
    if not chunks:
        print("DEBUG: No chunks to save.")
        return

    # Connection setup using the Transaction Pooler URL (Port 6543)
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # 1. OPTIONAL: Clear the database for a fresh upload
        # Only use this if you want to replace all data every time you upload
        # cur.execute("TRUNCATE TABLE labor_ordinances RESTART IDENTITY;")

        # 2. Prepared Statement for efficiency and security
        query = """
            INSERT INTO labor_ordinances (
                jurisdiction, 
                section_id, 
                title, 
                content, 
                is_repealed, 
                source_file
            ) VALUES (%s, %s, %s, %s, %s, %s);
        """

        for chunk in chunks:
            # Map the Pydantic model fields to database columns
            cur.execute(query, (
                chunk.metadata.jurisdiction,
                chunk.section_id,
                chunk.title,
                chunk.content,
                chunk.is_repealed,
                chunk.metadata.source_file
            ))
            
        print(f"SUCCESS: Successfully saved {len(chunks)} items to the unified table.")

    except Exception as e:
        print(f"DATABASE ERROR: {str(e)}")
        raise e
    finally:
        cur.close()
        conn.close()