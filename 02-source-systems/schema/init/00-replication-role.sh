#!/bin/sh
# =============================================================================
# Phase 02 — replication-role bootstrap (runs once, on first DB init).
#
# Mounted into every source Postgres at /docker-entrypoint-initdb.d/ so the
# official postgres:16 entrypoint executes it during cluster initialisation,
# BEFORE the DB accepts external connections. It creates the dedicated
# replication-capable role Phase 03 Debezium logs in as.
#
# WHY a dedicated role (not the superuser POSTGRES_USER):
#   - least privilege — Debezium needs LOGIN + REPLICATION, not superuser.
#   - failure isolation — the CDC credential can be rotated/revoked without
#     touching the application owner role.
#
# REPLICATION is a CLUSTER-LEVEL attribute (pg_roles.rolreplication), so this
# role works for logical decoding on every database in the instance. Per-table
# REPLICA IDENTITY is a separate, Chunk-2 concern (no tables exist yet).
#
# SAFETY: env-derived values are passed as psql variables and escaped server-side
# with format() — %I for identifiers, %L for literals — so a password containing a
# quote can neither break the bootstrap nor inject SQL. (psql does NOT interpolate
# :'var' inside dollar-quoted DO blocks, so we build the statements with format()
# and run them via \gexec, outside any dollar-quoting.)
# Idempotent: CREATE ROLE is guarded by WHERE NOT EXISTS; GRANT is naturally idempotent.
# eol=lf enforced via .gitattributes — CRLF would break /bin/sh in the container.
# =============================================================================
set -e

: "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER must be set}"
: "${POSTGRES_REPLICATION_PASSWORD:?POSTGRES_REPLICATION_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 \
  --set=replication_user="$POSTGRES_REPLICATION_USER" \
  --set=replication_password="$POSTGRES_REPLICATION_PASSWORD" \
  --set=target_db="$POSTGRES_DB" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
-- Create the replication role only if it does not already exist (idempotent).
-- format(%I/%L) escapes the identifier/password server-side; \gexec runs the
-- generated statement. :'var' is interpolated by psql here because it sits in
-- plain SQL, not inside a dollar-quoted block.
SELECT format('CREATE ROLE %I WITH LOGIN REPLICATION PASSWORD %L', :'replication_user', :'replication_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'replication_user')
\gexec

-- Debezium needs to connect to read the source tables it captures. GRANT CONNECT
-- now; table-level SELECT grants land in Chunk 2 alongside the DDL.
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'target_db', :'replication_user')
\gexec
SQL
