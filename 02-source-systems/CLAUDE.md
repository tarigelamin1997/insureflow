# CLAUDE.md — Phase 02: Source Systems (PostgreSQL schemas + seed data)

## What This Builds

After this phase the stack has three running PostgreSQL source systems — the systems-of-record the
entire platform ingests from — and nothing downstream of them. Concretely: three Postgres services
named exactly `postgres-pms`, `postgres-cms`, and `postgres-pfs`, each on the shared `insureflow`
network, each with a behavioral healthcheck, each digest-pinned in Terraform, each with a named
volume per the `insureflow-<service>-<purpose>` convention. Each database has its schema created
(PMS: 7 tables; CMS: 6 tables; PFS: 4 tables), and is configured for **logical replication**
(`wal_level=logical`, `max_wal_senders>=3`, `max_replication_slots>=3`), exposes a
replication-capable role, and declares the correct `REPLICA IDENTITY` on every table so Debezium can
capture full before/after images in Phase 03. The deliberate post-acquisition seed data is loaded:
the S01 happy-path baseline plus the four DQ scenarios S02–S05 (duplicate policyholders, orphan
claims, mixed date formats, mixed currency). The Kafka topic namespace `insureflow.{pms,cms,pfs}.{table}`
is **reserved** by these schemas (the table names define the topic names) — Phase 03, not this phase,
creates the topics. End state, verified: `docker compose up` brings all three Postgres services to
`healthy`; each accepts writes and serves them back; `pg_settings` confirms logical replication is
on; the seed loader produces exactly the documented edge-case counts.

## Prerequisites

Phase 01 (Infrastructure) is ✅ Complete and its substrate is consumed directly (see Consumes). No
other InsureFlow phase is upstream of this one. Required-healthy when the stack is up:

- The shared `insureflow` Docker network exists (Phase 01 — every Postgres service attaches here)
- Host tooling: Docker Engine ≥ 24 with Compose v2, Terraform ≥ 1.6, Python 3.11 (seed generator + fitness functions + pytest), reachable Docker daemon socket
- Internet access **on first run only** — to pull the `postgres:16` base image and digest-pin it via Terraform; every subsequent run is fully offline (optional after first run)

## Owns These Paths

Net-new (created by this phase):

- `02-source-systems/schema/init/00-replication-role.sh` — shared replication-role bootstrap (Chunk 1)
- `02-source-systems/schema/pms/01-schema.sql` — DDL for the 7 PMS tables (intra-PMS FKs, `policyholders` REPLICA IDENTITY FULL, table SELECT grant to the replication role)
- `02-source-systems/schema/cms/01-schema.sql` — DDL for the 6 CMS tables (claims cross-instance logical refs / NO FK, `claims`/`claim_events`/`reserves` REPLICA IDENTITY FULL)
- `02-source-systems/schema/pfs/01-schema.sql` — DDL for the 4 PFS tables (cross-instance logical refs / NO FK, one intra-PFS FK `gl_settlements`→`premium_transactions`, all DEFAULT)
- `02-source-systems/seed/generate.py` — parameterized scenario seed generator CLI (per `procedures/seed-data.md`)
- `02-source-systems/seed/builder.py` — importable `build_dataset(cfg)` + the seed-self invariant checks (no I/O)
- `02-source-systems/seed/registry.py` — `S01..S12` → builder map; S06–S12 are `NotImplementedError` placeholders (architected, out of scope)
- `02-source-systems/seed/config.py` — `GenConfig`, the seeded RNG, and the `BASELINE`/`FIXED`/`PERCENT` volume model (the percentage-vs-fixed split)
- `02-source-systems/seed/model.py` — typed dataclasses mirroring the 17 schema tables + the `Dataset` container
- `02-source-systems/seed/fields.py` — deterministic synthetic-field helpers (names, NICs, dates, money, enums)
- `02-source-systems/seed/sql.py` — `Dataset` → per-instance SQL serialisation (idempotent `TRUNCATE … RESTART IDENTITY CASCADE` preamble, `OVERRIDING SYSTEM VALUE`)
- `02-source-systems/seed/scenarios/` — one module per seeded scenario (S01–S05 implemented this phase)
- `02-source-systems/seed/output/` — generated SQL (gitignored)
- `02-source-systems/seed/README.md` — how to run the generator, scenario descriptions, the S06–S12 out-of-scope note
- `02-source-systems/seed/load.sh` — generate-then-load script: runs `generate.py` at a chosen `--scale`, then `psql`-loads each `*_seed.sql` into its matching running instance from env connection params (idempotent — the seed SQL TRUNCATEs+RESTART IDENTITY). Documented in `seed/README.md`.
- `02-source-systems/tests/contracts/conftest.py` — shared contract-test fixtures: env-keyed `DsnSpec` resolver + per-instance live `psycopg` connections that `pytest.skip()` (never silently pass) when no DB is reachable, so the CI `fitness-functions` job stays green and the behavioral proof runs against the live stack at close.
- `02-source-systems/tests/unit/conftest.py` — pytest path bootstrap so the unit tests import the `seed` package (the phase dir name is not a legal dotted-module path)
- `02-source-systems/terraform/` — `docker_image` digest pin for `postgres:16` (one resource, follows Phase 01 Terraform pattern)
- `02-source-systems/tests/unit/test_seed_scenarios.py` — seed-self assertions (per `procedures/seed-data.md`)
- `02-source-systems/tests/contracts/` — the fitness-function tests listed below
- `02-source-systems/CLAUDE.md`, `README.md`, `decisions/`, `errors/`

Modifies (shared files owned by the foundation — **flagged**):

- `docker-compose.yml` (root) — appends the three `postgres-*` service blocks, their named volumes, and the schema/seed init wiring; attaches each to `insureflow`; each carries a healthcheck per `procedures/docker-healthcheck.md`
- `.env.example` (root) — adds the three databases' env-var contract (db names, users, passwords, host ports, **host** for the loader/contract tests, the replication role/password)
- `.github/workflows/quality.yml` (root) — adds `psycopg[binary]` to the `lint` (mypy import resolution) and `fitness-functions` (contract-test import) installs; the contract tests skip without a DB so the job stays green
- `CONTRACTS.md` (root) — appends the Phase 02 `Produces` row at close (per `/close-phase` Check 8)
- `README.md` (root) — Getting Started + service URLs, kept honest to what now runs
- `.gitignore` (root) — ensures `02-source-systems/seed/output/` is ignored

## Decisions

Phase-local ADRs (numbered from `001`, a separate sequence from root `decisions/adr-000`/`adr-001`).
These are the five non-trivial choices this phase records — authored at decision time during
implementation. The numbering follows the chunked build order (substrate ADRs land first, in Chunk 1):

Chunk 1 — substrate (written):

- **One shared digest-pinned Postgres image for all three source DBs** (not three image vars) — see `decisions/adr-001-shared-postgres-image.md` (single digest to keep in lockstep with Compose; per-system identity is DB/role/volume/port, not the image)
- **Three separate Postgres instances vs one multi-database instance** — see `decisions/adr-002-three-instances-vs-one.md` (separate instances model three real legacy systems, isolate per-system CDC slots/failure domains, and make CMS→PMS orphan claims a real cross-DB gap rather than an enforceable FK)
- **CDC-readiness as a source property** (`wal_level=logical`, senders/slots ≥ 3, dedicated replication role; set at postmaster start, asserted against the live engine) — see `decisions/adr-004-cdc-readiness-source-property.md`

Chunk 2 — schema (written):

- **`REPLICA IDENTITY FULL` vs `DEFAULT` per table** — see `decisions/adr-003-replica-identity-strategy.md` (FULL on `policyholders`/`claims`/`claim_events`/`reserves` where Silver dedup/SCD/out-of-order/revaluation needs full before-images; DEFAULT on the other 13 where PK suffices — a cost/fidelity tradeoff). Owned by Chunk 2.

Chunk 3 — seed (written):

- **Scenario-based seed generator design** (fixed-seed determinism, composable scenario modules behind a registry, percentage-vs-fixed injection split, SQL-file output vs direct DB load) — see `decisions/adr-005-seed-generator-design.md`. The generator implements S01–S05; S06–S12 are architected (registered) but raise `NotImplementedError` until their consuming phase implements them. Owned by Chunk 3.

## Interface Contract

### Produces

- **Docker services:** `postgres-pms`, `postgres-cms`, `postgres-pfs` (PostgreSQL 16, on `insureflow`, each with a behavioral healthcheck and a `insureflow-postgres-<sys>-data` named volume). These exact service-name strings are asserted by `01-infrastructure/tests/contracts/test_service_naming.py` — any deviation fails CI.
- **PMS schema (7 tables):** `policyholders`, `policies`, `endorsements`, `renewals`, `cancellations`, `agents`, `products` — grain: one row per policyholder / policy / endorsement / renewal / cancellation / agent / product respectively.
- **CMS schema (6 tables):** `claims`, `claim_events`, `assessments`, `settlements`, `reserves`, `third_party_details` — grain: one row per claim / claim event / assessment / settlement / reserve / third-party record respectively.
- **PFS schema (4 tables):** `premium_transactions`, `reinsurance_entries`, `gl_settlements`, `ifrs17_data` — grain: one row per premium transaction / reinsurance entry / GL settlement / IFRS 17 measurement record respectively.
- **CDC-ready Postgres configuration:** each instance set to `wal_level=logical`, `max_wal_senders>=3`, `max_replication_slots>=3`; a replication-capable role (e.g. `REPLICATION` privilege) exists; every table declares an explicit `REPLICA IDENTITY` (`FULL` or `DEFAULT` per ADR-003). This is the published contract Phase 03 Debezium consumes.
- **Seeded data:** S01 happy-path baseline + the four deliberate DQ scenarios — S02 (50 duplicate-NIC policyholder pairs), S03 (30 orphan claims), S04 (mixed date formats), S05 (mixed currency) — loaded deterministically (fixed seed) via the generator.
- **Reserved Kafka namespace:** `insureflow.pms.{table}`, `insureflow.cms.{table}`, `insureflow.pfs.{table}` — RESERVED only. The 17 table names above fix the topic names. **Phase 03 creates the topics; this phase creates no Kafka object.**

### Consumes

From Phase 01 (Infrastructure) — verbatim from `CONTRACTS.md` row 01:

- **Docker network `insureflow`** (bridge) — every Postgres service attaches here for service-name DNS resolution.
- **Named-volume convention `insureflow-<service>-<purpose>`** — each Postgres data volume is declared as `insureflow-postgres-<sys>-data` following this convention.
- **`docker-compose.yml` skeleton + `x-healthcheck-defaults` anchor + reserved service-name namespace** — the three service blocks are appended here, reusing the healthcheck-defaults anchor and the sanctioned names `postgres-pms`/`postgres-cms`/`postgres-pfs`.
- **`.env.example` env-var contract** — extended with the three databases' variables.
- **Healthcheck pattern (`procedures/docker-healthcheck.md`)** — each Postgres healthcheck follows the DB-ping pattern from this procedure.
- **Terraform image-provisioning (digest-pinned `docker_image`)** — `postgres:16` is digest-pinned following the Phase 01 Terraform pattern.
- **Python tooling baseline (ruff/mypy/bandit + pre-commit + CI lint/fitness jobs)** — the seed generator and fitness functions inherit this; no new tooling is introduced.

### SLA

- **Freshness:** N/A — Phase 02 is a system-of-record; no pipeline freshness flows yet (CDC freshness begins at Phase 03/04).
- **Completeness:** the loaded seed must contain the exact documented edge-case counts (S02 = 50 duplicate-NIC pairs, S03 = 30 orphan claims) and zero NULL primary keys across all 17 tables.
- **Latency:** N/A — no serving endpoint. The only timing property: all three Postgres services reach `healthy` within `start_period + interval × retries`.

## Test Strategy

Source-system phase. Every entry names its negative case per `procedures/validation-standard.md`.

- **Schema correctness (behavioral)** — Tool: `psql` against each running DB — Threshold: every declared table exists with a PK; an INSERT then SELECT round-trips — Blocking: yes — Negative: drop a table / omit a PK → the contract test fails.
- **Seed scenario self-assertions** — Tool: `pytest 02-source-systems/tests/unit/test_seed_scenarios.py` (runs against generated SQL per `procedures/seed-data.md`) — Threshold: row counts + scenario invariants exact (S02=50, S03=30) — Blocking: yes — Negative: perturb the generator count → the assertion fails.
- **CDC-config fitness** — Tool: `pytest` querying `pg_settings`/`pg_replication_slots` on the live DB — Threshold: `wal_level=logical`, senders/slots ≥ 3, replication role present — Blocking: yes — Negative: flip `wal_level` to `replica` → the test fails.
- **Null-PK fitness** — Tool: `pytest` aggregate query across all tables — Threshold: zero NULL PKs — Blocking: yes — Negative: inject a NULL-PK row (or a nullable PK column) → the test fails.
- **Lint / type / security** — Tool: ruff, `mypy --strict`, bandit on the seed generator — Threshold: all pass — Blocking: yes — Negative: each fails on an injected violation (inherited Phase 01 baseline).
- **No dbt/Soda/Spark tests** — Justified: those tools enter at Phases 05–06; this phase produces source rows, not lakehouse layers. Quality here is schema + seed-invariant + CDC-config, not layer-boundary checks.

## Procedures

Before writing any of the following file types in this phase, read the linked procedure first:

| Task | Procedure |
|---|---|
| Code quality standards | `procedures/code-quality.md` |
| Error encountered | `procedures/error-logging.md` |
| Docker healthcheck | `procedures/docker-healthcheck.md` |
| Seed data generation | `procedures/seed-data.md` |

> No procedure is `Deferred → Phase 02` in `procedures/README.md`. `seed-data.md` and
> `docker-healthcheck.md` are already `Written`; `kafka-connector.md` / `airflow-dag-factory.md`
> are owned by Phase 03. This phase authors **no** new procedure.

## Validation Gate

Each criterion is **behavioral** (asserts the component does its job through its real interface) and
carries a **negative case** (per `procedures/validation-standard.md`). No criterion depends on
Prometheus/Grafana alerting, so none is deferred `[validated at Phase 12]`.

**One-time setup (brings the three sources up and loads the fixture):**

```bash
cp .env.example .env                      # if not already present
export TF_VAR_postgres_image=$(grep '^POSTGRES_IMAGE=' .env | cut -d= -f2)
docker compose up -d postgres-pms postgres-cms postgres-pfs
docker compose ps                          # wait until all three show (healthy)
SCALE=1 ./02-source-systems/seed/load.sh   # generate + psql-load S01–S05 into all three (idempotent)
pip install "psycopg[binary]==3.2.3"       # contract-test connection driver
```

VG2/VG3/VG4 then run as one command (each fitness test names its own negative case in its
docstring); VG1 is the manual write/serve probe below:

```bash
pytest 02-source-systems/tests/contracts -v -ra
# Expect: every test PASSES (DB present). With NO DB up, every behavioral test SKIPS with an
# explicit reason (deferred proof) and the two pure-config guard tests pass — CI stays green.
```

### VG1 — Each source DB accepts writes and serves them back (behavioral, not a port probe)

- **Positive (runnable):**
  ```bash
  docker compose exec postgres-pms psql -U pms -d pms \
    -c "INSERT INTO agents (agent_code, agent_name) VALUES ('VG1-PROBE','probe') RETURNING agent_id" \
    -c "SELECT agent_name FROM agents WHERE agent_code='VG1-PROBE'"
  ```
  the `RETURNING` row and the follow-up `SELECT` return the same value. Repeat for `postgres-cms` / `postgres-pfs`.
- **Negative:** `docker compose stop postgres-pms` then retry the INSERT → it fails with a non-zero exit; the healthcheck transitions to `unhealthy` within `interval × retries`. Proves the gate reads real DB behavior, not container liveness.

### VG2 — Logical-replication CDC config is active (asserted via the running engine, not file presence)

- **Positive (runnable):** `pytest 02-source-systems/tests/contracts/test_cdc_config_present.py -v` — asserts `SHOW wal_level` = `logical` on all three, `max_wal_senders`/`max_replication_slots` ≥ 3 from `pg_settings`, the replication role exists with `rolreplication = true` in `pg_roles`, and a logical slot can be **created and dropped** (the end-to-end decoding capability).
- **Negative:** start a DB with `command: ["postgres","-c","wal_level=replica"]` (or `ALTER ROLE replicator NOREPLICATION`) and re-run → the `wal_level` assertion fails and `pg_create_logical_replication_slot` errors. Proves the config is read from the live server, not from a `.conf` file on disk.

### VG3 — Deliberate DQ scenarios are present at exact counts (the seed is a test fixture)

- **Positive (runnable):** `pytest 02-source-systems/tests/contracts/test_duplicate_nic_pairs.py 02-source-systems/tests/contracts/test_orphan_claims_count.py -v` — `test_duplicate_nic_pairs` counts NICs in `postgres-pms.policyholders` carried by ≥ 2 distinct `policyholder_id` and asserts **exactly 50**; `test_orphan_claims_count` fetches the PMS `policies.policy_id` set, then counts `postgres-cms.claims` whose non-NULL `policy_id` is **not** in that set and asserts **exactly 30** — the set difference is computed **in Python across the two separate instances** (no FK, no single-DB join), exactly the cross-instance gap ADR-002 creates.
- **Negative:** `SCENARIOS=S01 ./02-source-systems/seed/load.sh` (re-load without S02/S03) → pairs ≠ 50 and orphans ≠ 30 → both tests fail. Proves the gate measures the actual loaded data, not a constant.

### VG4 — No NULL primary keys anywhere (referential foundation for all downstream layers)

- **Positive (runnable):** `pytest 02-source-systems/tests/contracts/test_no_null_pks.py -v` — for every one of the 17 tables (the map mirrors the DDL exactly), `SELECT count(*) WHERE <pk> IS NULL` is 0; the summed total across all 17 is 0.
- **Negative:** `ALTER TABLE agents ALTER COLUMN agent_id DROP NOT NULL` then insert a NULL-PK row → the per-table count > 0 → the aggregate fails. (Without dropping the constraint, Postgres rejects the NULL-PK insert outright — PK integrity is enforced at the source, not assumed.)

## Fitness Functions

**Status: implemented** (the four `xfail` stubs were replaced with real behavioral tests in
Chunk 4). Each is behavioral and **refutable** (per `procedures/fitness-function.md`): a reviewer
can name the change that turns each test red. They connect to the live instances via `psycopg`
with env-keyed connection params (a shared `tests/contracts/conftest.py` fixture), and
**`pytest.skip()` with an explicit, non-silent reason when no DB is reachable** — so the CI
`fitness-functions` job (which has no Postgres) stays green and the behavioral proof runs against
the live stack at phase close. They run in CI via the `fitness-functions` job and live at
`/close-phase`.

- **Exactly 30 orphan claims (S03)** — orphan = a CMS `claims` row whose non-NULL `policy_id` has no matching PMS `policies` row → `tests/contracts/test_orphan_claims_count.py`. **Cross-instance:** PMS and CMS are SEPARATE Postgres instances (ADR-002), so the test fetches the PMS `policy_id` set, then computes the set difference against CMS claim refs **in Python across two connections** — there is no FK and no single-DB join. Refute: change the injected orphan count, or make every claim reference a valid policy → the test fails. Negative case: re-load with S03 disabled → count ≠ 30 → test fails.
- **Exactly 50 duplicate-NIC policyholder pairs (S02)** — NICs in `postgres-pms.policyholders` carried by ≥ 2 distinct `policyholder_id` (`GROUP BY nic HAVING count(DISTINCT policyholder_id) > 1`) → `tests/contracts/test_duplicate_nic_pairs.py`. Refute: dedupe at source, or change the injection count → the test fails. Negative case: re-load with S02 disabled → pairs ≠ 50 → test fails.
- **Zero NULL primary keys across all 17 tables** → `tests/contracts/test_no_null_pks.py` — iterates a `(table, pk)` map mirroring the DDL exactly, composing identifiers with `psycopg.sql.Identifier` (no string interpolation). Refute: introduce a nullable PK column or a NULL-PK row → the aggregate count > 0 → the test fails. Negative case: drop a PK NOT-NULL constraint and inject a NULL-PK fixture row → test fails.
- **CDC config present (`wal_level=logical`, senders/slots ≥ 3, replication role)** — asserted via `pg_settings` / `pg_roles` on the live engine, NOT file presence; also creates + drops a real logical slot (`pg_create_logical_replication_slot`) to prove decoding works end to end → `tests/contracts/test_cdc_config_present.py`. Refute: set `wal_level=replica`, or drop senders/slots below 3, or remove the replication role → the test fails. Negative case: a DB started with default (`replica`) WAL config → the `wal_level` assertion fails and slot creation errors.

## Blast Radius

- **If a source service is renamed off `postgres-pms`/`cms`/`pfs`** → immediate: `01-infrastructure/tests/contracts/test_service_naming.py` fails CI; cascading: Phase 03 Debezium connector config (which targets these exact hostnames) cannot resolve them, and every downstream layer (Bronze 04 → Gold 06) starves.
- **If logical replication is not configured** → immediate: nothing visibly breaks at this phase; cascading: Phase 03 Debezium cannot create a replication slot, CDC never starts, and Bronze freshness SLO (validated at Phase 12) can never be met. This is a silent failure caught only downstream — hence the VG2 behavioral gate here.
- **If `REPLICA IDENTITY` is wrong** (DEFAULT where FULL is needed) → immediate: nothing breaks; cascading: Phase 05 Silver dedup and Phase 06 SCD Type 2 receive incomplete before-images for UPDATE/DELETE events and compute wrong history.
- **If the seed counts drift** (S02/S03 not exact) → immediate: this phase's fitness functions fail; cascading: Phase 05 dedup and Phase 06 referential-integrity gates lose their known-answer fixture and can report green on a broken transformation.
- **If a NULL PK reaches Bronze** → immediate: nothing at source; cascading: Bronze/Silver keying and all FK joins in Gold break unpredictably.

## Chaos Scenarios

None — this phase has no chaos scenarios.

Reason: depends on services not yet active. Per `chaos/CLAUDE.md` (Chaos Availability by Phase) the
earliest runnable scenario requires CDC live (Phase 03) — every scenario perturbs data flow through
Kafka/Debezium or a downstream stateful service that does not exist yet. Phase 02 produces static
source rows with no flow to perturb; its failure modes (write rejection, missing CDC config, seed
drift, NULL PKs) are already proven by the VG1–VG4 negative cases and the fitness-function refutations.

## Gotchas

- **`wal_level=logical` requires a restart, not a reload.** It is a `postmaster`-level GUC. Set it in the image's `postgresql.conf` / `command:` args at container build, not via a runtime `ALTER SYSTEM … ; SELECT pg_reload_conf()` — a reload silently leaves it at `replica` and Phase 03 fails much later with an opaque slot-creation error. VG2's negative case exists precisely to catch this.
- **`REPLICA IDENTITY DEFAULT` only emits the PK on UPDATE/DELETE.** Tables whose downstream needs full before-images (Silver dedup keys on non-PK columns, SCD Type 2 attribute changes) must be `REPLICA IDENTITY FULL` — but FULL doubles WAL volume for wide tables, so it is a per-table decision (ADR-003), not a blanket setting.
- **The reserved Kafka namespace is documentation, not an artifact.** This phase creates no topic, connector, or registry entry. Naming the table set fixes the future topic names so Phase 03 has zero naming ambiguity — but a fitness function here must NOT assert any Kafka object exists (there is none yet).
- **Seed determinism is load-order sensitive.** Fixed random seed (default 42) guarantees the same rows, but orphan/duplicate injection must run after the baseline so the FK-violating rows reference real-but-unmigrated keys deterministically. Generating S03 before S01 would make "orphan" non-reproducible.
- **Three instances share one image but not one config.** All three use the same digest-pinned `postgres:16`, but each needs its own database name, role, and replication slot budget. Do not collapse them into one instance with three schemas — that breaks the "three real legacy systems" model and gives Debezium one slot budget to share (ADR-004).
- **Column sets are not yet specified.** The 17 table names and grains are fixed (README Domain Model); their detailed column definitions are deliberately not invented in this brief and are decided at the Chunk-2 schema-design checkpoint. Do not treat any column list as authoritative until that ADR lands.
