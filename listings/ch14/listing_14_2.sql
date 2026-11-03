-- Listing 14.2. pgvector schema and permission-filtered
-- nearest-neighbor query.
--
-- Chapter 14, Embeddings and Vector Search. Reviewed for correctness
-- against pgvector documentation (September 2026); requires a
-- PostgreSQL server with the vector extension to run.
--
-- Apply with:  psql "$DATABASE_URL" -f listings/ch14/listing_14_2.sql
-- The Compose file of Listing 44.1 starts a suitable database.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id            BIGSERIAL PRIMARY KEY,
    document_id   TEXT NOT NULL,
    chunk_index   INT  NOT NULL,
    heading_path  TEXT,
    content       TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    -- dimension of the chosen model
    embedding     vector(1024) NOT NULL,
    -- e.g. 'vendor/model-name@2026-03'
    embed_model   TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, chunk_index)
);

-- Access control lives on the document, not the chunk.
CREATE TABLE document_acl (
    document_id TEXT NOT NULL,
    group_id    TEXT NOT NULL,
    PRIMARY KEY (document_id, group_id)
);

-- HNSW index using cosine distance; parameters are tuned by
-- measurement.
CREATE INDEX chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- Search-time settings (pgvector 0.8.0 or later). The default
-- hnsw.ef_search is 40, which is too small for a LIMIT of 40 with a
-- filter; iterative scans keep walking the index until enough rows
-- pass the WHERE clause.
SET hnsw.ef_search = 100;
SET hnsw.iterative_scan = relaxed_order;   -- or strict_order
SET hnsw.max_scan_tuples = 20000;          -- safety bound on the walk

-- Query: nearest chunks the caller's groups may read. $1 = query
-- vector, $2 = array of the caller's group ids. <=> is cosine
-- distance.
SELECT c.id, c.document_id, c.heading_path, c.content,
       1 - (c.embedding <=> $1) AS similarity
FROM   chunks c
WHERE  EXISTS (SELECT 1 FROM document_acl a
               WHERE a.document_id = c.document_id
                 AND a.group_id = ANY($2))
ORDER  BY c.embedding <=> $1
LIMIT  40;
