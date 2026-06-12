# Procedure Registry

The authoritative list of every procedure, its status, and which phases consume it.
This file is the **single source of truth** for procedure status — the `procedures/` tree in
root `CLAUDE.md` points here rather than duplicating it.

## Status meaning

- **Written** — the procedure exists and is ready to read before its task.
- **Deferred → Phase NN** — intentionally not written yet. It MUST be authored as the **first
  implementation step of Phase NN**, before any code in that phase. `/start-phase` enforces this:
  it blocks if a procedure marked `Deferred → this phase` is still missing.

A procedure is never referenced as if it exists when it does not. Every reference resolves to
either a Written file or a Deferred entry with an owning phase.

## Registry

| Procedure | Status | Consumed by | Purpose |
|---|---|---|---|
| `phase-claude-md.md` | Written | All phases (`/new-phase`, `/start-phase`) | Phase CLAUDE.md template + field definitions |
| `adr-template.md` | Written | All phases (`/write-adr`) | ADR structure + when to write one |
| `fitness-function.md` | Written | All phases with `tests/contracts/` (`/fitness-check`) | How to write architectural property tests |
| `code-quality.md` | Written | All phases (`/review-phase`) | Pre-commit / CI / PR review quality stack + per-phase test strategy |
| `error-logging.md` | Written | All phases (`/new-error`, `/resolve-error`) | Error file template + workflow |
| `chaos-testing.md` | Written | Phase 03 onward (`/run-chaos`) | Chaos scenario + ST-NNN standard, six-angle framework |
| `validation-standard.md` | Written | All phases (`/start-phase`, `/review-phase`, `/close-phase`) | Gate Robustness Standard — behavioral + negative-case bar for every criterion |
| `seed-data.md` | Written | Phase 02 | Scenario-based seed data — 12 InsureFlow scenarios |
| `foundation-audit.md` | Written | Foundation edits (`/audit-foundation`) | Repeatable consistency sweep of the foundation |
| `docker-healthcheck.md` | Written | Phase 01 onward (every service in `docker-compose.yml`) | Healthcheck patterns per service type |
| `kafka-connector.md` | Deferred → Phase 03 | Phase 03 | Debezium connector config template |
| `airflow-dag-factory.md` | Deferred → Phase 03 | Phase 03 onward (first DAG phase) | YAML DAG factory: idempotent ops, ShortCircuit gate, audit trail |
| `iceberg-table.md` | Deferred → Phase 04 | Phases 04, 05, 06 | Iceberg table creation + partitioning conventions |
| `spark-job.md` | Deferred → Phase 04 | Phases 04, 05 | PySpark job structure + structured-logging standard |
| `soda-check.md` | Deferred → Phase 05 | Phases 05, 06 | Soda Core YAML check patterns per layer |
| `dbt-model.md` | Deferred → Phase 06 | Phase 06 | dbt model documentation standard |

## Rule

When a phase's `## Procedures` table (in its CLAUDE.md) lists a procedure marked `Deferred → this
phase` here, authoring that procedure is the first task of the phase. Once written, update this
registry: change its Status to `Written` and remove the owning-phase tag.
