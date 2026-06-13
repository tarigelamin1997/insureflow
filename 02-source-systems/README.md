# Phase 02 — Source Systems

## What This Phase Builds
Three PostgreSQL source databases — `postgres-pms` (Policy Management System), `postgres-cms`
(Claims Management System), and `postgres-pfs` (Premium & Finance System) — each running on the
shared `insureflow` network with its schema created, CDC-ready logical-replication configuration,
and the deliberate post-acquisition seed data loaded. This is the system-of-record substrate that
Phase 03 (Debezium CDC) captures from.

## How to Run

All commands run from the **repository root**. Requires Docker Engine ≥ 24 with Compose v2,
plus `python3` and `psql` (libpq client) on PATH on the host for the seed load.

```bash
# 1. Environment contract — copy the example and (for a real deploy) change the passwords.
cp .env.example .env
export TF_VAR_postgres_image=$(grep '^POSTGRES_IMAGE=' .env | cut -d= -f2)

# 2. Bring up the three source instances (each digest-pinned postgres:16, on the insureflow net).
#    First run pulls the base image (internet needed once); every later run is fully offline.
docker compose up -d postgres-pms postgres-cms postgres-pfs
docker compose ps           # wait until postgres-pms / -cms / -pfs all show (healthy)

# 3. Generate + load the deterministic seed (S01 baseline + S02–S05 DQ scenarios) into all three.
#    Idempotent: each *_seed.sql TRUNCATEs + RESTART IDENTITY, so re-running resets and reseeds.
SCALE=1 ./02-source-systems/seed/load.sh          # full domain (~50K policyholders / 80K policies)
# CI / fast profile — same 50/30 edge counts (fixed injections ignore --scale):
SCALE=0.02 ./02-source-systems/seed/load.sh

# 4. (Optional) regenerate the seed SQL only, without loading:
python 02-source-systems/seed/generate.py --scenarios all --scale 0.02
```

Connection params for the loader and the fitness tests come from `.env`
(`POSTGRES_<SYS>_HOST` / `_HOST_PORT` / `_USER` / `_PASSWORD` / `_DB`, for `<SYS>` ∈ PMS/CMS/PFS).
Compose-internal traffic uses the service-name DNS (`postgres-pms` etc.) and ignores the host
vars; the host vars exist so the loader/tests can reach the **published** ports (5432/5433/5434).

## Validation

The four fitness functions are behavioral — they assert against the **live engines**, not files
on disk — and live in `02-source-systems/tests/contracts/`. They connect via `psycopg`; with no
DB reachable they `pytest.skip()` with an explicit reason (never a silent pass), so CI stays
green and the proof runs against the live stack here.

```bash
pip install "psycopg[binary]==3.2.3"
# After steps 1–3 above (stack up + seed loaded):
pytest 02-source-systems/tests/contracts -v -ra      # VG2 + VG3 + VG4
```

| Gate | What it proves (behavioral) | Negative case |
|---|---|---|
| **VG1** — write/serve | `docker compose exec postgres-pms psql -c "INSERT … RETURNING …"` then `SELECT` returns the same row | `docker compose stop postgres-pms` → INSERT exits non-zero; healthcheck → `unhealthy` |
| **VG2** — CDC config (`test_cdc_config_present.py`) | live `SHOW wal_level=logical`, senders/slots ≥ 3 via `pg_settings`, replication role with `rolreplication=true`, a logical slot creates+drops | start a DB on `wal_level=replica` → assertion fails, slot creation errors |
| **VG3** — DQ fixtures (`test_duplicate_nic_pairs.py`, `test_orphan_claims_count.py`) | exactly **50** duplicate-NIC pairs in PMS; exactly **30** orphan claims via a **cross-instance** PMS↔CMS set difference (separate instances, no FK) | `SCENARIOS=S01 ./02-source-systems/seed/load.sh` → pairs ≠ 50, orphans ≠ 30 |
| **VG4** — no NULL PKs (`test_no_null_pks.py`) | NULL-PK count is 0 across all 17 tables (sum 0) | drop a PK NOT-NULL constraint + insert a NULL-PK row → count > 0 |

The seed-self invariants (same counts proven against the in-memory dataset, no Docker) run with
`pytest 02-source-systems/tests/unit -q`. Full seed-generator usage: `seed/README.md`.
