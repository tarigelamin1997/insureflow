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
# Idempotent: guarded by a DO block so a re-run (e.g. volume reset) does not error.
# eol=lf enforced via .gitattributes — CRLF would break /bin/sh in the container.
# =============================================================================
set -e

: "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER must be set}"
: "${POSTGRES_REPLICATION_PASSWORD:?POSTGRES_REPLICATION_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	DO \$\$
	BEGIN
	  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${POSTGRES_REPLICATION_USER}') THEN
	    CREATE ROLE "${POSTGRES_REPLICATION_USER}"
	      WITH LOGIN REPLICATION PASSWORD '${POSTGRES_REPLICATION_PASSWORD}';
	  END IF;
	END
	\$\$;

	-- Debezium needs to read the source tables it captures. Grant CONNECT now;
	-- table-level SELECT grants land in Chunk 2 alongside the DDL.
	GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${POSTGRES_REPLICATION_USER}";
SQL
