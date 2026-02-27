import re
import json
import psycopg2
from torch import chunk
from .schemas import ClauseAnalysis, FullContractReport 
from sentence_transformers import SentenceTransformer, util

from .schemas import (
    ClauseAnalysis, 
    FullContractReport, 
)

model = SentenceTransformer('all-MiniLM-L6-v2')

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

def load_legal_rules(path="legal_rules.json"):
   
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rules from {path}: {e}")
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

        #1. GLOBAL SAFETY NET
        for term in forbidden_list:
            if term in text_lower:
                risk_level = "CRITICAL"
                rationale = f"Forbidden term detected: '{term}'. This may indicate illegal practices."
                break

        #2. STATUTORY CITATION
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
        
        clause.rationale = f"{rationale} | Source: {citation}"
        audited_results.append(clause)

    cur.close()
    conn.close()
    return audited_results

def analyze_contract_risk(chunks: list, detected_jurisdiction: str, rules_path: str) -> FullContractReport:
    """
    The Brain: Processes each chunk independently and aggregates risk.
    """
    rules_data = load_legal_rules(rules_path)
    all_benchmarks = rules_data.get('benchmarks', [])
    
    # Filter benchmarks to match jurisdiction
    active_benchmarks = [b for b in all_benchmarks if b.get('jurisdiction') == detected_jurisdiction]
    forbidden_terms = rules_data.get('global_config', {}).get('forbidden_terms', [])

    analysis_results = []
    total_risk_accumulation = 0.0

    for chunk in chunks:

        if isinstance(chunk, (bytes, bytearray)):
            chunk = chunk.decode('utf-8', errors='ignore')
    
        emb_user = model.encode(chunk, convert_to_tensor=True)
        
        found_forbidden = [term for term in forbidden_terms if term.lower() in chunk.lower()]
        
        # Pass 2: Semantic Analysis (ML Logic)
        category = classify_clause(chunk)
        
        # Find the specific benchmark for this category
        match = next((b for b in active_benchmarks if b['category'] == category), None)
        
        risk_score = 0.0
        confidence = 0.0
        rationale = "No significant deviation detected."
        violation_type = "Standard Clause"

        if found_forbidden:
            risk_score = 10.0 # Maximum risk for forbidden terms
            confidence = 1.0
            violation_type = "PROHIBITED TERM DETECTED"
            rationale = f"Clause contains forbidden language: {', '.join(found_forbidden)}"
        
        elif match:
            # Vector Similarity Math
            emb_user = model.encode(chunk, convert_to_tensor=True)
            emb_base = model.encode(match['baseline'], convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(emb_user, emb_base).item()
            
            # Risk = (1 - Similarity) * Weight
            deviation = 1 - similarity
            risk_score = round(deviation * match['weight'], 2)
            confidence = round(similarity, 2)
            violation_type = match['law_reference']
            
            if risk_score > 3.0:
                rationale = f"Significant deviation from {detected_jurisdiction} statutory baseline."

        # Only add to report if there is a category or a risk
        analysis_results.append(ClauseAnalysis(
            category=category,
            risk_score=risk_score,
            confidence=confidence,
            violation_type=violation_type,
            extracted_text=chunk,
            rationale=rationale
        ))
        total_risk_accumulation += risk_score

    return FullContractReport(
        total_risk=round(total_risk_accumulation, 2),
        analysis=analysis_results
    )

 