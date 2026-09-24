import psycopg
import os 
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("SELECT 1;")
        print(cur.fetchone())
        cur.execute("SELECT extname FROM pg_extension;")
        print(cur.fetchall())
