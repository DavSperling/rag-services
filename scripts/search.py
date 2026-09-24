from embed import model
import psycopg
import time
import os 
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")


PREFIX = "Represent this sentence for searching relevant passages: "
question = "What is a fiscal year?"
qvec = model.encode([PREFIX + question], normalize_embeddings=True)[0]

with psycopg.connect(DB_URL) as conn:
    register_vector(conn)
    with conn.cursor() as cur:
        query_start= time.perf_counter()
        cur.execute("""SELECT content,source,page,1 - (embedding <=> %s) AS similarity 
        FROM chunks 
        ORDER BY embedding <=> %s LIMIT 5 
         """,(qvec,qvec))
        rows = cur.fetchall()
        query_end= time.perf_counter()
    
latency_ms = (query_end - query_start) * 1000
print(f"\n🔍 Résultats pour : \"{question}\"")
print(f"⏱️  Temps de requête : {latency_ms:.2f} ms ({len(rows)} résultats trouvés)\n" + "─" * 70)

for i, (content, source, page, sim) in enumerate(rows, start=1):
    preview = content.strip().replace("\n", " ")
    if len(preview) > 160:
        preview = preview[:157] + "..."

    print(f"#{i} │ Score: {sim * 100:.1f}% ({sim:.4f}) │ Page {page} │ Source: {source}")
    print(f"   └─ \"{preview}\"\n")