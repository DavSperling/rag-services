from pypdf import PdfReader
import re
import logging
from pathlib import Path
logging.getLogger("pypdf").setLevel(logging.ERROR)


def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    result = []
    for i in range(0, len(words), (chunk_size - overlap)):
        words_chunked = words[i:i+chunk_size]
        words_chunked = ' '.join(words_chunked)
        result.append(words_chunked)
    return result 

NOISE = ["Fileid:", "MUST be removed before printing", "The type and rule above prints"]

def clean_text(raw):
    text = re.sub(r"-\n", "", raw)
    lines = text.split("\n")
    kept = [ i for i in lines if not any(n in i for n in NOISE)  ]                 
    text = " ".join(kept)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def load_pdf(path, chunk_size=300, overlap=50):
    """Retourne une liste de dicts {content, source, page, chunk_index}."""
    pages_text = []
    page_starts = [] 
    word_count = 0
    reader = PdfReader(path)
    for num, i in enumerate(reader.pages, start=1):
        page = clean_text(i.extract_text())
        pages_text.append(page)
        page_starts.append((num, word_count))
        word_count += len(page.split())
    full_text = " ".join(pages_text)
    chunks = chunk_text(full_text, chunk_size, overlap)
    
    result =[]

    for name, i in enumerate(chunks, start=1):
        result.append({
                "content": name,
                "source":path,
                "page": None,          # on le remplira à l'étape G
                "chunk_index": i,
            })
import collections
from pypdf import PdfReader
import re
import logging
from pathlib import Path
logging.getLogger("pypdf").setLevel(logging.ERROR)


def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    result = []
    for i in range(0, len(words), (chunk_size - overlap)):
        words_chunked = words[i:i+chunk_size]
        words_chunked = ' '.join(words_chunked)
        result.append(words_chunked)
    return result 

NOISE = ["Fileid:", "MUST be removed before printing", "The type and rule above prints", "Userid"]

def clean_text(raw):
    text = re.sub(r"-\n", "", raw)
    lines = text.split("\n")
    kept = [ i for i in lines if not any(n in i for n in NOISE)  ]                 
    text = " ".join(kept)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
    
def find_page(word_pos, page_starts):
    """Retourne le numéro de la page contenant le mot à la position word_pos."""
    best = 1
    for num, start in page_starts:
        if word_pos >= start :
            best = num
    return best 

def load_pdf(path, chunk_size=300, overlap=50):
    """Retourne une liste de dicts {content, source, page, chunk_index}."""
    pages_text = []
    page_starts = [] 
    word_count = 0
    reader = PdfReader(path)
    for num, i in enumerate(reader.pages, start=1):
        page = clean_text(i.extract_text())
        pages_text.append(page)
        page_starts.append((num, word_count))
        word_count += len(page.split())
    full_text = " ".join(pages_text)
    chunks = chunk_text(full_text, chunk_size, overlap)
    
    result =[]

    for idx, text in enumerate(chunks):
        result.append({
                "content": text,
                "source":Path(path).name,
                "page": find_page(idx * (chunk_size - overlap),page_starts),          # on le remplira à l'étape G
                "chunk_index": idx,
            })
    return result

if __name__ == "__main__":
    docs = load_pdf("data/p538.pdf")
    print(docs[0]["page"], docs[35]["page"], docs[-1]["page"])