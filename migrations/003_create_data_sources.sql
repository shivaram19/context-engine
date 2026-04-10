-- 003_create_data_sources.sql
-- Data sources table (Google Drive, GitHub, etc.) with encrypted credentials.

CREATE TABLE data_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    source_type     VARCHAR(50) NOT NULL,  -- google_drive, github_pr, github_code, slack, notion
    config          JSONB NOT NULL,        -- encrypted credentials, auth tokens
    last_synced_at  TIMESTAMPTZ,
    status          VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, paused, failed
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY data_sources_org_isolation ON data_sources
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX data_sources_org_id_idx ON data_sources(org_id);
