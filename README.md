# LICE — Legal Intelligence & Compliance Engine

> An AI-powered contract auditing system for Overseas Filipino Worker (OFW) employment contracts, built to detect statutory violations against Philippine Labor Code and Hong Kong Employment Ordinance Cap. 57.

---

## Overview

Most legal document tools fail with OFW contracts because they treat them as generic text. LICE uses a **Hybrid Risk Model** that combines deterministic forbidden-term detection with ML-based semantic similarity scoring against jurisdiction-specific statutory baselines — delivering structured, auditable risk reports.

Built for: **DOLE / POEA compliance workflows**, legal aid orgs, and OFW advocacy groups.

---

## How It Works

```
Upload Contract (PDF or TXT)
        ↓
Automatic Jurisdiction Detection (PH 🇵🇭 or HK 🇭🇰)
        ↓
Text Segmentation & Clause Classification
        ↓
Hybrid Risk Scoring:
  → Pass 1: Forbidden Term Detection (hard rules)
  → Pass 2: Semantic Similarity vs. Statutory Baseline (SentenceTransformer)
        ↓
Pydantic-Validated Structured Report
        ↓
Streamlit Dashboard + Downloadable PDF Audit
```

---

## Features

| Feature | Description |
|---|---|
| **Automatic Jurisdiction Detection** | Heuristic keyword scoring identifies PH vs. HK contracts without user input |
| **Semantic Risk Scoring** | `all-MiniLM-L6-v2` compares contract clauses against statutory baselines via cosine similarity |
| **Forbidden Term Detection** | Catches illegal clauses (e.g., "placement fee", "exit bond", "employer owns passport") instantly |
| **Selective Indexing** | Domain-aware filter excludes repealed provisions from the legal knowledge base |
| **PDF Audit Report** | Generates a formal FPDF report with per-clause risk scores and statutory citations |
| **Pydantic Validation** | All data is schema-validated, ensuring structured and production-ready JSON outputs |
| **OCR Fallback** | Tesseract fallback for scanned/image-based PDF pages |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| UI | Streamlit + Plotly |
| API | FastAPI |
| ML Model | `sentence-transformers/all-MiniLM-L6-v2` |
| PDF Extraction | PyMuPDF (`fitz`) |
| OCR | Tesseract via `pytesseract` + `pdf2image` |
| Data Validation | Pydantic v2 |
| Report Generation | FPDF2 |
| Database | SQLite (local) / Supabase-ready (PostgreSQL) |
| Legal Corpus | PH Labor Code (DOLE 2022 Edition), HK Employment Ordinance Cap. 57 |

---

## Statutory Coverage

### 🇵🇭 Philippines
- Labor Code Art. 83, 85 — Working Hours & Meal Breaks  
- Labor Code Art. 87 — Overtime Pay  
- Labor Code Art. 91 — Rest Days  
- Labor Code Art. 94 — Holiday Pay  
- Labor Code Art. 95 — Service Incentive Leave  
- Labor Code Art. 102–103 — Wage Payment Rules  
- Labor Code Art. 279, 283 — Termination & Due Process  
- Presidential Decree No. 851 — 13th Month Pay  
- RA 10022 (Migrant Workers Act) — Zero Placement Fee Rule  
- RA 11210 — Expanded Maternity Leave  

### 🇭🇰 Hong Kong
- Cap. 57 s.6, s.9 — Termination & Notice  
- Cap. 57 s.14–15 — Maternity Leave (14 weeks)  
- Cap. 57 s.17 — Rest Days  
- Cap. 57 s.23–32 — Wage Payment & Deductions  
- Cap. 57 s.31G — Severance Payment  
- Cap. 57 s.33 — Sickness Allowance  
- Cap. 57 s.39–40 — Statutory Holidays  
- Cap. 608 (Minimum Wage Ordinance) — HKD 40/hr floor  
- Cap. 57A — Employment Agency Fee Caps  

---

## Running the App

### Prerequisites
```bash
pip install -r requirements.txt
```

> For OCR support, install [Tesseract](https://github.com/tesseract-ocr/tesseract) and ensure it is in your PATH.

### Start the Streamlit UI
```bash
streamlit run app.py
```

### Start the FastAPI Backend (optional)
```bash
uvicorn api.index:app --reload
```
API docs available at: `http://localhost:8000/docs`

---

## Environment Variables

Copy `api/api_keys.env.example` to `.env` and fill in:

```env
SUPABASE_DB_URL=your_supabase_connection_string
```

---

## Risk Score Legend

| Score | Label | Meaning |
|---|---|---|
| 0–2 | ✅ Low / Compliant | Standard, legally sound phrasing |
| 2–5 | 🟡 Medium | Non-standard wording, warrants review |
| 5–8 | 🟠 High | Likely statutory violation |
| 8–10 | 🔴 Critical | Illegal or prohibited clause |

> Score = `(1 − Cosine Similarity) × Severity Weight`

---

## Disclaimer

This tool is for **informational and research purposes only** and does not constitute formal legal advice. For binding assessments, consult the POEA, DMW, or a licensed attorney.
