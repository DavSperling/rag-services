from fastapi import FastAPI
import os 
from pathlib import Path
from dotenv import load_dotenv
import psycopg
from pydantic import BaseModel
from scripts.ingest import ingest
from fastapi import FastAPI, HTTPException

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

app = FastAPI()

class IngestRequest(BaseModel):
    path: str

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