import psycopg2
from .schemas import LegalOrdinanceChunk
from typing import List

def save_to_supabase(chunks, db_url):
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        query = """
            INSERT INTO labor_ordinances (
                jurisdiction, section_id, title, content, is_repealed, source_file, category
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        for chunk in chunks:
            cur.execute(query, (
                chunk.jurisdiction,
                chunk.section_id,
                chunk.title,
                chunk.content,
                chunk.is_repealed,
                chunk.metadata.source_file,
                chunk.metadata.corpus_category
            ))
    finally:
        cur.close()
        conn.close()

def push_to_baseline(chunks: List[LegalOrdinanceChunk], db_url: str):
    """
    Persists extracted laws to the Supabase baseline table.
    Ensures the 'Source of Truth' is populated for future contract audits.
    """
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # SQL with Upsert logic: if jurisdiction + section_id already exists, update the content.
        query = """
            INSERT INTO labor_ordinances (
                jurisdiction, section_id, title, content, category, is_repealed, source_file
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (jurisdiction, section_id) 
            DO UPDATE SET 
                content = EXCLUDED.content,
                category = EXCLUDED.category,
                title = EXCLUDED.title;
        """
        
        for chunk in chunks:
            cur.execute(query, (
                chunk.jurisdiction,
                chunk.section_id,
                chunk.title,
                chunk.content,
                chunk.metadata.corpus_category,
                chunk.is_repealed,
                chunk.metadata.source_file
            ))
            
        print(f"Baseline Sync Complete: {len(chunks)} laws pushed to Supabase.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database Sync Failed: {e}")