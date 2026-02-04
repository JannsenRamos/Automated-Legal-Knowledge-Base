import os
from dotenv import load_dotenv
from api.logic_helpers import extract_legal_text, push_to_baseline

load_dotenv()


LAW_FILES = [
    {"path": "C:\\Users\\Lenovo\\Documents\\GitHub\\Automated-Legal-Knowledge-Base\\Labor-Code-of-the-Philippines-DOLE.pdf", "jurisdiction": "PH"},
    {"path": "C:\\Users\\Lenovo\\Downloads\\Cap 57 Consolidated version for the Whole Chapter (24-08-2025) (English).pdf", "jurisdiction": "HK"}
]

def run_full_ingestion():
    db_url = os.getenv("SUPABASE_DB_URL")
    
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not found in .env")
        return

    for law in LAW_FILES:
        file_path = law["path"]
        print(f"Processing {law['jurisdiction']} Baseline: {file_path}...")

        if not os.path.exists(file_path):
            print(f" Skipping: {file_path} not found in root directory.")
            continue

        try:
            # 1. Read PDF as bytes
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            # 2. Extract and Categorize (Includes OCR Fallback & ToC-Shield)
            print(f"Extracting and Shielding {law['jurisdiction']} laws...")
            chunks = extract_legal_text(pdf_bytes, file_path)

            # 3. Push to Supabase
            print(f"Syncing {len(chunks)} sections to Supabase...")
            push_to_baseline(chunks, db_url)
            
            print(f"{law['jurisdiction']} Ingestion Complete.\n")

        except Exception as e:
            print(f"Failed to ingest {file_path}: {e}")

if __name__ == "__main__":
    run_full_ingestion()