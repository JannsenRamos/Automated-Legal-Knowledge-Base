import os
import re
import fitz  # PyMuPDF
import psycopg2
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes


class LegalMetadata(BaseModel):
    source_file: str
    jurisdiction: str    # "PH" or "HK"
    corpus_category: str # "wages", "contracts", etc.
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class LegalOrdinanceChunk(BaseModel):
    jurisdiction: str
    section_id: str      
    title: str
    content: str
    is_repealed: bool = False
    metadata: LegalMetadata


ROUTING_RULES = {
    "PH": {
        "wages": ["wage", "salary", "13th month", "overtime", "payroll", "deduction"],
        "contracts": ["dismissal", "termination", "probationary", "resignation", "tenure"],
        "benefits": ["maternity", "paternity", "retirement", "holiday", "sss", "pag-ibig"],
    },
    "HK": {
        "wages": ["wage", "payment", "deduction", "overtime", "end of year payment"],
        "contracts": ["notice", "termination", "probation", "summary dismissal", "damages"],
        "benefits": ["maternity", "paternity", "leave", "medical certificate", "rest day"],
    }
}

def extract_legal_text(pdf_bytes, filename):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()
        
        if len(text) < 100: 
            images = convert_from_bytes(pdf_bytes, first_page=page_num+1, last_page=page_num+1)
            if images:
                text = pytesseract.image_to_string(images[0])
        
        page_texts.append(text)

    full_text = "\n".join(page_texts).replace('\xa0', ' ')

    jurisdiction = "HK" if "Cap. 57" in full_text[:3000] else "PH"
    pattern = re.compile(r"(?m)^(\d+[A-Z]*)\.\s+(.*)") if jurisdiction == "HK" else re.compile(r"(?i)ART\.?\s*(\d+)")
    
    matches = list(pattern.finditer(full_text))
    chunks = []

    for i in range(len(matches)):
        start_idx = matches[i].end()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        content = full_text[start_idx:end_idx].strip()
  
        if len(content) < 60 or "........" in content or re.search(r"^\d+-\d+$", content):
            continue

        category = "general"
        rules = ROUTING_RULES.get(jurisdiction, {})
        for cat, keywords in rules.items():
            if any(k in content.lower() for k in keywords):
                category = cat; break

        # D. Structural Mapping
        sec_id = matches[i].group(1)
        # HK title comes from regex; PH title uses the first line of captured content[cite: 1, 2].
        title = matches[i].group(2).strip() if jurisdiction == "HK" else content.split('\n')[0][:100]

        chunks.append(LegalOrdinanceChunk(
            jurisdiction=jurisdiction,
            section_id=sec_id,
            title=title,
            content=content,
            is_repealed="(Repealed)" in title or "repealed" in content.lower(),
            metadata=LegalMetadata(
                source_file=filename, 
                jurisdiction=jurisdiction, 
                corpus_category=category
            )
        ))

    return chunks

# --- STEP 4: PRODUCTION DATABASE SYNC ---
def save_to_supabase(chunks, db_url):
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        query = """
            INSERT INTO labor_ordinances (
                jurisdiction, section_id, title, content, is_repealed, source_file, category
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        for chunk in chunks:
            cur.execute(query, (
                chunk.jurisdiction,
                chunk.section_id,
                chunk.title,
                chunk.content,
                chunk.is_repealed,
                chunk.metadata.source_file,
                chunk.metadata.corpus_category
            ))
    finally:
        cur.close()
        conn.close()