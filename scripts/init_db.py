from pathlib import Path
import os 
from dotenv import load_dotenv
import psycopg


load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

schema_sql = Path("scripts/schema.sql").read_text()

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(schema_sql)
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'chunks'
            ORDER BY ordinal_position;
            """)
        print(cur.fetchall())   