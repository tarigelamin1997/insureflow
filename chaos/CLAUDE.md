# CLAUDE.md — Chaos Testing

## What This Is

A cross-cutting concern, not a numbered phase. The `chaos/` directory contains everything needed to deliberately break the InsureFlow platform and verify it responds correctly. It proves the platform is production-grade — not just that it works under happy-path conditions, but that it survives and recovers from failures, rejects bad data, detects schema drift, and holds its SLOs under load.

Chaos testing does not wait until the full stack is built. Scenarios become available as each phase completes and are run immediately at that phase's close gate.

## Directory Structure

```
chaos/
├── CLAUDE.md                          # This file
├── generators/
│   ├── insurance_data_gen.py          # Configurable synthetic data: volume, anomaly rate, schema version
│   └── anomaly_injector.py            # Injects specific DQ issue into live source PostgreSQL
├── schema/
│   ├── additive_drift.py              # Adds nullable column to source — expected: graceful
│   ├── breaking_drift.py              # Renames a column — expected: contract violation, pipeline halt
│   └── type_narrowing.py             # Changes bigint → int — expected: Avro rejection, CDC pauses
├── infrastructure/
│   ├── kill_kafka_partition.sh        # Pauses Kafka via docker pause or Toxiproxy
│   ├── minio_outage.sh                # Takes MinIO offline for N seconds, then restores
│   ├── schema_registry_down.sh        # Stops schema-registry service mid-ingestion
│   └── restart_debezium.sh            # Kills Debezium connector mid-transaction
├── load/
│   ├── burst_ingestion.py             # 10x normal event rate for 60 seconds via anomaly_injector
│   └── api_load_test.py               # Locust — Feature Store P99 under concurrent load
├── scenarios/
│   ├── scenario-01-additive-drift.md
│   ├── scenario-02-breaking-drift.md
│   ├── scenario-03-type-narrowing.md
│   ├── scenario-04-null-pk-injection.md
│   ├── scenario-05-orphan-claim-injection.md
│   ├── scenario-06-kafka-partition-loss.md
│   ├── scenario-07-minio-outage.md
│   ├── scenario-08-schema-registry-down.md
│   ├── scenario-09-debezium-restart.md
│   ├── scenario-10-burst-ingestion.md
│   ├── scenario-11-feature-store-load.md
│   ├── scenario-12-slo-breach-alert.md
│   ├── scenario-13-airflow-pause-time-degradation.md   # Angle 3 — time-based degradation
│   ├── scenario-14-concurrent-dag-writes.md            # Angle 4 — concurrent operations
│   └── scenario-15-cascading-schema-corrupt.md         # Angle 5 — cascading failures
└── stress-tests/                                        # ST-NNN documents — one per executed test
    └── ST-NNN-description.md
```

## Tools

**Toxiproxy** — network chaos proxy. Runs as a Docker service (`toxiproxy`). Simulates latency, packet loss, connection timeout, and bandwidth limits between any two services. Added to `docker-compose.yml` in Phase 03.

**Locust** — load testing. Python-based. Runs `load/api_load_test.py` to stress the Feature Store and FastAPI endpoints.

**pytest** — all chaos scenarios that have deterministic pass/fail criteria are wrapped as pytest tests in `scenarios/`. Scenarios that require manual observation are documented in `.md` files only.

## Chaos Availability by Phase

Scenarios become runnable as phases complete. Do not run a scenario before its prerequisite phase is closed.

| Scenario | Available from Phase |
|---|---|
| Additive schema drift | 03 — CDC running |
| Breaking schema drift | 08 — Data contracts active |
| Type narrowing | 03 — Schema Registry active |
| Null PK injection | 04 — Bronze ingestion active |
| Orphan claim injection | 06 — Gold referential integrity active |
| Kafka partition loss | 03 — CDC running |
| MinIO outage | 04 — Bronze writing to MinIO |
| Schema Registry down | 03 — Avro encoding active |
| Debezium restart | 03 — CDC running |
| Burst ingestion | 05 — Silver pipeline active |
| Feature Store load | 10a — Online Feature Store active |
| SLO breach + alert | 12 — Prometheus + Grafana active |
| Airflow pause — time-based degradation (Angle 3) | 12 — its pass criterion is "Bronze freshness SLO alert fires correctly", which needs Prometheus + Grafana alerting (Phase 12). The Airflow pipeline it pauses exists from Phase 05, but the alert it validates does not exist until Phase 12. |
| Concurrent DAG writes — race condition (Angle 4) | 06 — Gold layer active |
| Cascading failure — Schema Registry + corrupt timestamps (Angle 5) | 08 — Data contracts active |

## Six-Angle Coverage Matrix

The completion rule (below) requires every one of the six stress-testing angles to have at least
one executed scenario before Phase 12 closes. This matrix is the single place that tracks it —
each angle maps to the scenario(s) that satisfy it, the phase from which it can run, and the
`ST-NNN` document that records the executed result. The angle definitions live in
`procedures/chaos-testing.md`. Update the ST-NNN column as scenarios are run.

| Angle | Satisfying scenario(s) | Runnable from | ST-NNN status |
|---|---|---|---|
| 1 — Volume stress | scenario-10 (burst ingestion), `load/api_load_test.py` | Phase 05 | — not yet run |
| 2 — Subtle data corruption | scenario-04 (null PK), scenario-05 (orphan claim) | Phase 04 / 06 | — not yet run |
| 3 — Time-based degradation | scenario-13 (Airflow pause) | Phase 12 | — not yet run |
| 4 — Concurrent operations | scenario-14 (concurrent DAG writes) | Phase 06 | — not yet run |
| 5 — Cascading failures | scenario-15 (Schema Registry + corrupt timestamps) | Phase 08 | — not yet run |
| 6 — Recovery completeness | scenario-07 (MinIO outage), scenario-09 (Debezium restart) | Phase 04 / 03 | — not yet run |

A blank ST-NNN cell at Phase 12 close is a release blocker: an angle that was never exercised.

## How to Run a Scenario

Use the `/run-chaos` command. It handles pre-checks, execution, observation, and cleanup.

```
/run-chaos scenario-06-kafka-partition-loss
```

Manual execution (without the command):
1. Read `chaos/scenarios/scenario-NN-name.md` — understand inject → observe → expected response → cleanup
2. Confirm prerequisites are met (phase availability table above)
3. Run the inject script
4. Observe platform response per the scenario spec
5. Run the cleanup script
6. Confirm platform returns to healthy state

**Always run cleanup.** A chaos scenario that leaves the stack in a broken state contaminates subsequent testing.

## What Good Looks Like

The platform passes chaos testing when:
- Every schema drift scenario produces the documented response (graceful or halt — no silent corruption)
- Every data anomaly is caught at the documented gate (Bronze, Silver, or Gold — not silently passed through)
- Every infrastructure failure triggers the correct SLO alert within the documented window
- The platform self-recovers or requires only the documented manual intervention
- No chaos scenario results in data loss, silent corruption, or incorrect data reaching Gold
- All six angles of the coverage framework have at least one executed scenario before Phase 12 closes
- Every executed scenario — pass or fail — has a corresponding `ST-NNN` document in `chaos/stress-tests/`

## Blast Radius

Chaos scripts modify live source PostgreSQL databases, Kafka topics, and running Docker services. Always run against the local Docker Compose stack only. Never point these scripts at any external system.

Running a chaos scenario while another scenario's cleanup is pending is undefined behaviour. Finish and clean up one scenario before starting another.
