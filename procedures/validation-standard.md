# Procedure: Validation Standard (Gate Robustness)

## Guiding Principle

The phase gates force the right checks to **exist and run**. This standard forces those checks to be
**strong**. A gate is only as good as its criteria: a criterion that asserts *presence* or *liveness*
("the container is up") passes while the thing it guards is broken ("the container is up but Postgres
rejects writes"). This standard closes that gap. It is the universal **bar** applied on top of the
per-phase criteria catalogs — it does not replace them.

A criterion that does not meet this bar is not a weak gate. It is **no gate** — it will report green
on a broken system. That is worse than no check at all, because it manufactures false confidence.

---

## The Two Rules

Every criterion in a phase's `## Validation Gate` and `## Fitness Functions` must satisfy both.

### Rule 1 — Behavioral, not presence/liveness

A criterion asserts the component **does its job**, observed through its real interface — not that it
exists, is running, or is reachable.

| Weak (presence/liveness) | Robust (behavioral) |
|---|---|
| `postgres-pms` container is `running` | `psql` INSERT a row then SELECT it back — value matches |
| Kafka broker port 9092 is open | Produce a message to `insureflow.pms.policyholders`, consume it, payload decodes against the registered Avro schema |
| Soda container starts | `soda scan` returns 0 failures on known-good data |
| FastAPI returns HTTP 200 | Response body matches the declared Pydantic schema field-for-field |
| Bronze Iceberg table exists | Bronze row count is within ±0.1% of source row count |

### Rule 2 — Negative case, no exceptions

Every criterion pairs its positive assertion with a **negative case** that proves the gate **fires
when it should**. A quality gate that has never rejected bad data is unproven — it may be inert.

- The negative case injects the exact failure the criterion guards against, and asserts the gate
  catches it (fails loud, blocks, alerts, or quarantines — per the criterion).
- **No exceptions.** Where no failure can meaningfully be injected, the criterion must state:
  `Negative case: N/A — <one-line reason>`. A missing negative case with no `N/A` justification is a
  **FAIL**. (Silent omission is never acceptable — same rule as `Detection` in error-logging and
  "No unit tests" in code-quality: the absence must be justified in writing.)

| Criterion | Positive | Negative case |
|---|---|---|
| Postgres healthcheck | INSERT+SELECT succeeds | Stop Postgres / revoke write → healthcheck reports `unhealthy` within its interval |
| Soda Silver gate | scan passes on clean data | Inject a null in a non-nullable column → scan **fails**, ShortCircuit skips downstream |
| PII masked before Bronze | NIC/email/phone absent or hashed in Bronze output | Feed a raw NIC through → fitness function **fails** if it appears unmasked |
| Referential integrity (Gold) | all FKs resolve | Inject an orphan claim → it is excluded from `fact_claims` and reported, not silently dropped |
| Confidence band always present | every inference has `confidence_band` | Force a response without the field → contract test **fails** |
| `terraform plan` exits 0 | clean plan on valid config | `Negative case: N/A — a malformed config already fails `terraform validate` upstream in the same gate` |

---

## Rule 3 — Per-phase content comes from the existing catalogs

This standard is the bar, not the criteria list. The actual criteria for each phase come from:
- `procedures/fitness-function.md` → "Standard Fitness Functions by Phase"
- `procedures/code-quality.md` → "Test types by phase category"

Apply Rules 1 and 2 to every criterion drawn from those catalogs. Per-phase content stays per-phase;
the robustness bar is universal.

---

## The Negative-Case Mechanism — reuse, don't reinvent

Do not build a parallel testing system for negative cases. Use what already exists:

| Failure class | Negative-case mechanism |
|---|---|
| Service / infra failure (down, slow, partitioned) | A chaos scenario — see `procedures/chaos-testing.md`. A guard criterion's negative case **may be** a chaos scenario; reference it by `scenario-NN` and its `ST-NNN`. |
| Bad data (null PK, orphan FK, out-of-range, drift) | Soda check on injected data, or a `chaos/` data scenario |
| Code-level contract (response shape, masking, band) | A fitness function (`tests/contracts/`) with the refutation built in |

This ties the validation standard to the chaos and fitness systems already in place — one negative
case, recorded once, satisfies both the gate and the chaos coverage matrix where applicable.

---

## Where This Is Enforced

This standard is not advisory. It is imposed at four points; a criterion that violates it cannot pass any of them:

1. **Authoring** — `procedures/phase-claude-md.md` template requires it in every phase CLAUDE.md.
2. **Entry gate** — `/start-phase` rejects presence-only criteria and criteria missing a negative case / `N/A` reason, **before any code**.
3. **Code + exit gates** — `/review-phase` confirms each negative case is a real test that ran and failed-correctly; `/close-phase` runs them as part of the Validation Gate.
4. **Audit** — `/audit-foundation` invariant I10 sweeps every phase CLAUDE.md for compliance, continuously.

## What Is Never Acceptable

- A Validation Gate criterion that checks only that something exists, runs, or is reachable.
- A criterion with no negative case and no written `N/A — reason`.
- A negative case that is described but never executed (claimed, not run).
- Marking a gate PASS when its negative case was skipped.
