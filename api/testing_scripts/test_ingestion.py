import os
import json
from api.logic_helpers import extract_legal_text

# --- CONFIGURATION ---
LOCAL_PDF_PATH = r"C:\Users\Lenovo\Documents\GitHub\Automated-Legal-Knowledge-Base\Labor-Code-of-the-Philippines-DOLE.pdf"
OUTPUT_FOLDER = "./test_results"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def run_local_test():
    print(f"Starting Local Ingestion Test for: {LOCAL_PDF_PATH}")
    
    if not os.path.exists(LOCAL_PDF_PATH):
        print(f"Error: File not found at {LOCAL_PDF_PATH}")
        return

    # Read the file as bytes (simulating an upload)
    with open(LOCAL_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    # Trigger the LICE Unified Extractor
    # Note: Ensure your logic_helpers.py has the TESSERACT_CMD set correctly!
    try:
        chunks = extract_legal_text(pdf_bytes, LOCAL_PDF_PATH)
        
        print(f"Success! Extracted {len(chunks)} valid sections.")
        print(f"ToC-Shield filtered out {len(chunks)} possible noise entries.")

        # Save the first 3 chunks to JSON for manual review
        for i, chunk in enumerate(chunks[:3]):
            output_file = os.path.join(OUTPUT_FOLDER, f"sample_section_{chunk.section_id}.json")
            with open(output_file, "w") as jf:
                jf.write(chunk.model_dump_json(indent=2))
            print(f"Saved sample to: {output_file}")

    except Exception as e:
        print(f"Ingestion failed: {e}")

if __name__ == "__main__":
    run_local_test()