#!/bin/sh
# InsightAI dev stack — load the demo analytics database.
#
# Runs once on first Postgres init (after 00-supabase-shim.sql). Creates a
# separate "insightai_demo" database (e-commerce / HR / projects / support,
# ~25 tables, ~20k rows) and loads seed_demo_db.sql into it. The backend's
# BACKEND_DEV_MODE startup then auto-registers it as the "Dev - insightai_demo"
# connection, so Chat / Dashboards / Library / Analytics all have real data to
# work with out of the box.
set -e

echo "[dev-db-init] creating insightai_demo database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "CREATE DATABASE insightai_demo OWNER $POSTGRES_USER;"

if [ -f /seed/seed_demo_db.sql ]; then
  echo "[dev-db-init] loading demo data (this takes ~30s the first time)..."
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname insightai_demo \
    -f /seed/seed_demo_db.sql
  echo "[dev-db-init] demo database ready."
else
  echo "[dev-db-init] /seed/seed_demo_db.sql not mounted — skipping demo data."
fi
