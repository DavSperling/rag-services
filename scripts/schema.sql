CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    content TEXT NOT NULL,
    source TEXT  NOT NULL,
    page INTEGER  NOT NULL,
    chunk_index INTEGER  NOT NULL,
    embedding vector(384), 
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);