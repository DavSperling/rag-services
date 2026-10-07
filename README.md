# RAG Services 🚀

Service complet de **RAG (Retrieval-Augmented Generation)** de bout en bout construit en Python. Ce projet implémente un pipeline complet : ingestion et prétraitement de documents PDF, découpage en fenêtres glissantes avec traçabilité page/source, embeddings vectoriels denses, stockage et indexation HNSW dans PostgreSQL via `pgvector`, recherche sémantique avec couche de **Reranking (Cross-Encoder)**, génération augmentée via l'API Claude (Anthropic), API REST FastAPI conteneurisée avec Docker Compose, et banc d'évaluation complet avec **LLM-as-a-judge**.

---

## 🛠️ Stack Technique

- **Langage** : Python 3.12
- **Backend API** : [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Base Vectorielle** : [PostgreSQL 16](https://www.postgresql.org/) avec extension [pgvector](https://github.com/pgvector/pgvector)
- **Pilote DB** : [psycopg 3](https://www.psycopg.org/psycopg3/) avec support `pgvector`
- **Extraction PDF** : [pypdf](https://pypdf.readthedocs.io/)
- **Embeddings** : [sentence-transformers](https://www.sbert.net/) (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **Reranker** : Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- **LLM Générateur** : Claude 3.7 Sonnet (`claude-sonnet-4-6`)
- **LLM Juge Évaluateur** : Claude 3.5 Haiku (`claude-haiku-4-5`)
- **Conteneurisation** : Docker & Docker Compose
- **Tests** : [pytest](https://docs.pytest.org/)

---

## 📂 Structure du Projet

```text
rag-services/
├── app/
│   └── main.py             # API FastAPI (routes: /health, /ingest, /query)
├── data/                   # Documents PDF bruts (ex: data/p538.pdf)
├── eval/
│   ├── questions.jsonl     # Dataset de 40 questions (direct, reformulation, multi, out_of_scope)
│   └── results/            # Rapports d'évaluation horodatés (.json)
├── scripts/
│   ├── check_db.py         # Test de connectivité PostgreSQL et pgvector
│   ├── check_evidence.py   # Normalisation de texte et validation des extraits de référence
│   ├── chunking.py         # Extraction PDF, nettoyage et découpage en fenêtres glissantes
│   ├── embed.py            # Génération d'embeddings denses BGE-small (384d normalisés)
│   ├── evaluate.py         # Benchmark automatique : Recall@5, LLM-as-a-judge & abstention
│   ├── generate.py         # Prompt engineering strict et génération de réponses avec Claude
│   ├── init_db.py          # Initialisation de la table chunks et de l'index HNSW
│   ├── ingest.py           # Ingestion complète : parsing -> chunking -> embed -> upsert SQL
│   ├── rerank.py           # Couche de Reranking Cross-Encoder (top 20 -> top 5)
│   ├── schema.sql          # Schéma SQL DDL et index vector_cosine_ops
│   └── search.py           # Recherche sémantique vectorielle pgvector
├── Dockerfile              # Image Docker du service FastAPI
├── docker-compose.yml      # Orchestration des services DB (pgvector) et API
├── requirements.txt        # Dépendances Python
└── README.md
```

---

## 🏗️ Architecture & Explication Détaillée des Fonctions

### 1. Prétraitement et Découpage (`scripts/chunking.py`)
- `clean_text(text)` : Nettoie les retours à la ligne parasites, espaces consécutifs et césures tout en préservant la ponctuation.
- `load_pdf(pdf_path)` : Extrait le texte page par page avec `pypdf`, associe le numéro de page source à chaque segment.
- `chunk_text(words, chunk_size=300, overlap=50)` : Applique une fenêtre glissante basée sur les mots pour éviter de couper des phrases au milieu et préserver le contexte sémantique entre chunks contigus.

### 2. Modèle d'Embedding (`scripts/embed.py`)
- `model = SentenceTransformer("BAAI/bge-small-en-v1.5")` : Modèle dense bi-encoder projetant le texte dans un espace de 384 dimensions.
- `embed_texts(texts, model)` : Encode une liste de textes en vecteurs avec normalisation L2 (`normalize_embeddings=True`). La normalisation permet de calculer la similarité cosinus par un simple produit scalaire (dot product).
- **Préfixe d'instruction pour les requêtes** : Pour BGE, les questions sont préfixées par `"Represent this sentence for searching relevant passages: "` afin d'aligner l'espace latent des requêtes avec celui des passages.

### 3. Schéma et Indexation (`scripts/schema.sql` & `scripts/init_db.py`)
- Table `chunks` avec colonne `embedding vector(384)`.
- Contrainte d'unicité `UNIQUE (source, chunk_index)` pour garantir l'idempotence des ingestions.
- Index approximatif **HNSW** (`USING hnsw (embedding vector_cosine_ops)`) pour des requêtes de similarité sous la milliseconde.

### 4. Ingestion Idempotente (`scripts/ingest.py`)
- Lit un PDF, génère les chunks et leurs embeddings, puis exécute un `INSERT INTO chunks ... ON CONFLICT (source, chunk_index) DO UPDATE` par lots.

### 5. Recherche Vectorielle (`scripts/search.py`)
- Encode la question utilisateur avec le préfixe BGE.
- Interroge PostgreSQL avec l'opérateur distance cosinus `<=>` :
  ```sql
  SELECT content, source, page, 1 - (embedding <=> %s) AS similarity
  FROM chunks ORDER BY embedding <=> %s LIMIT %s
  ```

### 6. Couche de Reranking (`scripts/rerank.py`)
- `rerank(question, candidates, top_k=5)` : Prend les 20 meilleurs candidats issus de la recherche vectorielle et les passe dans un **Cross-Encoder** (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- Contrairement au bi-encoder qui encode question et document séparément, le cross-encoder analyse les interactions mot à mot entre la question et chaque passage, réordonnant les candidats avec une précision chirurgicale.

### 7. Génération Augmentée (`scripts/generate.py`)
- `build_prompt(question, chunks)` : Assemble les chunks numérotés avec métadonnées (`[i] source, page`) et injecte une consigne stricte anti-hallucination.
- `generate(prompt)` : Envoie le contexte à Claude Sonnet avec instruction explicite d'abstention si l'information est absente.

### 8. Évaluation & LLM-as-a-Judge (`scripts/evaluate.py`)
- `is_hit(evidence, results)` : Vérifie en pur Python si les extraits de référence sont présents dans les chunks récupérés (calcul de **Recall@5**).
- `judge(question, reference, answer)` : Utilise `claude-haiku-4-5` comme arbitre impartial avec règles calibrées :
  - Verdicts : `correct`, `partial`, `incorrect`.
  - Règle spéciale `ABSTAIN` pour les questions hors-sujet.
  - Biais anti-verbosité : ne pénalise pas une réponse précise et exacte contenant des détails supplémentaires conformes.
  - Sortie JSON structurée.

---

## 📊 Résultats du Benchmark & Évolution des Métriques

L'évaluation porte sur un dataset de **40 questions** : 20 directes, 10 reformulations, 5 multi-passages, 5 hors-sujet (`out_of_scope`).

| Étape | Recall@5 | Réponses Correctes (hors OOS) | Réponses Partielles | Taux d'Abstention (OOS) | Croisement (Hit mais non-correct) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Baseline (Sans Rerank, Juge brut)** | 31/35 (88.6 %) | 31/35 (88.6 %) | 3/35 (`d05`, `d10`, `d11`) | 5/5 (100 %) | 3 questions |
| **2. Calibration du Juge** | 31/35 (88.6 %) | **34/35 (97.1 %)** | 0/35 | 5/5 (100 %) | 0 question |
| **3. Avec Reranking (Cross-Encoder)** | **32/35 (91.4 %)** | **34/35 (97.1 %)** | 0/35 | 5/5 (100 %) | 0 question |

### Analyse des Gains :
- **Recall@5** : Le Reranker fait passer le recall de **88.6 % à 91.4 %** en hissant avec succès le second passage de la question multi `m03` dans le top 5.
- **Fiabilité** : **100 % d'abstention** respectée sur les questions hors-sujet (`o01`-`o05`), 0 hallucination constatée.
- **Robustesse** : 0 question où le contexte était présent et la réponse incorrecte (`Croisement = []`).

---

## 🐳 Déploiement Docker & Docker Compose

L'ensemble de l'infrastructure est conteneurisée :

### 1. Lancement de la stack complète

```bash
docker compose up -d --build
```

Cette commande démarre :
- **`db`** : PostgreSQL 16 avec extension `pgvector` (port externe `5440`) avec healthcheck automatique.
- **`api`** : Service FastAPI conteneurisé (port externe `8000`), montant le dossier `data/` en volume.

### 2. Vérification des services

```bash
docker compose ps
curl http://localhost:8000/health
```

Réponse attendue :
```json
{"status": "ok", "db": "ok"}
```

---

## 🌐 Endpoints de l'API REST

- **`GET /health`** : Contrôle l'état de l'API et la liaison PostgreSQL.
- **`POST /ingest`** : Déclenche l'ingestion d'un PDF présent dans `data/`.
  ```bash
  curl -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d '{"path": "data/p538.pdf"}'
  ```
- **`POST /query`** : Interroge le RAG et retourne la réponse synthétisée avec sources et scores.
  ```bash
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"question": "What is a fiscal year?", "k": 5}'
  ```

---

## 🧪 Lancer les Évaluations

Pour exécuter le banc d'évaluation complet :

```bash
# Avec couche de Reranking (Cross-Encoder)
python -m scripts.evaluate

# Sans Reranking (baseline pure pgvector)
python -m scripts.evaluate --no-rerank
```
Les rapports d'évaluation sont automatiquement sauvegardés et horodatés dans `eval/results/`.
