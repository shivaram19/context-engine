-- 004_create_documents.sql
-- Documents table: raw docs from data sources.

CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    data_source_id      UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    source_url          TEXT NOT NULL,
    title               VARCHAR(255) NOT NULL,
    source_type         VARCHAR(50) NOT NULL,  -- google_drive, github_pr, github_code, slack, notion
    authority_score     FLOAT NOT NULL DEFAULT 0.7,  -- 1.0=code, 0.9=pr, 0.7=doc, 0.5=chat
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_stale            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_org_isolation ON documents
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX documents_org_id_idx ON documents(org_id);
