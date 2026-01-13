# Automated-Legal-Knowledge-Base
This project automates the structuring of the 2022 DOLE Edition of the Philippine Labor Code. Most RAG systems fail with legal text because they don't account for renumbered articles or repealed provisions. This system uses a Hybrid-AI Router to achieve high-precision extraction with zero API costs.

- Hybrid-AI Router: Utilizes gpt-oss-120b for high-level pattern recognition to route documents to specific parsing logic, minimizing API costs.
- Deterministic Extraction: A local Python-based engine ensures 100% accuracy in capturing legal citations and article numbers.
- Pydantic Validation: All data is strictly validated against a schema to ensure production-ready JSON outputs.
- Selective Indexing: A domain-aware filter that identifies and excludes repealed provisions from the final search index.

# Tech Stack
- Language: Python
- Models: gpt-oss-120b:free (OpenRouter)
- Libraries: LangChain, Pydantic, PyMuPDF (fitz)
- Database Readiness: Structured for FAISS / LSH Vector Stores
