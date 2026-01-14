import os, re, sqlite3, fitz
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 1. SETUP & SECURITY
env_path = os.path.join(os.path.dirname(__file__), 'api_keys.env')
load_dotenv(env_path)
DB_PATH = "labor_law_knowledge_base.db"

# 2. DATA MODELS (Restored from your notebook)
class DocumentMetadata(BaseModel):
    source_file: str
    file_type: str
    page_number: int
    corpus_category: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class LaborArticleChunk(BaseModel):
    node_type: Literal["labor_article"] = "labor_article"
    article_number: int
    old_article_number: Optional[int] = None
    title: str
    content: str
    is_repealed: bool = False
    metadata: DocumentMetadata

# 3. SELECTIVE INDEXING RULES (Restored from your notebook)
ROUTING_RULES = {
    "wages": ["wage", "salary", "pay", "overtime", "payroll", "deduction", "night shift"],
    "contracts": ["contract", "dismissal", "tenure", "termination", "probationary", "resignation"],
}

# 4. DATABASE INITIALIZATION: Separate Tables for Categories
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table_name in ["wages", "contracts", "general"]:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_number INTEGER,
                old_article_number INTEGER,
                title TEXT,
                content TEXT,
                is_repealed BOOLEAN,
                full_json TEXT,
                timestamp DATETIME
            )
        ''')
    conn.commit()
    conn.close()

# 5. INTEGRATED PARSING & AI ROUTING
def run_full_pipeline(uploaded_file, api_key):
    init_db()
    llm = ChatOpenAI(
        model="openai/gpt-oss-120b:free", 
        api_key=api_key, 
        base_url="https://openrouter.ai/api/v1", 
        temperature=0
    )
    
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    sample_text = doc[0].get_text()[:500]
    
    # AI Identification Step
    try:
        response = llm.invoke(f"Identify legal text type. Return 'LABOR_CODE' or 'GENERIC': {sample_text}")
        doc_type = response.content.strip()
    except:
        doc_type = "LABOR_CODE"

    pattern = r"ART\.\s+(\d+)(?:\s+\[(\d+)\])?"
    full_text = "".join([page.get_text() for page in doc])
    parts = re.split(pattern, full_text)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    processed_count = 0

    for i in range(1, len(parts), 3):
        art_num, old_num, content = parts[i], parts[i+1], parts[i+2].strip()

        # SELECTIVE INDEXING
        category = "general"
        for cat, keywords in ROUTING_RULES.items():
            if any(k in content.lower() for k in keywords):
                category = cat; break

        chunk = LaborArticleChunk(
            article_number=int(art_num),
            old_article_number=int(old_num) if old_num else None,
            title=content.split('\n')[0][:100],
            content=content,
            is_repealed="repealed" in content.lower() or "ra 10151" in content.lower(),
            metadata=DocumentMetadata(source_file=uploaded_file.name, file_type=doc_type, page_number=0, corpus_category=category)
        )

        cursor.execute(f'''
            INSERT INTO {category} (article_number, old_article_number, title, content, is_repealed, full_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (chunk.article_number, chunk.old_article_number, chunk.title, chunk.content, 
              chunk.is_repealed, chunk.model_dump_json(), datetime.now().isoformat()))
        processed_count += 1
    
    conn.commit()
    conn.close()
    return processed_count, doc_type