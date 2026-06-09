# Procedure: Fitness Functions

## Guiding Principle

A fitness function is an automated test that verifies an architectural property — not a business rule, not a data quality check, but a structural guarantee about the system itself. Examples: "Bronze never reads from Silver," "every inference response includes a confidence band," "no service writes to MinIO without going through the Bronze pipeline."

Fitness functions live in `NN-phase/tests/contracts/` and run in CI on every push. They block merge on failure. A fitness function that is commented out or marked xfail at ship time is not a fitness function — it is a placeholder.

---

## When to Write a Fitness Function

Write a fitness function when:
- The property must hold for the architecture to be correct — not just for the current implementation to work
- A future change could silently violate the property without any test catching it
- The property is stated as a guarantee in the phase CLAUDE.md (Blast Radius, Interface Contract, or Fitness Functions sections)

Do NOT write a fitness function for:
- Data quality checks — those belong in Soda Core YAML
- Business logic correctness — those belong in unit tests
- Service availability — that belongs in Docker healthchecks

---

## File Location and Naming

```
NN-phase-name/tests/contracts/test_{property}.py
```

Examples:
- `04-bronze-layer/tests/contracts/test_layer_isolation.py`
- `04-bronze-layer/tests/contracts/test_pii_masking.py`
- `10c-confidence-scoring/tests/contracts/test_confidence_always_present.py`

One file per property. Do not combine unrelated properties in a single file.

---

## Standard Structure

Every fitness function file follows this structure:

```python
"""
Fitness function: [one-line statement of the property being verified]

Property: [the architectural guarantee this test enforces]
Phase: [phase that owns this property]
Fails when: [what change would cause this test to fail]
"""

import pytest
# imports specific to what this test needs to inspect


def test_[property_name]():
    """[Property statement in plain English — should be readable as documentation.]"""
    # Arrange: set up what needs to be inspected (config files, schema definitions,
    # import graphs, Iceberg metadata, API response shapes, etc.)

    # Act: perform the inspection

    # Assert: verify the property holds
    assert ..., "[Clear failure message explaining what property was violated]"
```

---

## Robustness: A Fitness Function Must Be Able to Fail

Per `procedures/validation-standard.md`, every fitness function is subject to the Gate Robustness
Standard:
- **Behavioral** — it inspects the real artifact (import graph, schema, response model, Iceberg
  metadata), not merely that a file or service exists.
- **Refutable** — it must contain (or be paired with) a negative case proving it fails when the
  property is violated. The way to demonstrate this: temporarily introduce the violation (a raw NIC
  in the masked column, a Bronze import of the Silver namespace) and confirm the test goes red. A
  fitness function that passes no matter what the code does is not a fitness function — it is a
  placeholder, the same as an unimplemented `xfail` stub.

When reviewing a fitness function at `/review-phase`, the reviewer must be able to answer "what change
would make this test fail?" with a concrete, specific answer. If the answer is "nothing", the test fails Check 4.

## What Fitness Functions Inspect

Fitness functions do not require a running stack unless they are integration-level contracts. Most inspect static artifacts:

| What to verify | What to inspect |
|---|---|
| Layer isolation | Import statements, Iceberg namespace references in code |
| PII masking | Column definitions, transformation code, schema files |
| Naming conventions | Docker Compose service names, Kafka topic names, MinIO bucket names |
| Interface contracts | Schema definitions, API response models, Avro schemas |
| Confidence band always present | FastAPI response model definition |
| No future data leakage | Feature computation code — verify event_time filtering |
| SCD Type 2 correctness | dbt model SQL — verify valid_from/valid_to/is_current columns |

Integration-level fitness functions (require running services) are marked with `@pytest.mark.integration` and run in CI against the Docker Compose stack, not in the pre-commit hook.

---

## The xfail Stub Pattern

When a fitness function is required but the implementation is not yet written, write a stub — not a passing placeholder:

```python
@pytest.mark.xfail(reason="not yet implemented — Bronze layer not built")
def test_bronze_never_reads_silver():
    """Bronze layer must never reference the Silver Iceberg namespace."""
    # TODO: implement when Bronze layer is built
    assert False
```

Rules for stubs:
- `reason` must state why it is not yet implemented and what phase will implement it
- The stub must contain the test function signature and a comment describing the assertion it will make
- Stubs block merge at `/review-phase` — a stub with xfail cannot ship as the final state
- Remove the xfail marker and implement the assertion before the phase closes

---

## Standard Fitness Functions by Phase

These are the minimum required for each phase type. The `/fitness-check` command verifies these exist.

### Any ingestion phase (CDC, streaming — Phase 03)
- Source record count reaches destination within SLA window
- No data loss: record count at Kafka topic >= record count at source table

### Bronze layer (Phase 04)
- Layer isolation: Bronze code never imports from or queries Silver or Gold namespaces
- PII masking: NIC, email, phone, health data fields are absent or hashed in Bronze output
- Raw fidelity: Bronze schema contains all source fields (no columns silently dropped)
- No business logic: Bronze applies no transformations beyond PII masking and type casting

### Silver layer (Phase 05)
- Layer isolation: Silver never reads from Gold namespace
- Soda gate enforced: Silver pipeline cannot write output if Soda checks report failures
- Deduplication: no duplicate primary keys in Silver output

### Gold layer (Phase 06)
- Referential integrity: all foreign keys in fact tables resolve to dimension records
- SCD Type 2: exactly one `is_current = true` record per business key in dim_policyholder

### AI layer (Phases 10a, 10b, 10c)
- Point-in-time correctness: no feature value uses data with event_time > as_of timestamp
- Confidence band always present: no inference response is missing `confidence_band` field
- Band thresholds match spec: High > 0.85, Medium 0.60–0.85, Low < 0.60

### Serving layer (Phase 11)
- API contract: every FastAPI endpoint returns the declared response schema shape
- No raw PII: no endpoint response includes unmasked NIC, email, or health data

### Observability (Phase 12)
- All 6 SLO alert rules exist in Prometheus rule config
- Every Docker service has a healthcheck defined in docker-compose.yml

---

## CI Integration

Fitness functions run as a dedicated job in `.github/workflows/quality.yml`:

```yaml
fitness-functions:
  - pytest NN-phase-name/tests/contracts/ -v --tb=short
```

They are separate from unit tests. A phase where all unit tests pass but a fitness function fails does not ship.
