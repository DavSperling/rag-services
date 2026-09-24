from chunk import load_pdf
from embed import embed_texts, model
import psycopg
import os 
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
docs = load_pdf("data/p538.pdf")
texts = [d["content"] for d in docs]
vecs = embed_texts(texts, model)

params = [(d["content"], d["source"], d["page"],d["chunk_index"], vec) for d, vec in zip(docs, vecs)]

with psycopg.connect(DB_URL) as conn:
    register_vector(conn)
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO chunks (content, source, page, chunk_index, embedding)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (source, chunk_index) DO UPDATE SET
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        page = EXCLUDED.page
         """, params)
        cur.execute("SELECT COUNT(*) FROM chunks")
        print(cur.fetchone()[0])   


