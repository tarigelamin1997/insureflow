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

- `02-source-systems/schema/pms/` — DDL for the 7 PMS tables + role + `REPLICA IDENTITY` + CDC settings
- `02-source-systems/schema/cms/` — DDL for the 6 CMS tables
- `02-source-systems/schema/pfs/` — DDL for the 4 PFS tables
- `02-source-systems/seed/generate.py` — parameterized scenario seed generator (per `procedures/seed-data.md`)
- `02-source-systems/seed/scenarios/` — one module per seeded scenario (S01–S05 in scope this phase)
- `02-source-systems/seed/output/` — generated SQL (gitignored)
- `02-source-systems/seed/README.md` — how to run the generator, scenario descriptions
- `02-source-systems/terraform/` — `docker_image` digest pin for `postgres:16` (one resource, follows Phase 01 Terraform pattern)
- `02-source-systems/tests/unit/test_seed_scenarios.py` — seed-self assertions (per `procedures/seed-data.md`)
- `02-source-systems/tests/contracts/` — the fitness-function tests listed below
- `02-source-systems/CLAUDE.md`, `README.md`, `decisions/`, `errors/`

Modifies (shared files owned by the foundation — **flagged**):

- `docker-compose.yml` (root) — appends the three `postgres-*` service blocks, their named volumes, and the schema/seed init wiring; attaches each to `insureflow`; each carries a healthcheck per `procedures/docker-healthcheck.md`
- `.env.example` (root) — adds the three databases' env-var contract (db names, users, passwords, host ports, the replication role/password)
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

Chunk 2/3 — schema + seed (deferred, authored when those chunks run):

- **`REPLICA IDENTITY FULL` vs `DEFAULT` per table** — `decisions/adr-003-replica-identity-strategy.md` (FULL where Silver dedup/SCD needs full before-images; DEFAULT where PK suffices — a cost/fidelity tradeoff). Owned by Chunk 2.
- **Scenario-based seed generator design** (fixed seed, composable scenarios, SQL output) — `decisions/adr-005-seed-generator-design.md` (reproducibility + scenario composability per `procedures/seed-data.md`). Owned by Chunk 3.

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
carries a **negative case** (per `procedures/validation-standard.md`). Runnable after
`docker compose up` and the seed load, with no other setup. No criterion depends on
Prometheus/Grafana alerting, so none is deferred `[validated at Phase 12]`.

### VG1 — Each source DB accepts writes and serves them back (behavioral, not a port probe)

- **Positive:** for each of `postgres-pms`/`postgres-cms`/`postgres-pfs`, `docker compose exec <svc> psql -U <user> -d <db> -c "INSERT … RETURNING …"` then a `SELECT` returns the same row, value-for-value.
- **Negative:** stop the target service (or revoke write on the table) and retry → the INSERT fails with a non-zero exit; the healthcheck transitions to `unhealthy` within `interval × retries`. Proves the gate reads real DB behavior, not container liveness.

### VG2 — Logical-replication CDC config is active (asserted via the running engine, not file presence)

- **Positive:** `psql -c "SHOW wal_level"` returns `logical` on all three; `SELECT setting FROM pg_settings WHERE name IN ('max_wal_senders','max_replication_slots')` returns ≥ 3 each; the replication role exists with `rolreplication = true`; a test logical slot can be created and dropped.
- **Negative:** set `wal_level=replica` (or remove the replication privilege) and restart → the `SHOW wal_level` assertion fails and creating a logical slot errors. Proves the config is read from the live server, not from a `.conf` file on disk.

### VG3 — Deliberate DQ scenarios are present at exact counts (the seed is a test fixture)

- **Positive:** after loading S01–S05, `SELECT count(*) FROM (… duplicate-NIC pairs …)` returns exactly **50**; `SELECT count(*) FROM claims c LEFT JOIN policies p … WHERE p.policy_id IS NULL` returns exactly **30** orphan claims; both observed through `psql` against the loaded DB.
- **Negative:** regenerate the seed with the S02/S03 injection disabled (or count perturbed) → the counts no longer equal 50 / 30 and the gate fails. Proves the gate measures the actual loaded data, not a constant.

### VG4 — No NULL primary keys anywhere (referential foundation for all downstream layers)

- **Positive:** for every one of the 17 tables, `SELECT count(*) WHERE <pk> IS NULL` returns 0; aggregated, the total is 0.
- **Negative:** attempt to insert a row with a NULL PK → Postgres rejects it (PK NOT NULL constraint), and if the constraint were dropped the fitness query returns > 0 and fails. Proves PK integrity is enforced at the source, not assumed.

## Fitness Functions

Each is behavioral and **refutable** (per `procedures/fitness-function.md`): a reviewer can name the
change that turns each test red. These run in CI via the `fitness-functions` job.

- **Exactly 30 orphan claims (S03)** — orphan = a `claims` row whose `policy_id` has no matching `policies` row → `tests/contracts/test_orphan_claims_count.py` — Refute: change the injected orphan count, or make every claim reference a valid policy → the test fails. Negative case: seed with S03 disabled → count ≠ 30 → test fails.
- **Exactly 50 duplicate-NIC policyholder pairs (S02)** — pairs of `policyholders` rows sharing a NIC under different `policyholder_id` → `tests/contracts/test_duplicate_nic_pairs.py` — Refute: dedupe at source, or change the injection count → the test fails. Negative case: seed with S02 disabled → pairs ≠ 50 → test fails.
- **Zero NULL primary keys across all 17 tables** → `tests/contracts/test_no_null_pks.py` — Refute: introduce a nullable PK column or a NULL-PK row → the aggregate count > 0 → the test fails. Negative case: inject a NULL-PK fixture row → test fails.
- **CDC config present (`wal_level=logical`, senders/slots ≥ 3, replication role)** — asserted via `pg_settings` / `pg_replication_slots` on the live engine, NOT file presence → `tests/contracts/test_cdc_config_present.py` — Refute: set `wal_level=replica`, or drop senders/slots below 3, or remove the replication role → the test fails. Negative case: a DB started with default (`replica`) WAL config → test fails.

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
