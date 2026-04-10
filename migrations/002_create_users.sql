-- 002_create_users.sql
-- Users table with org_id and RLS enabled.

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    whatsapp_phone  VARCHAR(20),
    role            VARCHAR(50) NOT NULL DEFAULT 'member',  -- admin or member
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: org_id isolation
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_org_isolation ON users
    USING (
        org_id = current_setting('app.current_org_id', true)::uuid
    );

CREATE INDEX users_org_id_idx ON users(org_id);
