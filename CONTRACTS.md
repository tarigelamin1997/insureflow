# Cross-Phase Interface Contract Ledger

The single source of truth for what each phase **Produces** and which downstream phase **Consumes**
it. Each phase's own `## Interface Contract` (in its CLAUDE.md) is the detailed record; this file
is the rollup that the `/close-phase` contract check reads.

## How this ledger is used

- **On phase close:** `/close-phase` Check 8 verifies this phase's `Consumes` exactly matches the
  `Produces` of its already-closed **upstream** phases (recorded here). It then appends this phase's
  `Produces` row. The check is upstream-oriented because in a sequential build the downstream
  consumer does not exist yet at close time — only the producer it depends on.
- **Every second phase:** reconcile this ledger across the last two adjacent closed phases (Global
  Build Standard). Naming drift is caught here before it compounds.
- **A mismatch is a FAIL.** A `Consumes` entry naming a topic/table/endpoint that no upstream
  `Produces` row provides is an integration contract violation — fix the name in one place or the
  other before the phase closes.

## Naming source of truth

All names in this ledger use the Global Naming Conventions from root `CLAUDE.md` (Docker service
names, Kafka topics `insureflow.{src}.{table}`, MinIO buckets `insureflow-{layer}`, Iceberg
namespaces `insureflow.{layer}`). This ledger never invents a name that conflicts with that table.

## Ledger

Status legend: ✅ closed (Produces verified) · 🚧 in progress · ⬜ not started.
Rows are filled as each phase closes — the table is empty until Phase 01 closes.

| Phase | Status | Produces (for downstream) | Consumed by |
|---|---|---|---|
| 01 Infrastructure | ✅ | Docker network `insureflow` (bridge); named-volume convention `insureflow-<service>-<purpose>`; root `docker-compose.yml` skeleton + `x-healthcheck-defaults` anchor + reserved service-name namespace; `.env.example` env-var contract; healthcheck pattern (`procedures/docker-healthcheck.md`); Terraform image-provisioning (`01-infrastructure/terraform`, digest-pinned `docker_image`); Python tooling baseline (ruff/mypy/bandit + pre-commit + CI lint/fitness jobs) | All later phases 02–12 — every service attaches to `insureflow`, declares a volume per the convention, carries a healthcheck per the pattern, is digest-pinned in Terraform, and inherits the Python tooling. First consumer: 02 Source Systems (`postgres-pms`/`cms`/`pfs` on `insureflow`, healthchecks, image pins) |
| 02 Source Systems | ✅ | Three PostgreSQL 16 sources `postgres-pms`/`postgres-cms`/`postgres-pfs` (on `insureflow`, behavioral `SELECT 1` healthchecks, named volumes, digest-pinned via `02-source-systems/terraform`); 17-table schemas (PMS 7 / CMS 6 / PFS 4) with explicit `REPLICA IDENTITY` (FULL on `policyholders`/`claims`/`claim_events`/`reserves`, DEFAULT elsewhere); CDC-ready config (`wal_level=logical`, `max_wal_senders`/`max_replication_slots` ≥ 3, dedicated `REPLICATION` role + table SELECT grant); deterministic seed (S01 baseline + S02–S05 data-debt: 50 duplicate-NIC pairs, 30 orphan claims, mixed date formats, mixed currency); **reserved** Kafka topic namespace `insureflow.{pms,cms,pfs}.{table}` (table names fix the topic names — Phase 03 creates the topics, not this phase) | 03 CDC Ingestion — Debezium connects to the three sources via the replication role and the per-table `REPLICA IDENTITY`, capturing the 17 tables into `insureflow.{src}.{table}` |
| 03 CDC Ingestion | ⬜ | | |
| 04 Bronze | ⬜ | | |
| 05 Silver | ⬜ | | |
| 06 Gold | ⬜ | | |
| 07 Catalog + Lineage | ⬜ | | |
| 08 Data Contracts | ⬜ | | |
| 09 Governance | ⬜ | | |
| 10a Feature Store | ⬜ | | |
| 10b RAG | ⬜ | | |
| 10c Confidence Scoring | ⬜ | | |
| 11 Serving + BI | ⬜ | | |
| 12 Observability | ⬜ | | |

> Example of a filled row (illustrative, do not treat as final):
> `| 03 CDC Ingestion | ✅ | Kafka topics insureflow.pms.* / insureflow.cms.* / insureflow.pfs.* (Avro, registry: yes) | 04 Bronze |`
