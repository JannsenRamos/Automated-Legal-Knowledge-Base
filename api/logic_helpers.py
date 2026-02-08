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

class ContractClause(BaseModel):
    category: str      # wages, hours, benefits, etc.
    original_text: str # The raw text from the contract
    risk_score: str = "Pending"
    rationale: str = ""


def classify_clause(text: str):
    text_lower = text.lower()

    categories = {
        "wages": ["salary", "remuneration", "pay", "wage", "hkd", "php", "deduction", "allowance"],
        "leave": ["leave", "holiday", "sick", "vacation", "rest day", "absence", "off-duty"],
        "termination": ["notice", "terminate", "resign", "dismiss", "severance", "repatriation"],
        "benefits": ["insurance", "medical", "13th month", "bonus", "food", "accommodation", "housing"],
        "conditions": ["probation", "hours", "shift", "location", "job description", "duties"]
    }

    scores = {cat: 0 for cat in categories.keys()}

    for category, keywords in categories.items():
        for word in keywords:
            if word in text_lower:
                scores[category] += 1

    best_cat = max(scores, key=scores.get)
    
    return best_cat if scores[best_cat] > 0 else "general"

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
        rules = classify_clause(content)
        if rules != "general":
            category = rules

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

def segment_contract_clauses(contract_text, jurisdiction):
    segments = []
    # Splitting by double newline assumes standard contract formatting
    paragraphs = contract_text.split('\n\n') 
    
    for para in paragraphs:
        clean_para = para.strip()
        if len(clean_para) < 30: continue # Skip noise/headers
        
        # Use the new weighted classifier
        assigned_cat = classify_clause(clean_para)
        
        segments.append(ContractClause(
            category=assigned_cat,
            original_text=clean_para
        ))
    
    return segments

def audit_contract(contract_clauses, db_url):
    """
    benchmarks contract clauses against the statutory baseline.
    uses the db_url passed from the caller (e.g., test_audit.py).
    """
    if not db_url:
        raise ValueError("The database URL provided to the audit function is empty.")
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    audited_results = []

    for clause in contract_clauses:
        # 1. Fetch the legal baseline for this category
        cur.execute(
            "SELECT content, section_id FROM labor_ordinances WHERE category = %s AND jurisdiction = %s",
            (clause.category, "HK") # Assuming HK for this example
        )
        laws = cur.fetchall()

        # 2. Basic Deviation Logic (e.g., Statutory Minimums)
        # If the category is 'wages', we check for common red flags
        if clause.category == "wages":
            # Heuristic: Check for 'deductions' which are highly regulated
            if "deduct" in clause.original_text.lower():
                clause.risk_score = "MEDIUM"
                clause.rationale = "Contract permits wage deductions. Cross-check with HK Cap 57 Sec. 32 for compliance."
        
        # 3. Handle Ambiguity (The 'General' Bucket)
        if clause.category == "general" and len(clause.original_text) > 200:
            clause.risk_score = "HIGH"
            clause.rationale = "Uncategorized long-form text detected. High potential for hidden compliance risks."

        audited_results.append(clause)

    cur.close()
    conn.close()
    return audited_results

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

def push_to_baseline(chunks: List[LegalOrdinanceChunk], db_url: str):
    """
    Persists extracted laws to the Supabase baseline table.
    Ensures the 'Source of Truth' is populated for future contract audits.
    """
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # SQL with Upsert logic: if jurisdiction + section_id already exists, update the content.
        query = """
            INSERT INTO labor_ordinances (
                jurisdiction, section_id, title, content, category, is_repealed, source_file
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (jurisdiction, section_id) 
            DO UPDATE SET 
                content = EXCLUDED.content,
                category = EXCLUDED.category,
                title = EXCLUDED.title;
        """
        
        for chunk in chunks:
            cur.execute(query, (
                chunk.jurisdiction,
                chunk.section_id,
                chunk.title,
                chunk.content,
                chunk.metadata.corpus_category,
                chunk.is_repealed,
                chunk.metadata.source_file
            ))
            
        print(f"Baseline Sync Complete: {len(chunks)} laws pushed to Supabase.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database Sync Failed: {e}")