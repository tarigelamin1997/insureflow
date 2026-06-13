#!/bin/sh
# =============================================================================
# Phase 02 — table-SELECT grant for the replication role (runs after schema init).
#
# Ordered 02- so the postgres entrypoint runs it AFTER 01-schema.sql (tables must
# exist for GRANT ... ON ALL TABLES) and after 00-replication-role.sh (the role
# must exist). Debezium needs SELECT on the captured tables; 00- granted CONNECT only.
#
# Parameterized on $POSTGRES_REPLICATION_USER (the same role 00- created) so the
# role name stays configurable from .env — no hardcoded literal. Escaped server-side
# with format(%I) via \gexec (psql does not interpolate :'var' inside dollar-quoted
# blocks, so the GRANT is built in plain SQL and executed with \gexec).
# eol=lf enforced via .gitattributes — CRLF would break /bin/sh in the container.
# =============================================================================
set -e

: "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER must be set}"

psql -v ON_ERROR_STOP=1 \
  --set=replication_user="$POSTGRES_REPLICATION_USER" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
-- All of this instance's tables exist by now (created by 01-schema.sql), so
-- GRANT ... ON ALL TABLES IN SCHEMA public covers every one of them.
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA public TO %I', :'replication_user')
\gexec
SQL
