import json
import psycopg
import os 
from dotenv import load_dotenv
import re

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")


def load_questions(file_path):
    questions = []
    with open(file_path, 'r', encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line :
                questions.append(json.loads(line))
        return questions 

def load_chunks():
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT chunk_index,content
            FROM chunks 
            ORDER BY chunk_index
            """)
            rows = cur.fetchall()
    return rows

def normalize(text):
    text = text.lower()
    text = text.replace("’","'")
    text = re.sub(r"\s+", " ", text)
    clean = text.strip()

    return clean

def find_chunks(extrait, chunks_normalises):
    extrait_norm = normalize(extrait)
    resultats = []
    for chunk_index, content in chunks_normalises:
        if extrait_norm in content:
            resultats.append(chunk_index)
    return resultats


if __name__ == "__main__":
    questions = load_questions("eval/questions.jsonl")
    rows = load_chunks()

    chunks_normalises = [(chunk_index, normalize(content)) for chunk_index, content in rows]

    total = 0
    trouves = 0
    introuvables = []

    for q in questions:
        for extrait in q["evidence"]:
            total += 1
            chunks_trouves = find_chunks(extrait, chunks_normalises)
            if chunks_trouves:
                trouves += 1
            else:
                introuvables.append((q["id"], extrait))

    for q_id, extrait in introuvables:
        print(f"{q_id}: {extrait}")

    print(f"Extraits trouvés : {trouves}/{total}")