-- 008_create_audit_log.sql
-- Audit log table: append-only for DPDP compliance.

CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(255) NOT NULL,  -- query, ingest, permission_change, etc.
    resource_type   VARCHAR(50),  -- documents, chunks, data_sources, etc.
    resource_id     UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_org_isolation ON audit_log
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX audit_log_org_id_idx ON audit_log(org_id);

-- Append-only: no UPDATE or DELETE allowed (enforced in application layer)
