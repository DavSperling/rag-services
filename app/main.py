from fastapi import FastAPI
import os 
from pathlib import Path
from dotenv import load_dotenv
import psycopg
from pydantic import BaseModel
from scripts.ingest import ingest
from fastapi import FastAPI, HTTPException
from scripts.search import search 
from scripts.generate import build_prompt, generate

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

app = FastAPI()

class IngestRequest(BaseModel):
    path: str

class QueryRequest(BaseModel):
    question: str
    k: int = 5

@app.get("/health")
def health():
    try :
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""SELECT 1""")
        return {"status": "ok", "db": "ok"}
    except psycopg.OperationalError:
        return {"status": "degraded", "db": "down"}


@app.post("/ingest")
def ingest_route(req: IngestRequest):
    pdf_path = Path(req.path).resolve()
    data_dir = Path("data").resolve()
    if not pdf_path.is_relative_to(data_dir):
        raise HTTPException(status_code=403, detail="FORBIDEN")
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="N'existe pas ")
    reponse = ingest(req.path)
    return {"chunks": reponse}


@app.post("/query")
def query_route(req: QueryRequest):
    chunks = search(req.question, k=req.k)
    if not chunks:
        return {"there is no chunks ":"" }
    prompt = build_prompt(req.question, chunks)
    answer = generate(prompt)
    sources = [
    {"source": c[1], "page": c[2], "similarity": round(float(c[3]), 4)}
    for c in chunks
    ]
    return {"answer": answer, "sources": sources}