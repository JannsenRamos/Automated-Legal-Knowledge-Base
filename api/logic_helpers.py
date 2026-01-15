import os, re, psycopg2, fitz
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI

# 1. DATA MODELS
class LaborArticleChunk(BaseModel):
    article_number: int
    title: str
    content: str
    is_repealed: bool = False

# 2. SELECTIVE INDEXING RULES
ROUTING_RULES = {
    "wages": ["wage", "salary", "pay", "overtime", "payroll"],
    "contracts": ["contract", "dismissal", "termination", "probationary"],
}

# 3. THE PARSER
def parse_and_validate(file_stream, api_key):
    llm = ChatOpenAI(model="openai/gpt-oss-120b:free", api_key=api_key, base_url="https://openrouter.ai/api/v1")
    file_stream.seek(0) 
    
    # 2. Now perform the read
    doc = fitz.open(stream=file_stream.read(), filetype="pdf")
    
    # AI Router
    sample = doc[0].get_text()[:800]
    prompt = f"Is this a Legal Labor Code? Reply 'VALID' or 'INVALID'. Sample: {sample}"
    if "INVALID" in llm.invoke(prompt).content.upper():
        raise ValueError("AI rejected content: This is not a legal document.")

    # Regex Splitting
    pattern = r"ART\.\s+(\d+)"
    full_text = "".join([p.get_text() for p in doc])
    parts = re.split(pattern, full_text)
    
    validated_chunks = []
    for i in range(1, len(parts), 2):
        try:
            art_num, content = parts[i], parts[i+1].strip()
            category = "general"
            for cat, kw in ROUTING_RULES.items():
                if any(k in content.lower() for k in kw): category = cat; break

            chunk = LaborArticleChunk(
                article_number=int(art_num),
                title=content.split('\n')[0][:100],
                content=content,
                is_repealed="repealed" in content.lower()
            )
            validated_chunks.append((category, chunk))
        except: continue
    return validated_chunks

def save_to_supabase(data_list, db_url):
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    for category, chunk in data_list:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {category} (id SERIAL PRIMARY KEY, art_num INT, title TEXT, full_json JSONB)")
        cursor.execute(f"INSERT INTO {category} (art_num, title, full_json) VALUES (%s, %s, %s)",
                       (chunk.article_number, chunk.title, chunk.model_dump_json()))
    conn.commit()
    cursor.close(); conn.close()