-- 007_create_ingestion_jobs.sql
-- Ingestion jobs table: tracks document fetch and chunk indexing.

CREATE TABLE ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    data_source_id  UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, running, done, failed
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    chunks_indexed  INT DEFAULT 0,
    error_text      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY ingestion_jobs_org_isolation ON ingestion_jobs
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX ingestion_jobs_org_id_idx ON ingestion_jobs(org_id);
