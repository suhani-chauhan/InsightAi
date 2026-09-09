-- InsightMind AI — Supabase compatibility shim for the zero-setup dev stack.
--
-- The Alembic migrations were written for a Supabase Postgres: they FK to
-- auth.users, call auth.uid() inside RLS policies, and use uuid_generate_v4().
-- A vanilla Postgres has none of that. This script runs once on first db init
-- (docker-entrypoint-initdb.d) and provides just enough for the migrations to
-- apply cleanly. RLS is not actually enforced here — the backend connects as
-- the database superuser, which bypasses row-level security — so the stub
-- auth.uid() only needs to make the policy DDL compile.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id    uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    email text,
    created_at timestamptz DEFAULT now()
);

-- Stubs of the Supabase auth helpers referenced by RLS policies.
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE AS $$ SELECT 'authenticated'::text $$;

CREATE OR REPLACE FUNCTION auth.jwt() RETURNS jsonb
    LANGUAGE sql STABLE AS $$ SELECT '{}'::jsonb $$;

-- The user that BACKEND_DEV_MODE mock auth returns for every request.
INSERT INTO auth.users (id, email)
VALUES ('00000000-0000-0000-0000-000000000000', 'dev@query-mind.com')
ON CONFLICT (id) DO NOTHING;
