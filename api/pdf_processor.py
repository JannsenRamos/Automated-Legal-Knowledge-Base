from .schemas import ContractClause, LegalMetadata, LegalOrdinanceChunk
from .logic_helpers import classify_clause
import re
import pytesseract
import fitz  # PyMuPDF
from pdf2image import convert_from_bytes
from PIL import Image

import re
import fitz  # PyMuPDF

def get_text_and_jurisdiction(uploaded_file_bytes, filename):
    """
    Advanced Extractor: 
    1. Normalizes PDF line breaks into full sentences.
    2. Segments text into logical legal paragraphs (Chunks).
    3. Heuristically detects Jurisdiction (PH vs HK).
    """
    ext = filename.split('.')[-1].lower()
    full_text = ""
    
    # --- STEP 1: RAW EXTRACTION ---
    if ext == 'txt':
        full_text = uploaded_file_bytes.decode('utf-8', errors='ignore')
    
    elif ext == 'pdf':
        doc = fitz.open(stream=uploaded_file_bytes, filetype="pdf")
        page_texts = []
        for page in doc:
            page_texts.append(page.get_text())
        full_text = "\n".join(page_texts)
        doc.close()

    if not full_text.strip():
        return [], "UNKNOWN"

    # --- STEP 2: CONTEXTUAL NORMALIZATION ---
    # PDFs often insert newlines mid-sentence. 
    # This regex joins lines that don't end in a period or double-newline.
    # It turns: "The employee\n shall receive" -> "The employee shall receive"
    normalized_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', full_text)

    # --- STEP 3: SEMANTIC CHUNKING ---
    # Split by double newlines or common legal numbering (e.g., "1. ", "Section 2")
    # This ensures each item in the list is a complete 'Legal Clause'
    raw_chunks = re.split(r'\n\n|(?=\d+\.\s)|(?=\bSECTION\b)', normalized_text)
    
    # Filter out empty chunks and tiny fragments (noise)
    # 40 characters is roughly the minimum for a meaningful legal statement
    final_chunks = [c.strip() for c in raw_chunks if len(c.strip()) > 40]

    # --- STEP 4: JURISDICTION DETECTION ---
    # We analyze the first 3 chunks (usually contains the header/title)
    detection_window = " ".join(final_chunks[:3]).lower()
    
    ph_anchors = ["poea", "republic act", "dole", "philippines", "art.", "pna", "owwa"]
    hk_anchors = ["cap. 57", "hong kong", "employment ordinance", "hksar", "hkd", "domestic helper"]
    
    ph_score = sum(1 for a in ph_anchors if a in detection_window)
    hk_score = sum(1 for a in hk_anchors if a in detection_window)
    
    # Logic: If tied, look for currency clues
    if ph_score == hk_score:
        if "php" in normalized_text.lower(): ph_score += 1
        if "hkd" in normalized_text.lower(): hk_score += 1
    
    jurisdiction = "PH" if ph_score >= hk_score else "HK"
    
    # Return the LIST of chunks and the detected string
    return final_chunks, jurisdiction
   

def extract_legal_text(pdf_bytes, filename):

    ext = filename.split('.')[-1].lower()
    full_text = ""

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


    jurisdiction = "HK" if "Cap. 57" in full_text[:3000] or "Hong Kong" in full_text[:500] else "PH"
    
    pattern = re.compile(r"(?m)^(\d+[A-Z]*)\.\s+(.*)") if jurisdiction == "HK" else re.compile(r"(?i)ART\.?\s*(\d+)")
    
    matches = list(pattern.finditer(full_text))
    chunks = []

    for i in range(len(matches)):
        start_idx = matches[i].end()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        content = full_text[start_idx:end_idx].strip()
  
        # Noise Filter (ToC-Shield)
        if len(content) < 60 or "........" in content or re.search(r"^\d+-\d+$", content):
            continue

        category = classify_clause(content)

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