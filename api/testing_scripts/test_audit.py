import os
from dotenv import load_dotenv
from api.logic_helpers import segment_contract_clauses, audit_contract

load_dotenv()

# 1. Simulating a raw contract upload
MOCK_CONTRACT = """
Standard Employment Contract for Filipino Workers in Hong Kong
...
Section 5: Wages
The monthly salary shall be $4,500. The employer may deduct costs for broken equipment.
...
"""

def run_audit_test():
    db_url = os.getenv("SUPABASE_DB_URL")
    
    # Step A: Segment the contract
    print("Segmenting contract...")
    clauses = segment_contract_clauses(MOCK_CONTRACT, "HK")
    
    # Step B: Audit against Supabase baseline
    print("Auditing against legal baseline...")
    results = audit_contract(clauses, db_url)
    
    for res in results:
        print(f"\nCategory: {res.category}")
        print(f"Risk: {res.risk_score}")
        print(f"Rationale: {res.rationale}")

if __name__ == "__main__":
    run_audit_test()