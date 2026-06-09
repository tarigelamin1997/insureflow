# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Orientation

**Project:** InsureFlow — production-grade insurance data platform, Medallion lakehouse architecture.
**Status:** Design complete. Zero code written. Implementation starts at Phase 01.
**GitHub target:** `github.com/tarigelamin1997/insureflow`
**Deployment:** 100% offline. Single `docker compose up` brings the entire stack live.

**This file is navigation only.** All deep context — decisions, thought process, gotchas, interfaces, validation — lives inside each phase directory. When working on a phase, read `NN-phase-name/CLAUDE.md` first and treat it as the source of truth for that phase.

---

## Contributor Profile

Built by and for senior data engineers and architects. The documentation, ADRs, and phase context files assume working knowledge across:
Kafka · Spark/PySpark · dbt · Airflow · Iceberg · FastAPI · Terraform · Docker · AWS · Python · SQL.

Nothing is explained from first principles. Every document goes straight to the decision, the tradeoff, and the production-grade implication.

**Documentation and communication standard across this repository:**
- Direct and precise. No filler.
- Conclusion first, reasoning after.
- Bullets over paragraphs. Tables for comparisons. Code blocks for all technical content.
- Intellectual honesty over politeness — if something is wrong in a review or PR, say so directly.
- No closing filler.

---

## Repo Structure

```
insureflow/
├── CLAUDE.md                      # This file — navigation only
├── README.md
├── CONTRACTS.md                   # Cross-phase interface ledger — Produces → Consumes rollup
├── docker-compose.yml             # Single root file — entire stack
├── .env.example
├── .gitignore                     # Updated as new file types are introduced
├── .github/workflows/
│
├── .claude/                       # Root-level only — applies to entire project
│   └── commands/                  # Slash commands, invokable with /command-name
│       ├── new-phase.md           # /new-phase — scaffolds phase directory + CLAUDE.md
│       ├── start-phase.md         # /start-phase — entry gate: prereqs, CLAUDE.md, procedures, fitness stubs
│       ├── write-adr.md           # /write-adr — guides an ADR through the template
│       ├── close-phase.md         # /close-phase — runs completion validation checklist
│       ├── fitness-check.md       # /fitness-check — lists required fitness functions for current phase
│       ├── new-error.md           # /new-error — creates an error file when a failure is encountered
│       ├── resolve-error.md       # /resolve-error — marks an error resolved with full documentation
│       ├── run-chaos.md           # /run-chaos — executes a chaos scenario and validates response
│       ├── review-phase.md        # /review-phase — code quality gate before /close-phase
│       └── audit-foundation.md    # /audit-foundation — read-only consistency sweep of the foundation
│
├── procedures/                    # Reference standards — Claude reads before doing a recurring task
│   └── README.md                  # PROCEDURE REGISTRY — authoritative list, status, consumed-by.
│                                  # Some procedures are Deferred → Phase NN (authored when that
│                                  # phase starts). See the registry for current status of each.
│
├── 01-infrastructure/             # Each phase is a self-contained conviction
├── 02-source-systems/
├── 03-cdc-ingestion/
├── 04-bronze-layer/
├── 05-silver-layer/
├── 06-gold-layer/
├── 07-catalog-lineage/
├── 08-data-contracts/
├── 09-governance-compliance/
├── 10a-feature-store/
├── 10b-rag/
├── 10c-confidence-scoring/
├── 11-serving-bi/
├── 12-observability/
│
├── airflow/                       # Root-level — orchestrates across all phases
│   ├── CLAUDE.md                  # Airflow-specific context (spans all phases)
│   └── dags/factory/pipelines/
│
├── chaos/                         # Root-level — cross-cutting, available from Phase 03 onwards
│   ├── CLAUDE.md                  # Chaos testing context and usage
│   ├── generators/                # Synthetic data generation + anomaly injection
│   ├── schema/                    # Schema drift injection scripts
│   ├── infrastructure/            # Service failure + network chaos scripts
│   ├── load/                      # Burst ingestion + API load tests
│   ├── scenarios/                 # One .md per scenario — inject → observe → pass/fail
│   └── stress-tests/              # ST-NNN documents — one per executed stress test
│
├── errors/                        # Root-level — cross-phase and infrastructure-wide errors only
│   └── ERR-NNN-description.md    # One file per error, open until resolved
│
├── decisions/                     # Root-level — project-wide ADRs not owned by a single phase
│   ├── adr-000-foundation-airtightness.md      # gates + ledgers + entry gate
│   └── adr-001-validation-robustness-standard.md  # behavioral + negative-case bar for all gates
│
└── docs/                          # Project documentation
    └── plans/                     # Archived execution plans — every approved plan is copied here
        └── README.md              # Plan-archive convention (permanent decisions live in ADRs)
```

Each phase directory contains:
```
NN-phase-name/
├── CLAUDE.md        # Full context: decisions, interfaces, fitness functions, blast radius
├── README.md        # What this phase builds and how to run it
├── decisions/       # ADRs local to this phase
├── errors/          # Error logs — one file per error (ERR-NNN-description.md), open until resolved
└── tests/
    ├── unit/
    ├── integration/
    └── contracts/   # Fitness functions — architectural property checks
```

---

## Phase Index

Status legend: `⬜ Not started` · `🚧 In progress` (set by `/start-phase`) · `✅ Complete` (set by `/close-phase`).

| Phase | Title | Status |
|---|---|---|
| 01 | Infrastructure — Docker Compose + Terraform | ⬜ Not started |
| 02 | Source Systems — PostgreSQL schemas + seed data | ⬜ Not started |
| 03 | CDC Ingestion — Debezium + Kafka KRaft | ⬜ Not started |
| 04 | Bronze Layer — Iceberg + MinIO + PII masking | ⬜ Not started |
| 05 | Silver Layer — PySpark + Soda Core | ⬜ Not started |
| 06 | Gold Layer — dbt + Star Schema + SCD Type 2 | ⬜ Not started |
| 07 | Catalog + Lineage — OpenMetadata + OpenLineage | ⬜ Not started |
| 08 | Data Contracts + Schema Drift Detection | ⬜ Not started |
| 09 | Governance — RBAC + PDPL + IFRS 17 | ⬜ Not started |
| 10a | Feature Store — Offline + Online | ⬜ Not started |
| 10b | RAG — Qdrant + sentence-transformers | ⬜ Not started |
| 10c | Confidence Scoring | ⬜ Not started |
| 11 | Serving + BI — DuckDB + FastAPI + Superset | ⬜ Not started |
| 12 | Observability — Prometheus + Grafana + 6 SLOs | ⬜ Not started |

---

## Global Naming Conventions

| Entity | Convention |
|---|---|
| Docker service names | `kafka`, `schema-registry`, `postgres-pms`, `postgres-cms`, `postgres-pfs`, `debezium`, `minio`, `airflow`, `openmetadata`, `marquez`, `qdrant`, `ollama`, `prometheus`, `grafana`, `superset`, `fastapi` |
| Kafka topics | `insureflow.pms.{table}`, `insureflow.cms.{table}`, `insureflow.pfs.{table}` |
| MinIO buckets | `insureflow-bronze`, `insureflow-silver`, `insureflow-gold` |
| Iceberg namespaces | `insureflow.bronze`, `insureflow.silver`, `insureflow.gold` |
| dbt project | `insureflow` |
| Airflow DAG IDs | `insureflow_{layer}_{concern}` |

---

## Documentation Philosophy

Every piece of documentation in this project — phase CLAUDE.md files, ADRs, README files, procedure definitions — must be written to this standard:

**Documentation as infrastructure.** The state of every decision, the reasoning behind every choice, and the implications of every tradeoff live in the files — not in anyone's memory, not in an external tool, not implied by the code. Anyone who clones this repo and reads the docs can reproduce the project and understand why it was built this way without asking a single question.

Every document captures three layers:
- **What** — the concrete output, implementation, configuration
- **Why** — the reasoning, the constraints that shaped the decision, what was rejected and why
- **So what** — the implications for other phases, what this enables, what it forecloses

This serves two purposes that must never be compromised:
1. **Public reproducibility** — this is a public portfolio repo. Any engineer reading it should be able to follow the thought process end to end and reproduce the system from the documentation alone.
2. **Session independence** — any Claude session picking up any phase must be able to operate with full context from that phase's CLAUDE.md alone. No cross-phase context hunting. No reliance on conversation history.

A document that describes WHAT without WHY is incomplete. An ADR without consequences is incomplete. A phase CLAUDE.md with placeholder sections is not ready for implementation.

**Error logging is mandatory at every level.** Every failure encountered during implementation is logged in `NN-phase/errors/` (phase-specific) or `errors/` (root, cross-phase). Before attempting any fix, read the relevant `errors/` directories. A solution that reintroduces a known failed approach is a documentation failure, not an engineering one. Full standard in `procedures/error-logging.md`.

**Plans are archived, not discarded.** Every approved execution plan is copied into `docs/plans/` once executed (`YYYY-MM-DD-title.md`, with a `Status: Executed` header and deviations noted). The plan is the scaffolding; the backing ADR in `decisions/` is the durable record. Together they document the full cycle — what was planned, how it was executed, and why the decision was made. Convention and index: `docs/plans/README.md`.

---

## Procedures and Commands

**Before starting any phase:** read `procedures/phase-claude-md.md` — it defines every required field in a phase CLAUDE.md.

**Before recording any decision:** read `procedures/adr-template.md` — every non-trivial choice gets an ADR in `NN-phase/decisions/`.

**Available slash commands** (invoke with `/command-name` in any Claude Code session):

| Command | When to use |
|---|---|
| `/new-phase` | Scaffolds a phase directory with CLAUDE.md, README, decisions/, tests/ |
| `/start-phase` | Entry gate — after CLAUDE.md is filled, before code: verifies prerequisites ✅, CLAUDE.md complete, required procedures authored, fitness stubs exist; sets phase 🚧 |
| `/write-adr` | Walks through an ADR before any non-trivial decision is implemented |
| `/fitness-check` | Lists and verifies required fitness functions for the current phase |
| `/new-error` | Creates a new error file when a failure is encountered |
| `/resolve-error` | Marks an error resolved, documents root cause and why previous attempts failed |
| `/run-chaos` | Executes a chaos scenario and validates the platform response |
| `/review-phase` | Code quality gate — runs before `/close-phase`. Static analysis, tests, CodeRabbit status. |
| `/close-phase` | Completion gate — documentation, contracts, chaos, phase index. Requires `/review-phase` to pass first. |
| `/audit-foundation` | Read-only consistency sweep of the foundation itself (registry, contracts, chaos matrix, gate wiring). Run before any `/close-phase` and after any foundation edit. |

**Other procedures** in `procedures/` are consulted passively — Claude reads the relevant one before writing a Soda check, dbt model, Spark job, Kafka connector, etc. They do not need to be invoked explicitly. The authoritative list of which procedures exist and which are still `Deferred → Phase NN` is `procedures/README.md` (the procedure registry). A procedure marked deferred is authored as the first step of its owning phase — `/start-phase` enforces this.

---

## Global Build Standards

- **Offline-only** — no cloud services, no paid APIs, no external network calls
- Every service in `docker-compose.yml` has a `healthcheck`
- Every ADR written at decision time, inside the phase that owns the decision
- Every dbt model documented at creation: description, grain, column-level definitions, owner
- Every Airflow DAG is **idempotent** — running it twice for the same execution date produces the same result. Use `MERGE INTO`, `DELETE+INSERT`, or `INSERT OVERWRITE`. Never bare `INSERT` for mutable data. Full pattern in `procedures/airflow-dag-factory.md`
- Every Airflow DAG implements a **ShortCircuit quality gate** — if a Soda or dbt check task fails, downstream tasks in the same DAG are skipped. Bad data never propagates to the next layer automatically
- Every Airflow DAG execution writes an **audit log entry**: `dag_id`, `run_id`, `status`, `started_at`, `duration_ms`, `error_message`. The audit table is the first place to check when debugging a pipeline failure
- **Cross-phase contract validation**: the interface contract ledger is root `CONTRACTS.md`. `/close-phase` Check 8 verifies each closing phase's `Consumes` against the `Produces` of already-closed upstream phases (upstream-oriented, because the downstream consumer does not exist yet at close time) and appends the phase's `Produces` row. Additionally, after every second phase closes, reconcile `CONTRACTS.md` across the last two adjacent closed phases — naming drift compounds, so catch it at phase 2, not phase 8
- **Gate robustness**: every Validation Gate and Fitness Function criterion must be **behavioral** (assert the component does its job, not that it exists/runs) and carry a **negative case** that proves the gate fires when it should — no exceptions; an un-injectable criterion states `Negative case: N/A — <reason>`. Full standard in `procedures/validation-standard.md`, enforced at `/start-phase`, `/review-phase`, `/close-phase`, and audited by `/audit-foundation` (I10)

**Code quality stack** (full detail in `procedures/code-quality.md`):

| Layer | Tools | Fires when |
|---|---|---|
| Pre-commit | ruff · mypy · bandit · ggshield (GitGuardian) | every `git commit` |
| CI | ruff · mypy · bandit · ggshield · pytest · dbt test · soda scan | every push |
| PR review | CodeRabbit (automatic) · `/review-phase` (manual) | every PR, before merge |
| Weekly | pip-audit | scheduled, non-blocking unless CRITICAL |

Test strategy is defined per phase in each phase's `## Test Strategy` section — not a global coverage threshold.

---

## Validation Architecture

Three layers, each phase implements all three. **Every criterion across all three layers must meet the Gate Robustness Standard** (`procedures/validation-standard.md`): behavioral, not presence/liveness, and paired with a negative case that proves it fires. A criterion that only checks something exists or is alive is not a weak gate — it is no gate, and reports green on a broken system.

**1 — Data quality** (does the data meet expectations)
- Soda Core YAML checks at every layer boundary (lives in the phase that produces the data)
- dbt tests for Gold layer (schema + referential integrity + business rules)

**2 — Service health** (is infrastructure alive)
- Docker healthchecks (defined in docker-compose.yml)
- Prometheus SLOs — 6 defined: Bronze freshness · Silver completeness · Gold freshness · Feature Store P99 · Contract compliance · Catalog completeness
- **SLO timing note:** Prometheus + Grafana alerting is built in Phase 12, but the 6 SLOs measure phases 04–11. Those phases therefore close before their alerting exists. SLO-based pass criteria in phases 04–11 are marked `[validated at Phase 12]` in their Validation Gate and are exercised retroactively when Phase 12 closes (this is also why the time-based-degradation chaos scenario is Phase-12-gated). Each pre-12 phase still validates its data-quality and fitness-function criteria at its own close.

**3 — Architectural fitness functions** (do architectural properties hold)
- Automated tests in `NN-phase/tests/contracts/`
- Examples: Bronze never reads Silver, no service bypasses Kafka after CDC is live, PII masked before Bronze write, confidence score always returned with every inference
- These run in CI and block merge on failure

---

## Service Dependency Map

Critical path (longest chain):
```
PostgreSQL → Debezium → Kafka → Spark Bronze → Spark Silver (+Soda)
→ dbt Gold (+dbt tests) → DuckDB → Feature Store → FastAPI → Confidence Scoring
```

Blast radius of key failures:

| Failure | Immediate | Cascading |
|---|---|---|
| Kafka down | CDC stops | Bronze staleness → Silver staleness → SLO breach |
| MinIO down | All Iceberg I/O fails | Everything downstream of Bronze |
| DuckDB down | dbt can't run, offline features fail | Gold stale, features unavailable |
| Airflow down | No orchestration | No scheduled jobs, quality gates, or lineage |
| OpenMetadata down | No governance visibility | Schema drift undetected, contracts unvalidated |
| Ollama down | RAG generation fails | FastAPI `search_knowledge` tool returns 503 — retrieval still works, generation does not |

---

## Architecture — Quick Reference

```
PMS / CMS / PFS (PostgreSQL)
  → Debezium CDC → Kafka KRaft + Schema Registry (Avro)
  → PySpark Streaming → Bronze (Iceberg + MinIO, PII-masked)
  → PySpark + Soda → Silver (Iceberg + MinIO, cleaned)
  → dbt 1.8 + Soda → Gold (Iceberg + MinIO, Star Schema, SCD Type 2)
  → dbt MetricFlow → 7 insurance metrics
  → DuckDB + FastAPI + Superset (serving)
  → Offline Feature Store + Online Feature Store (AI — 10a)
  → Qdrant retrieval + sentence-transformers embeddings + Ollama LLaMA 3.2 3B generation (RAG — 10b)
  → sklearn logistic regression + confidence interval + band routing (Confidence Scoring — 10c)

Orchestration:  Airflow 2.10, DAG factory pattern (YAML-configured)
Governance:     OpenMetadata — catalog, lineage, contracts, schema drift, quality
                Lineage path: pipelines emit OpenLineage events → Marquez collects →
                OpenMetadata ingests for the unified surface (ADR owner: Phase 07)
Observability:  Prometheus + Grafana, 6 SLOs
IaC:            Terraform (Docker provider)
CI/CD:          GitHub Actions

Note: Ollama requires internet access on first run to pull LLaMA 3.2 3B (~2GB). Weights are
cached in a Docker volume. All subsequent runs are fully offline.
```

Always frame as **Medallion architecture** — Bronze/Silver/Gold is the term that resonated with adesso's technical leadership.

---

## Locked Global Decisions

These are not open for discussion unless Tarig explicitly asks. The **ADR owner** column names
the phase (or root) that holds each decision's full ADR — written when that phase arrives, but
ownership is assigned now so no decision is orphaned. The meta-decision that introduced the
foundation gates and ledgers is `decisions/adr-000-foundation-airtightness.md`.

| Decision | Choice | Why (one line) | ADR owner |
|---|---|---|---|
| Table format | Apache Iceberg | Cloud-agnostic — Snowflake, Azure, AWS, local. adesso clients are Azure/Snowflake. | Phase 04 |
| Data catalog | OpenMetadata | Single tool: catalog + lineage + contracts + drift + quality | Phase 07 |
| Lineage emission | OpenLineage → Marquez → OpenMetadata | Pipelines emit OpenLineage events; Marquez collects; OpenMetadata ingests for the unified surface | Phase 07 |
| Data quality | Soda Core | YAML-first, lighter, better Airflow + OpenMetadata integration | Phase 05 |
| Streaming | Kafka KRaft (no Zookeeper) | Same API as MSK, cleaner local setup | Phase 03 |
| Vector DB | Qdrant | Best offline performance, Docker-native | Phase 10b |
| Embeddings | sentence-transformers (local) | Zero API calls, fully offline | Phase 10b |
| RAG generation model | LLaMA 3.2 3B via Ollama | Better instruction following and domain context than 1.5B; CPU-feasible; Docker-native via Ollama | Phase 10b |
| Confidence scoring model | sklearn logistic regression | Structured numerical prediction; calibrated probabilities; auditable coefficients — Insurance Authority explainability requires interpretability, not a black box | Phase 10c |
| Confidence scoring | Always included (Layer 7) | Insurance Authority explainability requirement | Phase 10c |
| AI routing | Dropped | Single model — no routing use case | Phase 10c |
| Foundation gates + ledgers | Entry gate + behavioral close-checks + 3 ledgers | Every stated gate must be command-enforced; cross-phase state needs single sources of truth | `decisions/adr-000` |
