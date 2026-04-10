-- 001_create_organisations.sql
-- Root tenant table. No org_id, no RLS. This IS the tenant.

CREATE TABLE organisations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No RLS: organisations is the tenant root.
