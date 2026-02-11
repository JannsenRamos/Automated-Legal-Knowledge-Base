import os
import re
import json
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
        "conditions": ["probation", "hours", "shift", "location", "job description", "duties"],
        "fees": ["fee", "charge", "payment", "deployment", "exit fee", "processing", "bond", "placement"]
    }

    scores = {cat: 0 for cat in categories.keys()}

    for category, keywords in categories.items():
        for word in keywords:
            if word in text_lower:
                scores[category] += 1

    best_cat = max(scores, key=scores.get)
    
    return best_cat if scores[best_cat] > 0 else "general"

def extract_legal_text(pdf_bytes, filename):
    """
    Full Integrated Extractor:
    Handles .txt and .pdf, uses OCR fallback, and applies Regex Sectioning.
    """
    ext = filename.split('.')[-1].lower()
    full_text = ""

    # --- 1. EXTRACTION LAYER ---
    if ext == 'txt':
        full_text = pdf_bytes.decode('utf-8', errors='ignore')
    elif ext == 'pdf':
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_texts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            # OCR Fallback if text is sparse (scanned page)
            if len(text) < 100: 
                images = convert_from_bytes(pdf_bytes, first_page=page_num+1, last_page=page_num+1)
                if images:
                    text = pytesseract.image_to_string(images[0])
            page_texts.append(text)
        full_text = "\n".join(page_texts).replace('\xa0', ' ')
        doc.close()

    # --- 2. JURISDICTION & PATTERN DETECTION ---
    # We use a 3000-character window to identify the Law type
    jurisdiction = "HK" if "Cap. 57" in full_text[:3000] or "Hong Kong" in full_text[:500] else "PH"
    
    # Regex for HK (Section numbers) or PH (Art. numbers)
    pattern = re.compile(r"(?m)^(\d+[A-Z]*)\.\s+(.*)") if jurisdiction == "HK" else re.compile(r"(?i)ART\.?\s*(\d+)")
    
    matches = list(pattern.finditer(full_text))
    chunks = []

    # --- 3. SECTION CHUNKING & CLASSIFICATION ---
    for i in range(len(matches)):
        start_idx = matches[i].end()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        content = full_text[start_idx:end_idx].strip()
  
        # Noise Filter (ToC-Shield)
        if len(content) < 60 or "........" in content or re.search(r"^\d+-\d+$", content):
            continue

        # Week 2 Weighted Classifier
        category = classify_clause(content)

        # Structural Mapping
        sec_id = matches[i].group(1)
        # HK titles come from regex group 2; PH titles use the first line of text
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
    
    # This splits the text *at* the number without deleting the number itself.
    pattern = r'\n(?=\d+\.\d+|\bSECTION\b)'
    
    # Split the contract into logical blocks
    raw_blocks = re.split(pattern, contract_text)
    
    for block in raw_blocks:
        clean_block = block.strip()
        
        # Filter out tiny noise, but keep anything that looks like a legal statement
        if len(clean_block) < 30: 
            continue 
            
        # The Classifier now has the full context (e.g., "1.1 The salary is...")
        assigned_cat = classify_clause(clean_block)
        
        segments.append(ContractClause(
            category=assigned_cat,
            original_text=clean_block
        ))
    
    print(f"LICE grouped the contract into {len(segments)} contextual blocks.")
    return segments

def load_legal_rules():
    """Loads the statutory floors from the root directory."""
    try:
        # Assumes legal_rules.json is in your project root
        with open("legal_rules.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Warning: Could not load legal_rules.json: {e}")
        return {}

def audit_contract(contract_clauses, db_url):
    rules = load_legal_rules()
    audited_results = []
    forbidden_list = rules.get("global_config", {}).get("forbidden_terms", [])

    # Establish DB connection for citations
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for clause in contract_clauses:
        jurisdiction = "HK" # Dynamically set this in Week 4
        text_lower = clause.original_text.lower()
        risk_level = "LOW"
        rationale = "No obvious statutory deviations detected."
        citation = "General Labor Principles"

        #1. GLOBAL SAFETY NET (Forbidden Terms) 
        for term in forbidden_list:
            if term in text_lower:
                risk_level = "CRITICAL"
                rationale = f"Forbidden term detected: '{term}'. This may indicate illegal practices."
                break

        #2. STATUTORY CITATION (Basic Example)
        cur.execute(
            "SELECT section_id, title FROM labor_ordinances WHERE category = %s AND jurisdiction = %s LIMIT 1",
            (clause.category, jurisdiction)
        )
        law_match = cur.fetchone()
        if law_match:
            citation = f"{jurisdiction} Law: {law_match[1]} ({law_match[0]})"

        #3. CATEGORY SPECIFIC MATH (Wages Example)
        if risk_level != "CRITICAL" and clause.category == "wages":
            min_wage = rules.get(jurisdiction, {}).get("wages", {}).get("min_allowable_wage")
            amount_match = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b", clause.original_text)
            found_amount = float(amount_match.group(1).replace(',', '')) if amount_match else None

            if found_amount and min_wage and found_amount < min_wage:
                risk_level = "CRITICAL"
                rationale = f"Salary {found_amount} is below the statutory minimum of {min_wage}."

        # Update the Pydantic model
        clause.risk_score = risk_level
        # We append the citation to the rationale for a complete legal answer
        clause.rationale = f"{rationale} | Source: {citation}"
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