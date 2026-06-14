#!/usr/bin/env bash
# =============================================================================
# Phase 02 — seed generate + load.
#
# One command to (1) generate the deterministic per-instance seed SQL and
# (2) load each file into its matching RUNNING Postgres instance over the
# published host port, using connection params from the environment (.env).
#
# Idempotent: every generated *_seed.sql opens with
# `TRUNCATE … RESTART IDENTITY CASCADE` inside one transaction, so re-running
# this script resets and re-seeds — it never duplicates and never errors on a
# second run. Determinism: a fixed --seed (default 42) yields byte-identical SQL.
#
# Prerequisites:
#   - The three Postgres instances are UP and healthy (`docker compose up -d`
#     and `docker compose ps` shows postgres-pms/cms/pfs healthy).
#   - `python3` (the generator) and `psql` (libpq client) are on PATH on the host.
#   - Connection params exported in the shell or present in .env (see below).
#
# Connection params (per .env.example; defaults shown in []):
#   POSTGRES_PMS_HOST [localhost]  POSTGRES_PMS_HOST_PORT [15432]
#   POSTGRES_PMS_USER [pms]  POSTGRES_PMS_PASSWORD [pms_pw_change_me]  POSTGRES_PMS_DB [pms]
#   …and the CMS / PFS equivalents on ports 15433 / 15434.
#   (Host ports are non-standard 1543x — not 543x — to avoid colliding with a native
#   Postgres on the host's 5432. Container-internal port is still 5432.)
#
# Usage (run from the repository root or anywhere — paths are resolved absolutely):
#   ./02-source-systems/seed/load.sh                      # scale 1.0, scenarios S01..S05
#   SCALE=0.02 ./02-source-systems/seed/load.sh           # CI/fast profile (~1K policyholders)
#   SCALE=0.02 SCENARIOS=all SEED=7 ./02-source-systems/seed/load.sh
#
# Env knobs (all optional):
#   SCALE      [1.0]            → generator --scale
#   SCENARIOS  [S01,S02,S03,S04,S05] → generator --scenarios
#   SEED       [42]            → generator --seed
#
# The .env file at the repo root is auto-sourced if present (so a developer who
# ran `cp .env.example .env` needs no extra exports).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# --- Load .env (repo root) if present, without clobbering already-exported vars. ----------
ENV_FILE="${REPO_ROOT}/.env"
if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  set -a
  . "${ENV_FILE}"
  set +a
fi

SCALE="${SCALE:-1.0}"
SCENARIOS="${SCENARIOS:-S01,S02,S03,S04,S05}"
SEED="${SEED:-42}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PSQL_BIN="${PSQL_BIN:-psql}"

# --- 1. Generate the seed SQL (deterministic, gitignored output). -------------------------
echo "==> generating seed: scenarios=${SCENARIOS} scale=${SCALE} seed=${SEED}"
"${PYTHON_BIN}" "${SCRIPT_DIR}/generate.py" \
  --scenarios "${SCENARIOS}" --scale "${SCALE}" --seed "${SEED}"

# --- 2. Load each instance's file into the matching running Postgres. ----------------------
# Resolve per-instance connection params, falling back to the .env.example defaults so the
# common "brought the stack up with example values" path needs no extra config.
load_instance() {
  sys="$1"            # pms | cms | pfs
  default_port="$2"
  file="${OUTPUT_DIR}/${sys}_seed.sql"

  upper="$(printf '%s' "${sys}" | tr '[:lower:]' '[:upper:]')"
  eval "host=\${POSTGRES_${upper}_HOST:-localhost}"
  eval "port=\${POSTGRES_${upper}_HOST_PORT:-${default_port}}"
  eval "user=\${POSTGRES_${upper}_USER:-${sys}}"
  eval "password=\${POSTGRES_${upper}_PASSWORD:-${sys}_pw_change_me}"
  eval "dbname=\${POSTGRES_${upper}_DB:-${sys}}"

  if [ ! -f "${file}" ]; then
    echo "error: expected generated file not found: ${file}" >&2
    exit 1
  fi

  echo "==> loading ${file} → postgres-${sys} (${host}:${port}/${dbname} as ${user})"
  # PGPASSWORD is the standard non-interactive libpq mechanism; ON_ERROR_STOP makes a bad
  # statement abort the whole load (the file is one BEGIN/COMMIT transaction anyway).
  PGPASSWORD="${password}" "${PSQL_BIN}" \
    --host "${host}" --port "${port}" --username "${user}" --dbname "${dbname}" \
    --no-password --set ON_ERROR_STOP=1 --quiet \
    --file "${file}"
}

load_instance pms 15432
load_instance cms 15433
load_instance pfs 15434

echo "==> seed load complete (idempotent — re-run any time to reset + reseed)"
