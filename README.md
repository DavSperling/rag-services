# RAG Services 🚀

An end-to-end, production-grade **Retrieval-Augmented Generation (RAG)** system built with Python. This project implements a complete pipeline: PDF document parsing and preprocessing, sliding-window chunking with source/page traceability, dense vector embeddings, vector storage and HNSW indexing in PostgreSQL via `pgvector`, semantic search powered by a **Cross-Encoder Reranking layer**, grounded answer synthesis with Anthropic Claude, containerized FastAPI REST services via Docker Compose, and a rigorous automated evaluation harness featuring a calibrated **LLM-as-a-judge**.

---

## 🛠️ Tech Stack

- **Language**: Python 3.12
- **REST Backend**: [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Vector Database**: [PostgreSQL 16](https://www.postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector) extension
- **Database Driver**: [psycopg 3](https://www.psycopg.org/psycopg3/) with native `pgvector` support
- **PDF Extraction**: [pypdf](https://pypdf.readthedocs.io/)
- **Dense Embeddings**: [sentence-transformers](https://www.sbert.net/) (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **Reranker**: Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- **Generation LLM**: Claude 3.7 Sonnet (`claude-sonnet-4-6`)
- **Evaluation Judge**: Claude 3.5 Haiku (`claude-haiku-4-5`)
- **Containerization**: Docker & Docker Compose
- **Testing**: [pytest](https://docs.pytest.org/)

---

## 📂 Project Directory Structure

```text
rag-services/
├── app/
│   └── main.py             # FastAPI REST application (routes: /health, /ingest, /query)
├── data/                   # Source documents (e.g., IRS Publication 538 p538.pdf)
├── eval/
│   ├── questions.jsonl     # Benchmark dataset of 40 annotated questions
│   └── results/            # Timestamped evaluation reports (.json)
├── scripts/
│   ├── check_db.py         # PostgreSQL connectivity and pgvector validation script
│   ├── check_evidence.py   # Text normalization and ground-truth evidence verification
│   ├── chunking.py         # PDF text extraction, cleaning, and sliding-window chunking
│   ├── embed.py            # BGE-small dense embedding generation (L2-normalized 384d)
│   ├── evaluate.py         # Automated evaluation: Recall@5, LLM-as-a-judge, and abstention
│   ├── generate.py         # Strict prompt engineering and Claude synthesis pipeline
│   ├── init_db.py          # Table creation and HNSW index initialization
│   ├── ingest.py           # End-to-end ingestion: parse -> chunk -> embed -> upsert
│   ├── rerank.py           # Cross-Encoder Reranking layer (top 20 -> top 5)
│   ├── schema.sql          # PostgreSQL DDL schema with HNSW cosine index
│   └── search.py           # Semantic similarity search using pgvector
├── Dockerfile              # Docker container configuration for FastAPI service
├── docker-compose.yml      # Multi-service orchestration (Postgres/pgvector + API)
├── requirements.txt        # Python dependency manifest
└── README.md
```

---

## 🏗️ Architecture & Detailed Function Walkthrough

### 1. Document Extraction & Sliding-Window Chunking (`scripts/chunking.py`)
- `clean_text(text)`: Strips hyphenation artifacts, irregular line breaks, and excessive whitespace while preserving semantic punctuation.
- `load_pdf(pdf_path)`: Iterates through PDF pages using `pypdf`, associating each extracted text segment with its original page number for citations.
- `chunk_text(words, chunk_size=300, overlap=50)`: Splits document word streams into fixed-size windows (`chunk_size=300`) with a 50-word sliding overlap, preventing boundary clipping of key concepts.

### 2. Dense Vector Embeddings (`scripts/embed.py`)
- `model = SentenceTransformer("BAAI/bge-small-en-v1.5")`: High-performance dense bi-encoder generating 384-dimensional vectors.
- `embed_texts(texts, model)`: Generates L2-normalized vectors (`normalize_embeddings=True`). Because vectors have unit norm, cosine similarity simplifies directly to an inner dot product ($\mathbf{u} \cdot \mathbf{v}$).
- **Instruction Prefix for Asymmetric Search**: To align query and passage representations in vector space, questions are prepended with:
  `"Represent this sentence for searching relevant passages: "`.

### 3. Database Schema & Vector Indexing (`scripts/schema.sql` & `scripts/init_db.py`)
- `chunks` table stores text content, source metadata, page numbers, chunk indices, and a `vector(384)` column.
- Idempotent upsert constraint: `UNIQUE (source, chunk_index)`.
- **HNSW Index**: Built using `vector_cosine_ops` (`USING hnsw (embedding vector_cosine_ops)`) enabling sub-millisecond approximate nearest neighbor (ANN) retrieval.

### 4. Idempotent Ingestion Pipeline (`scripts/ingest.py`)
- Extracts PDF text, chunks content, computes dense embeddings, and performs batched SQL upserts:
  `INSERT INTO chunks ... ON CONFLICT (source, chunk_index) DO UPDATE`.

### 5. Semantic Vector Search (`scripts/search.py`)
- Encodes incoming user questions with the BGE retrieval prefix.
- Queries PostgreSQL using the pgvector cosine distance operator `<=>`:
  ```sql
  SELECT content, source, page, 1 - (embedding <=> %s) AS similarity
  FROM chunks ORDER BY embedding <=> %s LIMIT %s
  ```

### 6. Cross-Encoder Reranking Layer (`scripts/rerank.py`)
- `rerank(question, candidates, top_k=5)`: Receives the top-20 candidate passages from initial vector search and scores each `(query, passage)` pair simultaneously using a dedicated Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- Unlike bi-encoders that process queries and documents independently, the Cross-Encoder leverages cross-attention across tokens, identifying nuanced semantic matches and promoting relevant evidence into the top 5.

### 7. Grounded Answer Synthesis (`scripts/generate.py`)
- `build_prompt(question, chunks)`: Formats retrieved chunks with bracketed identifiers `[i] source, page` alongside strict anti-hallucination instructions.
- `generate(prompt)`: Calls `claude-sonnet-4-6` with instructions to abstain from answering if the provided context lacks the necessary facts.

### 8. Evaluation Harness & LLM-as-a-Judge (`scripts/evaluate.py`)
- `is_hit(evidence, results)`: Deterministic, non-LLM check measuring **Recall@5** by verifying whether ground-truth answer snippets (`evidence`) are present in retrieved chunks.
- `judge(question, reference, answer)`: Uses `claude-haiku-4-5` with temperature 0 as an impartial evaluator:
  - Three verdicts: `correct`, `partial`, `incorrect`.
  - Special `ABSTAIN` rule for off-topic questions.
  - Length bias mitigation: ensures additional accurate context beyond the reference answer is never penalized.
  - Structured JSON output with one-sentence justification.

---

## 📊 Benchmark Results & Empirical Improvements

Evaluated against a curated dataset of **40 questions**: 20 direct questions, 10 reformulated questions, 5 multi-passage questions, and 5 out-of-scope questions (`out_of_scope`).

| Stage | Recall@5 | Correct Answers (excl. OOS) | Partial Answers | Abstention Rate (OOS) | Discrepancies (Hit=True, Non-correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Baseline (No Rerank, Raw Judge)** | 31/35 (88.6 %) | 31/35 (88.6 %) | 3/35 (`d05`, `d10`, `d11`) | 5/5 (100 %) | 3 questions |
| **2. Calibrated Judge** | 31/35 (88.6 %) | **34/35 (97.1 %)** | 0/35 | 5/5 (100 %) | 0 questions |
| **3. With Cross-Encoder Reranking** | **32/35 (91.4 %)** | **34/35 (97.1 %)** | 0/35 | 5/5 (100 %) | 0 questions |

### Key Takeaways:
- **Recall@5 Gain**: The Cross-Encoder lifted Recall@5 from **88.6% to 91.4%**, successfully elevating the second required chunk for multi-passage question `m03` from rank 12 into the top 5.
- **Precision**: **100% abstention rate** on out-of-scope questions (`o01`–`o05`), with zero hallucinated answers.
- **Alignment**: **0 discrepancies** between retrieval success and answer correctness.

---

## 🐳 Docker & Docker Compose Deployment

The entire system is containerized for seamless reproducibility.

### 1. Launch the Stack

```bash
docker compose up -d --build
```

This starts:
- **`db`**: PostgreSQL 16 with `pgvector` on host port **`5440`** with integrated health checks (`pg_isready`).
- **`api`**: Containerized FastAPI service on host port **`8000`** with mounted `/app/data` volume.

### 2. Verify Service Health

```bash
docker compose ps
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "db": "ok"}
```

---

## 🌐 REST API Endpoints

- **`GET /health`**: Health check reporting database and API availability.
- **`POST /ingest`**: Ingests, chunks, embeds, and stores a document from `data/`.
  ```bash
  curl -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d '{"path": "data/p538.pdf"}'
  ```
  *Response*: `{"chunks": 70}`

- **`POST /query`**: Performs semantic search, synthesizes a grounded response, and returns cited sources with similarity scores.
  ```bash
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"question": "What is a fiscal year?", "k": 5}'
  ```

---

## 🧪 Running the Evaluation Suite

To run the automated benchmark locally:

```bash
# With Cross-Encoder Reranking enabled (default)
python -m scripts.evaluate

# Without Reranking (pure pgvector baseline)
python -m scripts.evaluate --no-rerank
```

Evaluation outputs and judge reasoning are automatically written to timestamped files under `eval/results/`.
