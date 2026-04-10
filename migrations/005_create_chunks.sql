-- 005_create_chunks.sql
-- Chunks table: document chunks ready for embeddings and retrieval.

CREATE TABLE chunks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content_text        TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    source_type         VARCHAR(50) NOT NULL,
    authority_score     FLOAT NOT NULL DEFAULT 0.7,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_stale            BOOLEAN NOT NULL DEFAULT FALSE,
    embedding_id        TEXT,  -- reference to vector DB (Qdrant)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY chunks_org_isolation ON chunks
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX chunks_org_id_idx ON chunks(org_id);

-- Full-text search index
CREATE INDEX chunks_fts_idx ON chunks USING GIN(to_tsvector('english', content_text));
