-- 006_create_queries.sql
-- Queries table: user queries and responses for analytics and debugging.

CREATE TABLE queries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text          TEXT NOT NULL,
    response_text       TEXT,
    detected_language   VARCHAR(5),  -- en, hi, ta, mr, bn
    citations           JSONB,  -- [{title, url, source_type, updated_at}]
    latency_ms          JSONB,  -- {detect_ms, translate_ms, embed_ms, retrieve_ms, generate_ms}
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;

CREATE POLICY queries_org_isolation ON queries
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX queries_org_id_idx ON queries(org_id);
