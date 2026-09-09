# RAG Services 🚀

End-to-end **RAG (Retrieval-Augmented Generation)** service built with Python. This project provides a full pipeline: PDF ingestion and preprocessing, sliding-window chunking with accurate source page tracking, vector indexing in PostgreSQL using `pgvector`, semantic search with sentence embeddings, and augmented answer generation via the Anthropic Claude API, served through FastAPI.

---

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **API Backend**: [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Vector Database**: [PostgreSQL 16](https://www.postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector) extension via Docker
- **DB Driver**: [psycopg 3](https://www.psycopg.org/psycopg3/)
- **PDF Extraction & Parsing**: [pypdf](https://pypdf.readthedocs.io/)
- **Embeddings**: [sentence-transformers](https://www.sbert.net/)
- **LLM & Generation**: [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- **Testing**: [pytest](https://docs.pytest.org/)

---

## 📂 Project Structure

```text
rag-services/
├── app/                  # FastAPI application and RAG core logic
├── data/                 # Raw documents to ingest (e.g. p538.pdf)
├── scripts/              # Utility and ingestion scripts
│   ├── check_db.py       # Check database connectivity and pgvector extension
│   ├── chunk.py          # PDF cleaning, chunking, and source page tracking
│   └── peek.py           # Quick inspection of PDF documents
├── tests/                # Unit and integration tests
├── docker-compose.yml    # PostgreSQL + pgvector service definition
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # Project documentation
```

---

## ⚙️ Prerequisites

- **Python** 3.10+
- **Docker** and **Docker Compose**
- An [Anthropic API key](https://console.anthropic.com/) (for LLM answer generation)

---

## 🚀 Installation & Setup

### 1. Navigate to the project directory

```bash
cd rag-services
```

### 2. Set up the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# or .venv\Scripts\activate on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`:

```env
DATABASE_URL=postgresql://rag:rag@localhost:5440/rag
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 5. Start the vector database (pgvector)

Spin up the PostgreSQL container with the pgvector extension enabled:

```bash
docker compose up -d
```

> **Note**: The database is exposed on host port `5440` (`localhost:5440`).

Verify database connectivity and check if the `vector` extension is installed:

```bash
python scripts/check_db.py
```

---

## 🔍 Ingestion & Data Pipeline

The `scripts/chunk.py` script handles preprocessing and text segmentation:

1. **Extraction and Cleaning (`clean_text`)**:
   - Removes hyphenated line breaks (`-\n`).
   - Strips noisy printing artifacts, boilerplate headers, and tech identifiers.
   - Normalizes whitespace.

2. **Sliding-Window Chunking (`chunk_text`)**:
   - Word-level chunking (`chunk_size=300`, `overlap=50`).
   - Overlap preserves semantic continuity between adjacent segments.

3. **Page Tracking & Metadata (`find_page`)**:
   - Maps each chunk to its exact original page number, source document filename, and chunk index for citation accuracy.

Run the chunking script:

```bash
python scripts/chunk.py
```

---

## 📡 Running the API (FastAPI)

Once endpoints are implemented under `app/`:

```bash
uvicorn app.main:app --reload --port 8000
```

- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Alternative**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Tests

Run the test suite using `pytest`:

```bash
pytest
```

---

## 🗺️ Roadmap & Next Steps

- [x] Dockerized PostgreSQL with `pgvector` extension
- [x] PDF text extraction, cleaning, and chunking with page tracking
- [ ] Embedding generation using Sentence Transformers
- [ ] Vector storage and index creation (HNSW / IVFFlat) in `pgvector`
- [ ] Hybrid / semantic search retrieval pipeline (cosine similarity)
- [ ] Augmented context synthesis with Claude (Anthropic SDK)
- [ ] FastAPI REST endpoints (`/ingest`, `/query`)
