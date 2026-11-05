-- 001: Atlas reference schema.
-- Documents and their ACLs are copies from the systems of record; chunks
-- and vectors are derived and rebuildable (Chapter 18). The embedding
-- dimension (256) matches the default HashingEmbedder; a different
-- embedding model needs a new migration and a full re-embed.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    doc_id            text PRIMARY KEY,
    title             text NOT NULL,
    status            text NOT NULL CHECK (status IN ('current','superseded','draft')),
    source            text NOT NULL,
    version           text NOT NULL,
    updated           text NOT NULL DEFAULT '',
    owner             text NOT NULL DEFAULT '',
    classification    text NOT NULL DEFAULT 'internal'
                      CHECK (classification IN ('internal','restricted')),
    content_hash      text NOT NULL,
    embed_model       text NOT NULL,
    quarantined       boolean NOT NULL DEFAULT false,
    quarantine_reason text,
    ingested_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE document_acl (
    doc_id   text NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    group_id text NOT NULL,
    PRIMARY KEY (doc_id, group_id)
);
CREATE INDEX document_acl_group ON document_acl (group_id);

CREATE TABLE chunks (
    chunk_id     text PRIMARY KEY,
    doc_id       text NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    ordinal      integer NOT NULL,
    heading_path text NOT NULL,
    content      text NOT NULL,
    embedding    vector(256) NOT NULL,
    tsv          tsvector GENERATED ALWAYS AS
                 (to_tsvector('english', heading_path || ' ' || content)) STORED
);
CREATE INDEX chunks_doc ON chunks (doc_id);
CREATE INDEX chunks_tsv ON chunks USING gin (tsv);
CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);

-- Tickets, drafts, and approvals (Chapters 19, 24, 29), stored as typed
-- JSON per kind. The idempotency key is unique per kind.
CREATE TABLE records (
    kind       text NOT NULL,
    id         text NOT NULL,
    owner      text NOT NULL,
    idem_key   text,
    data       jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, id)
);
CREATE UNIQUE INDEX records_idem ON records (kind, idem_key) WHERE idem_key IS NOT NULL;

-- Append-only, hash-chained action audit (Chapter 43). The application
-- role should be granted INSERT and SELECT only.
CREATE TABLE audit_log (
    seq       bigserial PRIMARY KEY,
    at        timestamptz NOT NULL DEFAULT now(),
    actor     text NOT NULL,
    action    text NOT NULL,
    detail    jsonb NOT NULL,
    prev_hash text NOT NULL,
    hash      text NOT NULL
);
