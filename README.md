# RAG Services 🚀

End-to-end **RAG (Retrieval-Augmented Generation)** service built with Python. This project provides a full end-to-end pipeline: PDF ingestion and preprocessing, sliding-window chunking with precise source-page tracking, dense vector embeddings with Sentence Transformers, vector storage and HNSW indexing in PostgreSQL using `pgvector`, low-latency semantic search, and augmented answer generation via the Anthropic Claude API, served through FastAPI.

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **API Backend**: [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Vector Database**: [PostgreSQL 16](https://www.postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector) extension via Docker
- **Database Driver**: [psycopg 3](https://www.psycopg.org/psycopg3/) with `pgvector-python` support
- **PDF Extraction & Parsing**: [pypdf](https://pypdf.readthedocs.io/)
- **Embeddings**: [sentence-transformers](https://www.sbert.net/) (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **LLM & Generation**: [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (Claude)
- **Testing**: [pytest](https://docs.pytest.org/)

---

## 📂 Project Structure

```text
rag-services/
├── app/                  # FastAPI application and RAG core logic
├── data/                 # Raw source documents (e.g., p538.pdf)
├── scripts/              # Data pipeline and utility scripts
│   ├── check_db.py       # Validates DB connection and pgvector extension
│   ├── chunk.py          # PDF text extraction, cleaning, and sliding-window chunking
│   ├── embed.py          # Dense vector embedding generation using BGE-small
│   ├── init_db.py        # Applies schema.sql to initialize tables and HNSW index
│   ├── ingest.py         # Full ingestion pipeline: chunks, embeds, and upserts into pgvector
│   ├── peek.py           # Quick document inspection utility
│   ├── schema.sql        # PostgreSQL DDL schema with HNSW index definition
│   └── search.py         # Semantic similarity search with latency benchmarking
├── tests/                # Unit and integration test suites
├── docker-compose.yml    # PostgreSQL 16 + pgvector container definition
├── requirements.txt      # Project Python dependencies
├── .env.example          # Environment variables template
└── README.md             # Project documentation
```

---

## ⚙️ Prerequisites

- **Python** 3.10+
- **Docker** & **Docker Compose** (Docker Desktop must be running)
- An [Anthropic API Key](https://console.anthropic.com/) (for LLM answer generation)

---

## 🚀 Installation & Quick Start

### 1. Clone & navigate to the repository

```bash
cd rag-services
```

### 2. Set up the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS / Linux
# or .venv\Scripts\activate on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql://rag:rag@localhost:5440/rag
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 5. Start the Vector Database (Docker)

Start the PostgreSQL container with `pgvector` enabled:

```bash
docker compose up -d
```

> **Note**: PostgreSQL is mapped to host port **`5440`** (`localhost:5440`).

Verify that the database is accessible and `pgvector` is loaded:

```bash
python scripts/check_db.py
```

---

## 🔄 RAG Pipeline Walkthrough

### Step 1: Initialize Database Schema & Index

Creates the `chunks` table and builds an approximate nearest neighbor **HNSW** vector index (`vector_cosine_ops`):

```bash
python scripts/init_db.py
```

**Schema features (`scripts/schema.sql`):**
- Vector column: `embedding vector(384)` matching BGE embeddings.
- Metadata: `content`, `source`, `page`, `chunk_index`, `date_creation`.
- Idempotent upsert constraint: `UNIQUE (source, chunk_index)`.
- Index: Fast cosine similarity search via `USING hnsw (embedding vector_cosine_ops)`.

### Step 2: Ingest and Vectorize Documents

Extracts, cleans, chunks, embeds, and stores document segments in PostgreSQL with conflict resolution:

```bash
python scripts/ingest.py
```

- **Preprocessing & Chunking (`scripts/chunk.py`)**: Word-level sliding window (`chunk_size=300`, `overlap=50`) preserving sentence flow and mapping chunks back to original page numbers.
- **Embedding Generation (`scripts/embed.py`)**: Computes normalized dense vectors using `BAAI/bge-small-en-v1.5`.
- **Bulk Upsert (`scripts/ingest.py`)**: Batched insert using `ON CONFLICT (source, chunk_index) DO UPDATE` to ensure idempotency.

### Step 3: Run Semantic Search

Test vector similarity search directly from the CLI:

```bash
python scripts/search.py
```

**Example output:**
```text
🔍 Résultats pour : "What is a fiscal year?"
⏱️  Temps de requête : 1.40 ms (5 résultats trouvés)
──────────────────────────────────────────────────────────────────────
#1 │ Score: 85.3% (0.8529) │ Page 3 │ Source: data/p538.pdf
   └─ "A fiscal year is 12 consecutive months ending on the last day of any month other than December..."

#2 │ Score: 78.1% (0.7812) │ Page 4 │ Source: data/p538.pdf
   └─ "Accounting Periods and Methods - Choosing a Tax Year..."
```

---

## 📡 Running the API (FastAPI)

Launch the RAG service backend with Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Alternative**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing

Run automated tests using `pytest`:

```bash
pytest
```

---

## 🗺️ Roadmap

- [x] Dockerized PostgreSQL 16 with `pgvector` extension
- [x] PDF text extraction, cleaning, and sliding-window chunking with page tracking
- [x] Dense vector embedding generation (`BAAI/bge-small-en-v1.5`)
- [x] Vector storage and HNSW cosine index (`pgvector`)
- [x] Idempotent bulk upsert pipeline
- [x] Semantic vector similarity search with latency benchmarking
- [ ] Contextual answer generation with Claude (Anthropic SDK)
- [ ] FastAPI REST endpoints (`/ingest`, `/query`, `/health`)
- [ ] Reranking layer (Cross-Encoder / Cohere Rerank)
