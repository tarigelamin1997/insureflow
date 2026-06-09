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
| 01 Infrastructure | ⬜ | _(filled at close)_ | — |
| 02 Source Systems | ⬜ | | |
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
