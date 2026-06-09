# Procedure: Chaos Testing

## Guiding Principle

A chaos scenario is a documented experiment. It has a hypothesis ("if Kafka loses a partition, CDC pauses and an SLO alert fires within 5 minutes"), an injection method, an observation checklist, and a cleanup procedure. It is repeatable, deterministic where possible, and always leaves the stack in a known good state.

Writing "the platform should handle failures" is not chaos testing. A passing chaos scenario is one where the exact expected response is documented before injection, and the observed response matches it.

**Relationship to the Validation Standard.** Chaos scenarios are the canonical *negative-case
mechanism* for the Gate Robustness Standard (`procedures/validation-standard.md`). When a phase's
Validation Gate criterion guards an infrastructure or data failure mode, its required negative case
*is* a chaos scenario — reference it by `scenario-NN` + its `ST-NNN` rather than building a parallel
test. One injection satisfies the gate's negative case and the six-angle coverage matrix at once.

---

## Scenario Categories

**Schema chaos** — proves the contract enforcement layer works
- Additive drift: new nullable column added to source PostgreSQL
- Breaking drift: column renamed or dropped at source
- Type change: column type narrowed (bigint → int) or widened (int → bigint)

**Data chaos** — proves the quality gate layer works
- Null injection: null value in a non-nullable field
- Type mismatch: string in a numeric column
- Referential integrity violation: record referencing a non-existent FK
- Duplicate PK: same primary key inserted twice
- Out-of-range value: negative premium, future birth date, claim amount > policy limit

**Infrastructure chaos** — proves the resilience layer works
- Service outage: kill a dependency (Kafka, MinIO, Schema Registry, Debezium)
- Network partition: Toxiproxy latency or packet loss between two services
- Restart mid-transaction: kill a service while it is processing a batch

**Load chaos** — proves the SLA layer holds under pressure
- Burst ingestion: 10x normal event rate for a sustained period
- Concurrent reads: N simultaneous queries against DuckDB or Feature Store API
- Slow consumer: deliberately lag the Silver processor and observe Bronze backpressure

---

## Six Angles Coverage Framework

Every complete chaos coverage pass must address all six angles. The four categories above cover angles 1, 2, 4, and partial 6. **Angles 3 and 5 are not covered by any current scenario** and require dedicated scenarios before Phase 12 can close.

**Angle 1 — Volume stress** (≈ Load chaos)
Does the pipeline handle 10x data volume? Do queries time out? Does P99 breach SLA threshold?

**Angle 2 — Subtle data corruption** (≈ Data chaos)
Does the DQ framework catch bad data before Gold? Go beyond obvious violations — test statistically impossible but technically valid values (every claim exactly the policy limit), and slow distribution drift (2% daily for 30 days until the feature is out-of-distribution).

**Angle 3 — Time-based degradation** `[NOT COVERED — required before Phase 12 closes]`
What happens when a scheduled pipeline misses N consecutive runs? Do SLO alerts fire at exactly the defined threshold, or is there a gap between the SLO definition and the alert evaluation interval?
InsureFlow scenario: pause Airflow for 7 hours, confirm the Bronze freshness SLO alert (< 15 min threshold) fires correctly and not 30 minutes late.

**Angle 4 — Concurrent operations** (≈ Infrastructure chaos)
Three DAGs writing to the same Iceberg table simultaneously. A CDC INSERT propagating through a Spark streaming job while dbt runs against the same Silver table. Race conditions between concurrent operations are invisible in sequential testing.

**Angle 5 — Cascading failures** `[NOT COVERED — required before Phase 12 closes]`
Two independent degradations that are individually survivable combine to create a blind spot. Neither failure alone is critical — together they allow silent corruption.
InsureFlow scenario: Schema Registry unreachable (drift detector skips silently) AND corrupt timestamps enter Bronze simultaneously (no range check active). Result: Bronze ingests corrupt data with no schema validation firing.

**Angle 6 — Recovery completeness** (≈ Infrastructure chaos + cleanup verification)
After the failure is fixed, does the pipeline fully self-heal with no data gaps? If Debezium was down for 10 minutes, does it replay the missed CDC events? Does the next Feature Store pipeline cycle produce correct values or compound the error?

---

## Scenario File Template

Every scenario lives in `chaos/scenarios/scenario-NN-name.md`. Copy this template exactly.

```markdown
# Chaos Scenario NN — Title

## Category
[Schema / Data / Infrastructure / Load / Time-based Degradation / Cascading Failure]
<!-- The first four are injection-type categories. Time-based Degradation and Cascading Failure
     are the two angles (3 and 5) the injection-type categories do not cover — see the Six Angles
     framework above. Concurrent Operations (Angle 4) and Recovery Completeness (Angle 6) fall
     under Infrastructure. The ST-NNN document for this scenario classifies it by the six-angle
     framework; this Category is its scenario-level tag. -->

## Hypothesis
[One sentence. "If X is injected, the platform will Y within Z time."]

## Prerequisites
[Exact phases that must be closed before this scenario can run.
 List service names that must be healthy.]

## Baseline State
[What to verify before injecting. Commands to confirm the stack is healthy.
 Example: kafka-topics.sh --list, soda scan passes, Prometheus shows 0 active alerts]

## Injection

### What to run
[Exact script path or command. Include all arguments.]

### What it does
[One paragraph. What the script actually modifies — which service, which data, which config.]

## Observation Checklist
[Ordered list of what to observe after injection. Each item has an expected value.
 Format: "Check X → expected: Y → how to verify: Z"

 Example:
 1. Debezium connector status → expected: paused or error → verify: curl connector API
 2. Kafka consumer lag → expected: growing → verify: kafka-consumer-groups.sh
 3. Prometheus SLO alert → expected: firing within 5 min → verify: Grafana alert panel
 4. OpenMetadata drift alert → expected: present → verify: OpenMetadata UI or API]

## Expected Platform Response
[Precise description of what a PASSING scenario looks like.
 Distinguish between: graceful handling (pipeline continues), controlled halt (pipeline stops with alert),
 and self-recovery (platform recovers without manual intervention).]

## Pass Criteria
[Bullet list of binary checks. Each is either true or false — no "approximately" or "mostly".
 Example:
 - Connector status = paused within 30 seconds of injection
 - No messages produced to Kafka topic after connector paused
 - SLO alert fired within 5 minutes
 - No partial or corrupt Iceberg files written to MinIO]

## Fail Criteria
[What constitutes a FAIL. Usually: silent corruption, wrong layer passed bad data, no alert fired.]

## Cleanup

### What to run
[Exact script or commands to restore the stack to baseline.]

### Verify recovery
[Commands to confirm the stack is healthy again before closing the scenario.]

## Notes
[Non-obvious observations. Known timing sensitivities. Retry behaviour.]
```

---

## Stress Test Documentation (ST-NNN)

Stress test results are permanent artifacts — not terminal output. Every executed chaos scenario or stress test is documented in `chaos/stress-tests/ST-NNN-description.md`. A scenario that finds nothing is still documented — the "clean pass" entry proves the recovery mechanism was tested, not assumed.

### Naming Convention

`ST-NNN-short-description.md`
- `NNN` = three-digit sequence, global across all phases, starting at 001
- Short description = kebab-case, describes what was tested (not the outcome)
- Examples: `ST-001-kafka-partition-loss-recovery.md`, `ST-002-null-pk-bronze-rejection.md`

### ST-NNN Template

```markdown
# ST-NNN — Short Description

## Category
[Volume / Data Corruption / Time-based Degradation / Concurrent Operations /
 Cascading Failures / Recovery Completeness]

## Phase(s) Covered
[Which phase(s) this stress test validates]

## Scenario Run
[Reference to chaos/scenarios/scenario-NN-name.md. If ad-hoc: describe the injection exactly.]

## Baseline Before Test
[Row counts, latencies, alert states, error counts — recorded before injection.]

## Result
[What actually happened vs what was expected. Be specific — numbers, not "it worked".]

## Gaps Discovered
[What the platform did NOT do that it should have. One gap per line.
 Write "None" if the platform behaved exactly as expected — but still document the observation.]

## Prevention Implemented
[For each gap: what was added (Soda check, fitness function, alert rule, config change).
 File reference or commit hash. Write "None required" only if no gaps were found.]

## Status
[Clean pass / Gap found — fixed (ERR-NNN) / Gap found — open (ERR-NNN)]
```

### Rules

- A stress test that finds a gap produces an `ERR-NNN` file in the relevant phase `errors/` directory
- `Source: chaos-discovered` on the resulting ERR-NNN file
- "Gaps Discovered: None" still requires at least one observation confirming the expected response was observed
- ST-NNN files are never deleted — a clean pass at Phase 05 is still relevant context at Phase 10

---

## When to Run Scenarios

Run the relevant scenarios at the `/close-phase` gate. The `## Chaos Scenarios` section in each phase CLAUDE.md lists which scenarios to run before that phase can be closed.

Do not defer chaos testing to "when the full stack is built." By that point, a failure mode that should have been caught in Phase 03 has had nine phases to propagate.

---

## Writing the Inject Script

Every inject script follows these rules:

- **Idempotent** — running it twice does not double the damage
- **Scoped** — modifies only what the scenario spec describes, nothing else
- **Reversible** — every inject script has a corresponding cleanup function or script
- **Logged** — prints what it is doing to stdout with timestamps
- **Exits non-zero on failure** — if the injection itself fails, the script must exit with a non-zero code so the test runner knows

Python scripts use `argparse` for configuration (target host, port, intensity). Shell scripts accept the same as positional arguments.

---

## What Is Never Acceptable

- A scenario with no cleanup procedure
- Running cleanup before observation is complete
- A scenario that passes because the observation checklist was skipped
- Marking a scenario as PASS when any pass criterion was not verified
- A chaos scenario that writes to any system outside the local Docker Compose stack
