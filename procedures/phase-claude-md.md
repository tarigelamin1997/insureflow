# Procedure: Phase CLAUDE.md

## Guiding Principle

Documentation as infrastructure. A phase CLAUDE.md is not a summary written after the fact — it is the authoritative, self-contained context that makes the phase independently reproducible by anyone: a future engineer, a new collaborator, or a Claude session with no prior conversation history.

Every section must capture three layers:
- **What** — the concrete output, the implementation, the configuration
- **Why** — the reasoning, the constraints, what was rejected and why
- **So what** — implications for other phases, what this enables, what it forecloses

A section that only answers "what" without "why" is incomplete. Fill the template with this standard in mind, not just to populate the fields.

---

Every phase directory must have a `CLAUDE.md` written **before any code is written**. This file is the complete brief for any Claude session that works on this phase. It must be self-contained — a fresh Claude instance should be able to implement the phase by reading only this file plus the root `CLAUDE.md`.

---

## When to Write It

Before touching any implementation file in the phase. The CLAUDE.md is the first commit in any phase branch.

---

## Full Template

Copy this verbatim. Fill every section. Delete nothing.

```markdown
# CLAUDE.md — Phase NN: Title

## What This Builds
[One precise paragraph. What exists after this phase that did not exist before.
 State the concrete outputs: running services, written data, exposed endpoints, registered schemas.
 Do NOT describe the implementation steps — describe the end state.]

## Prerequisites
[Bullet list. What must be running and healthy before this phase starts.
 Use exact Docker service names from the global naming conventions.
 Use exact table/topic/bucket names, not phase numbers.
 If a prerequisite is optional (nice-to-have but not blocking), mark it (optional).]

## Owns These Paths
[Every file and directory this phase creates or modifies.
 List exact paths relative to repo root.
 If this phase modifies a file owned by another phase, flag it explicitly.]

## Decisions
[Bullet list of every non-trivial choice made in this phase.
 Format: "Used X over Y — see decisions/adr-NNN.md"
 If a decision is trivial (no real alternative), state it inline without an ADR.
 Every item here must map to either an ADR file or an inline justification.]

## Interface Contract

### Produces
[Exact names of what this phase outputs for downstream consumption.
 Format by type:
   Kafka topics:    topic.name (schema: Avro/JSON, registry: yes/no)
   Iceberg tables:  namespace.table_name (partition: field, format: v2)
   MinIO paths:     bucket/prefix/
   API endpoints:   METHOD /path (request/response shape)
   dbt models:      model_name (grain: one row per X)
   Metrics:         metric_name (definition, time spine)]

### Consumes
[Exact names of what this phase reads from upstream.
 Same format as Produces.]

### SLA
[Freshness: how stale can this phase's outputs be before they breach an SLO
 Completeness: minimum acceptable row/record coverage
 Latency: if serving layer, P99 target]

## Test Strategy
[Define what quality checks apply to this phase and what the acceptance threshold is for each.
 Read procedures/code-quality.md for the standard test types per phase category.
 Be explicit — if a check does not apply, state why. "No unit tests" requires a justification.

 Format each entry as:
   - Test type: [what is being tested]
   - Tool: [pytest / dbt test / soda scan / latency test / other]
   - Threshold: [coverage % / all-pass / P99 < Xms / row count delta < X%]
   - Blocking: [yes — phase cannot ship if this fails / no — warning only]

 Example entries:
   - Unit tests for transformation functions: pytest, 80% coverage, blocking
   - Soda quality checks: soda scan, all checks pass, blocking
   - PII masking fitness function: pytest contracts/, must pass, blocking
   - Latency: not applicable — this phase has no serving endpoints]

## Procedures
Before writing any of the following file types in this phase, read the linked procedure first:

| Task | Procedure |
|---|---|
| Code quality standards | `procedures/code-quality.md` |
| Error encountered | `procedures/error-logging.md` |
| Chaos scenario | `procedures/chaos-testing.md` |
| Soda quality check | `procedures/soda-check.md` |
| dbt model | `procedures/dbt-model.md` |
| Spark job | `procedures/spark-job.md` |
| Docker healthcheck | `procedures/docker-healthcheck.md` |
| Iceberg table | `procedures/iceberg-table.md` |
| Kafka connector | `procedures/kafka-connector.md` |
| Airflow DAG | `procedures/airflow-dag-factory.md` |

[Keep only the rows relevant to this phase. Remove the rest.]

## Validation Gate
[Exact commands to run to confirm this phase is complete and healthy.
 Must be runnable with docker compose up and no other setup.
 Every command must have an expected output or exit code.

 ROBUSTNESS — read procedures/validation-standard.md. Every criterion here must be:
   (1) Behavioral — assert the component does its job through its real interface, not that it
       exists/runs/is reachable. "psql INSERT then SELECT returns the row", not "container up".
   (2) Paired with a negative case — inject the failure it guards against and assert the gate
       fires. No exceptions: if none can be injected, write `Negative case: N/A — <reason>`.
 Format each criterion as:
   - Positive: <command/assertion + expected output>
   - Negative: <injected failure + expected gate response>   (or `N/A — <reason>`)
 /start-phase rejects any presence-only criterion or any missing negative case / N/A.

 SLO note: for phases 04–11, any pass criterion that depends on Prometheus/Grafana alerting
 (Bronze freshness, Silver completeness, Gold freshness, Feature Store P99, etc.) is marked
 `[validated at Phase 12]` — the alerting it needs does not exist until Phase 12. Validate the
 phase's data-quality and fitness-function criteria at this phase's own close.]

## Fitness Functions
[List every architectural property this phase must maintain.
 Each item maps to a test file in tests/contracts/.
 Format: "property description → tests/contracts/test_filename.py"
 Examples:
   - Bronze layer never reads from Silver namespace → tests/contracts/test_layer_isolation.py
   - PII fields masked before write → tests/contracts/test_pii_masking.py
 ROBUSTNESS (procedures/validation-standard.md): each fitness function must be behavioral AND
 contain a refutation — a negative case proving the test fails when the property is violated
 (feed a raw NIC through → the masking test must fail). A test that cannot fail is not a test.]

## Blast Radius
[What breaks in other phases if this phase fails, degrades, or produces bad data.
 Format: "If X fails → immediate impact on Y → cascading impact on Z"
 Be specific about which downstream services or SLOs are affected.]

## Chaos Scenarios
[List every chaos scenario from `chaos/scenarios/` that must pass before this phase can be closed.
 These are run via `/run-chaos scenario-name` at the `/close-phase` gate.
 Read `chaos/CLAUDE.md` for the availability table — only list scenarios available at this phase.

 Format:
   - scenario-NN-name — one line stating what it proves for this phase

 Example:
   - scenario-06-kafka-partition-loss — proves CDC pauses cleanly and SLO alert fires
   - scenario-04-null-pk-injection — proves Bronze rejects null PKs before write

 If no chaos scenarios apply to this phase, write: "None — this phase has no chaos scenarios.
 Reason: [infrastructure-only / config-only / depends on services not yet active]"]

## Gotchas
[Non-obvious decisions, production-grade considerations, things that look wrong but are intentional.
 Do NOT document obvious things. Only document what would surprise a senior engineer reading this cold.]
```

---

## Field Rules

**What This Builds** — end state only. Not steps. Not "we will configure Debezium to..." — write "Debezium connectors running, capturing changes from all three PostgreSQL source systems, publishing Avro-encoded events to Kafka topics."

**Prerequisites** — use service names, not phase numbers. Wrong: "Phase 3 must be complete." Right: "`kafka`, `schema-registry`, `postgres-pms` must be running and healthy."

**Owns These Paths** — be exhaustive. If this phase touches `docker-compose.yml` to add services, list it. Shared files that multiple phases touch must be listed in every phase that modifies them.

**Decisions** — every ADR written for this phase is listed here. This section is a map, not the content. The content is in `decisions/`.

**Interface Contract** — the most critical section for cross-phase dependency. Downstream phases copy exact names from this section into their Consumes block. Mismatches here are the #1 source of integration failures.

**Validation Gate** — must be runnable by anyone who clones the repo. No "check the UI" — only CLI commands with deterministic outputs.

**Fitness Functions** — every item must have a corresponding file in `tests/contracts/`. If the file does not exist yet, write `→ tests/contracts/test_filename.py [TO BE WRITTEN]` as a reminder.

**Blast Radius** — think two levels deep. Immediate = what stops working. Cascading = what that stoppage causes downstream.

---

## Minimum Viable Phase CLAUDE.md

A phase CLAUDE.md is not acceptable if any of these are missing:
- Interface Contract (Produces + Consumes)
- At least one Fitness Function
- At least one Validation Gate command
- **Every Validation Gate and Fitness Function criterion is behavioral and names its negative case (or `N/A — <reason>`)** — per `procedures/validation-standard.md`. A presence/liveness-only criterion or a missing negative case makes the CLAUDE.md not ready.
- Blast Radius (even if minimal)
- At least one entry in Decisions (even if no ADR — inline justification is fine)
- Test Strategy section filled — every check either has a threshold or an explicit justification for why it doesn't apply
- Chaos Scenarios section filled — either lists applicable scenarios or explicitly states none with a reason
- Procedures section (even if only one row — must not be the full unfiltered table)
