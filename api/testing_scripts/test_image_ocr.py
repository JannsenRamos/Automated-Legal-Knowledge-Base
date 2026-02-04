# Create a new standalone test: test_image_ocr.py
import pytesseract
from PIL import Image

# Ensure this matches your local installation
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_raw_image(image_path):
    print(f"Testing OCR on: {image_path}")
    img = Image.open(image_path)
    
    # Extracting text directly to see 'Raw Output'
    raw_text = pytesseract.image_to_string(img)
    
    print("--- RAW OCR OUTPUT START ---")
    print(raw_text[:500]) # Print first 500 chars
    print("--- RAW OCR OUTPUT END ---")
    
    # Verification: Does it contain legal anchors?
    if "Section" in raw_text or "Art" in raw_text:
        print("SUCCESS: Tesseract identified legal anchors in the image.")
    else:
        print("WARNING: OCR failed to find section headers. Check image DPI.")

if __name__ == "__main__":
    test_raw_image(r"C:\Users\Lenovo\Documents\GitHub\Automated-Legal-Knowledge-Base\CAP 57 HK Labor Ordinance.png")