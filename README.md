# InsureFlow — Insurance Data Platform

![Build](https://github.com/tarigelamin1997/insureflow/actions/workflows/quality.yml/badge.svg)
![Release](https://img.shields.io/github/v/release/tarigelamin1997/insureflow)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Stack](https://img.shields.io/badge/stack-Kafka%20%C2%B7%20Iceberg%20%C2%B7%20dbt%20%C2%B7%20Airflow-informational)

A production-grade, fully offline insurance data platform built on a Medallion lakehouse architecture. InsureFlow models the data engineering and governance challenges of a KSA insurance company that has undergone an acquisition — inherited data debt, fragmented source systems, regulatory obligations, and the need for explainable AI decisions. The entire stack runs locally with a single command.

---

## The Problem

Modeled after the post-acquisition reality of a KSA insurance company operating across Motor, Healthcare, Property & Casualty, and Protection & Savings segments. An acquisition merges two distinct system landscapes into one:

- **Duplicate policyholders** — the same person holds policies under two different IDs from two legacy systems
- **Orphan claims** — claims referencing policies that were never migrated from the acquired entity
- **Date format inconsistency** — pre-acquisition records use DD/MM/YYYY, post-acquisition records use ISO 8601
- **Mixed currency** — legacy international reinsurance records carry amounts in USD alongside SAR

These are not hypothetical edge cases. They are seeded deliberately into the source systems to mirror real post-acquisition data debt. The platform ingests this reality, governs it through every layer, and produces a Gold layer that is clean, auditable, and ready for regulatory reporting.

**Regulatory obligations in scope:**

| Regulator | Requirement |
|---|---|
| Insurance Authority (IA) | Primary supervisor — policy, claims, solvency, explainable AI decisions |
| SAMA | Financial oversight — premium investments, capital adequacy |
| PDPL + NDMO | Personal data — NDMO 4-tier classification, PII masking at Bronze |
| IFRS 17 | Insurance contract accounting — mandatory in KSA |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Source Systems (PostgreSQL × 3)         │
│   PMS (Policy)  ·  CMS (Claims)  ·  PFS (Finance)│
└────────────────────┬────────────────────────────┘
                     │ Debezium 2.7 CDC (pgoutput)
                     ▼
┌─────────────────────────────────────────────────┐
│     Kafka 4.0 KRaft + Schema Registry (Avro)     │
└────────────────────┬────────────────────────────┘
                     │ PySpark Structured Streaming
                     ▼
┌─────────────────────────────────────────────────┐
│     Bronze Layer — Iceberg + MinIO               │
│     Raw · PII-masked · append-only               │
└────────────────────┬────────────────────────────┘
                     │ PySpark + Soda Core quality gate
                     ▼
┌─────────────────────────────────────────────────┐
│     Silver Layer — Iceberg + MinIO               │
│     Cleaned · Standardised · Deduplicated        │
└────────────────────┬────────────────────────────┘
                     │ dbt 1.8 + Soda Core quality gate
                     ▼
┌─────────────────────────────────────────────────┐
│     Gold Layer — Iceberg + MinIO                 │
│     Star Schema · SCD Type 2 · dbt MetricFlow   │
└──────┬──────────────────────────────────────────┘
       │
       ├──────────────────────────────────────────┐
       │                                          │
       ▼                                          ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│      Serving Layer       │     │           AI Layer               │
│                          │     │                                  │
│  DuckDB (in-process)     │     │  Feature Store                   │
│  FastAPI (tool APIs)     │     │    Offline: Iceberg + DuckDB     │
│  Apache Superset (BI)    │     │    Online:  FastAPI (P99 <10ms)  │
└─────────────────────────┘     │                                  │
                                │  RAG                             │
                                │    Qdrant + sentence-transformers│
                                │    LLaMA 3.2 3B via Ollama       │
                                │                                  │
                                │  Confidence Scoring              │
                                │    sklearn · probability +       │
                                │    confidence interval + band    │
                                └─────────────────────────────────┘

Orchestration:  Airflow 2.10 — DAG factory pattern (YAML-configured, one YAML per pipeline)
Governance:     OpenMetadata — catalog · lineage · contracts · schema drift · quality
Observability:  Prometheus + Grafana — 6 SLOs defined and alerted
IaC:            Terraform (Docker provider)
CI/CD:          GitHub Actions · CodeRabbit · GitGuardian
```

---

## Tech Stack

| Concern | Technology |
|---|---|
| Source systems | PostgreSQL 16 × 3 (PMS · CMS · PFS) |
| CDC | Debezium 2.7 (pgoutput plugin, logical replication) |
| Streaming | Apache Kafka 4.0 KRaft (no Zookeeper) · Confluent Schema Registry (Avro) |
| Storage | Apache Iceberg format v2 · MinIO (S3-compatible local object store) |
| Processing | Apache Spark (local mode) · PySpark |
| Transformation | dbt 1.8 · dbt MetricFlow (7 insurance metrics) |
| Orchestration | Apache Airflow 2.10 (LocalExecutor, DAG factory) |
| Governance | OpenMetadata · OpenLineage · Marquez |
| Data quality | Soda Core (YAML-defined checks at every layer boundary) |
| Serving | DuckDB · FastAPI · Apache Superset |
| Feature store | Iceberg + DuckDB (offline, point-in-time correct) · FastAPI (online) |
| RAG | Qdrant · sentence-transformers all-MiniLM-L6-v2 · LLaMA 3.2 3B via Ollama |
| Confidence scoring | scikit-learn (logistic regression) · calibrated probability + confidence intervals |
| Observability | Prometheus · Grafana |
| IaC | Terraform (Docker provider) |
| CI/CD | GitHub Actions · CodeRabbit (AI PR review) · GitGuardian (secret scanning) |
| Deployment | Docker Compose — entire stack, single command, fully offline |

**Why Iceberg over Delta Lake:** Cloud-agnostic. Works on Snowflake, Azure, AWS, and locally without modification. The same table format travels to any destination without rearchitecting.

**Why OpenMetadata over DataHub/Atlas:** Single tool covering catalog, lineage, contracts, schema drift detection, and data quality in one platform. Not four tools stitched together.

**Why DuckDB over ClickHouse/Redshift:** In-process, zero server overhead, native Iceberg extension, Snowflake-compatible SQL dialect. No additional service in the stack.

---

## Domain Model

**Three source systems:**

| System | Abbrev | Contents | Scale |
|---|---|---|---|
| Policy Management System | PMS | Policyholders, policies, endorsements, renewals, cancellations, agents, products | 50K policyholders · 80K policies · 3 years |
| Claims Management System | CMS | Claims, claim events, assessments, settlements, reserves, third-party details | 25K claims |
| Premium & Finance System | PFS | Premium transactions, reinsurance entries, GL settlements, IFRS 17 data | 200K transactions |

**Four insurance segments:** Motor · Healthcare · Property & Casualty · Protection & Savings

**Gold layer output:**

```
Facts:       fact_policies · fact_claims · fact_premiums
Dimensions:  dim_policyholder (SCD Type 2) · dim_insurance_product · dim_coverage_type
             dim_agent · dim_date
Marts:       mart_loss_ratio_report · mart_claims_reserve_report
             mart_underwriting_performance · mart_retention_analysis
```

---

## AI Layer

Seven layers, built in sequence:

| Layer | What it does |
|---|---|
| 1 — Training data | Iceberg time travel + versioned datasets + dataset cards in OpenMetadata + Soda pre-training validation gate |
| 2 — Feature store | Offline (Iceberg + DuckDB, point-in-time correct) + Online (FastAPI, P99 < 10ms). 8 insurance ML features. |
| 3 — Semantic layer | dbt MetricFlow — 7 governed insurance metrics: loss ratio, combined ratio, claims frequency, claims severity, policy retention rate, premium growth rate, reinsurance recovery rate |
| 4 — Agent tool APIs | FastAPI scoped tools: `get_policyholder_features`, `get_metric`, `search_knowledge`, `get_claim_status`, `get_policy_details`, `run_quality_check`, `create_training_dataset` |
| 5 — AI observability | PSI drift detection (weekly per feature, alert if PSI > 0.2), inference logging, data quality → model health feedback loop |
| 6 — RAG | Qdrant + sentence-transformers (local embeddings) + LLaMA 3.2 3B via Ollama (local generation). Indexes: OpenMetadata catalog, ADRs, data contracts, regulatory guides, IFRS 17 docs, feature definitions |
| 7 — Confidence scoring | Every inference returns `probability + confidence_interval + confidence_band + decision_routing`. Bands: High (> 0.85 → auto), Medium (0.60–0.85 → review queue), Low (< 0.60 → manual). Required by Insurance Authority explainability standards. |

**8 ML features:** `claim_frequency_12m` · `days_to_settlement` · `policyholder_tenure_years` · `prior_claims_count` · `premium_to_coverage_ratio` · `reinsurance_threshold_proximity` · `cross_product_holding_count` · `claim_amount_vs_premium_ratio`

---

## Governance

OpenMetadata is the single governance platform — not four tools stitched together:

- **Data catalog** — every asset registered, described, and owned
- **Lineage** — end-to-end: PostgreSQL → Bronze → Silver → Gold → Feature Store, visualised and queryable. Emission path: pipelines emit **OpenLineage** events → **Marquez** collects them → **OpenMetadata** ingests for the single governance surface
- **Data contracts** — schema contracts enforced at every layer boundary. Two deliberate drift scenarios: additive (handled gracefully) and breaking (pipeline halt + alert)
- **Schema drift detection** — automated alerts on unexpected schema changes at source
- **Data quality** — Soda Core results surfaced in OpenMetadata alongside the assets they cover

PII handling: NDMO 4-tier classification applied. Sensitive fields (NIC, email, phone, health data) masked at Bronze ingestion. Never present in Silver or Gold in raw form.

---

## Observability

Six SLOs monitored in Prometheus, alerted in Grafana:

| SLO | Target |
|---|---|
| Bronze freshness | Source commit → Bronze write < 15 minutes |
| Silver completeness | > 99.5% of Bronze records reach Silver |
| Gold freshness | Silver → Gold refresh < 1 hour |
| Feature Store latency | Online store P99 < 10ms |
| Contract compliance | Zero unacknowledged contract violations |
| Catalog completeness | > 95% of assets have owner + description |

---

## Implementation Phases

Status: ⬜ Not started · 🚧 In progress · ✅ Complete (released).

| Phase | Title | Status |
|---|---|---|
| 01 | Infrastructure — Docker Compose + Terraform | ✅ `v0.1.0` |
| 02 | Source Systems — PostgreSQL schemas + seed data | 🚧 |
| 03 | CDC Ingestion — Debezium + Kafka KRaft | ⬜ |
| 04 | Bronze Layer — Iceberg + MinIO + PII masking | ⬜ |
| 05 | Silver Layer — PySpark + Soda Core | ⬜ |
| 06 | Gold Layer — dbt + Star Schema + SCD Type 2 | ⬜ |
| 07 | Catalog + Lineage — OpenMetadata + OpenLineage | ⬜ |
| 08 | Data Contracts + Schema Drift Detection | ⬜ |
| 09 | Governance — RBAC + PDPL + IFRS 17 | ⬜ |
| 10a | Feature Store — Offline + Online | ⬜ |
| 10b | RAG — Qdrant + sentence-transformers + LLaMA 3.2 3B | ⬜ |
| 10c | Confidence Scoring — sklearn + confidence intervals | ⬜ |
| 11 | Serving + BI — DuckDB + FastAPI + Superset | ⬜ |
| 12 | Observability — Prometheus + Grafana + 6 SLOs | ⬜ |

---

## Getting Started

> **Prerequisites:** Docker, Docker Compose, Git. Minimum hardware requirements confirmed in Phase 01.

**First-time setup**

```bash
git clone https://github.com/tarigelamin1997/insureflow.git
cd insureflow
cp .env.example .env
```

> **Phase 01 status — infrastructure substrate only.** What runs today is the shared `insureflow`
> Docker network, the named-volume convention, the standard healthcheck pattern, and a single
> `canary` smoke-test service. Data, AI, governance, serving, and observability services land in
> later phases — the one-time ~2 GB Ollama model pull applies from Phase 10b, not yet.
>
> **Why digest pinning?** Every service image is pinned to an immutable digest (a content hash),
> never a floating tag like `latest`, so the exact same bits run on every machine and in air-gapped
> deployments. Terraform pre-stages those digests locally — *so what:* after one online provision the
> stack runs fully offline with no registry pulls. It is optional in Phase 01 (only the canary runs);
> skipping it just means the image is pulled on the first `docker compose up`.
>
> Optional — pre-stage digest-pinned images for fully-offline runs (Terraform image provisioning):
>
> ```bash
> export TF_VAR_canary_image=$(grep '^CANARY_IMAGE=' .env | cut -d= -f2)
> terraform -chdir=01-infrastructure/terraform init
> terraform -chdir=01-infrastructure/terraform apply
> ```

**Run the stack**

```bash
docker compose up -d
docker compose ps                 # canary should report (healthy)
curl -f http://localhost:8080/    # the canary page, over the published port
```

> After Phase 01 this brings up the `canary` smoke-test service only. Service URLs for Airflow,
> Superset, OpenMetadata, Grafana, Kafka UI, and MinIO are added here as those services land in their
> phases (02–12).

---

## Project Structure

```
insureflow/
├── docker-compose.yml         # Entire stack — single entry point
├── .env.example               # All environment variables documented
├── .github/workflows/         # CI: GitGuardian · ruff · mypy · bandit · pytest (dbt/soda added later)
├── CONTRACTS.md               # Cross-phase interface ledger — Produces → Consumes
├── procedures/                # Reference standards for recurring implementation tasks
├── decisions/                 # Project-wide ADRs (adr-000 foundation, adr-001 validation standard)
├── chaos/                     # Chaos engineering — schema drift, data injection, infra failure
├── airflow/                   # DAG factory — orchestrates all phases
├── 01-infrastructure/         # Phase directories — each self-contained
├── 02-source-systems/         # with CLAUDE.md · README · decisions/ · errors/ · tests/
├── ...
└── docs/                      # methodology/ (why we work this way) + plans/ (archived plans)
```

Each phase directory is self-contained: its own documentation, architectural decisions, error logs, and tests. No phase depends on reading another phase's files to function.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
