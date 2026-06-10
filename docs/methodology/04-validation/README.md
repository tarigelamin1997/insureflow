# 04 — Validation & Quality

## What

Validation is checked in three independent layers, and every phase implements all three:

1. **Data quality** — Soda Core checks at every layer boundary; dbt tests for Gold.
2. **Service health** — Docker healthchecks; six Prometheus SLOs.
3. **Architectural fitness functions** — automated tests in `tests/contracts/` that verify structural
   properties (e.g. "Bronze never reads Silver," "PII is masked before the Bronze write").

On top of all three sits one universal bar — the **Gate Robustness Standard**
([`procedures/validation-standard.md`](../../../procedures/validation-standard.md),
[adr-001](../../../decisions/adr-001-validation-robustness-standard.md)): every criterion must be
**behavioral** and carry a **negative case**.

Code quality is enforced at three independent moments: pre-commit (ruff, mypy, bandit, ggshield), CI
(the same plus tests, dbt test, soda scan), and PR review (CodeRabbit + `/review-phase`).

## Why

**Why validation is the highest-leverage thing we do.** An agentic build is only as good as its
validation loop. With a strong loop, the system self-corrects until it's right; without one, plausible
but wrong work ships looking green. Spec and context up front make generation cheap — but it's the
validation loop that decides whether what was generated is actually correct. This is the single most
important lever in the whole methodology, which is why it gets its own enforced standard rather than
being left to judgment.

**Why "behavioral, not presence/liveness."** A check that confirms something *exists* or *is running*
reports green while the thing it guards is broken. "The Postgres container is up" passes while Postgres
rejects every write. A behavioral criterion asserts the component *does its job* through its real
interface — *insert a row, read it back, the value matches*. The distinction is the difference between
a check and a decoration.

**Why every criterion needs a negative case — no exceptions.** A quality gate that has never rejected
bad data is unproven; it may be inert and you'd never know. So every criterion pairs its positive
assertion with a negative one that *injects the failure it guards against* and confirms the gate fires
— the Soda check rejects the injected null, the healthcheck goes `unhealthy` when the dependency dies,
the masking test fails on a raw NIC. Where no failure can meaningfully be injected, the criterion must
say so explicitly: `Negative case: N/A — <reason>`. Silent omission is a failure. This is the same
"justify the absence" rule used for error detection and missing unit tests — it makes the no-exceptions
rule mechanically checkable instead of a matter of taste.

> A criterion that only checks existence or liveness is not a weak gate. It is **no gate** — it reports
> green on a broken system, which is worse than no check, because it manufactures false confidence.

**Why fitness functions must be refutable.** A fitness function that passes no matter what the code
does is a placeholder, not a test. The standard: a reviewer must be able to answer "what change would
make this fail?" with a concrete answer. If the answer is "nothing," it doesn't ship.

**Why the negative case reuses the chaos system.** Rather than building a parallel testing apparatus,
a criterion that guards an infrastructure or data failure mode uses a chaos scenario *as* its negative
case (see [05 — Resilience](../05-resilience/)). One injection satisfies the gate's negative case and
the chaos coverage matrix at once.

**Why seed data is a test suite, not filler.** Generic seed data tests the happy path; production
breaks on edge cases. So the seed is twelve named scenarios (duplicate policyholders, orphan claims,
mixed currency, late-arriving claims, IFRS-17 contracts spanning fiscal years…), each targeting a
specific pipeline stage with a concrete pass assertion about a downstream layer. The seed isn't done
when data loads — it's done when the pipeline *behaves correctly* with it.

## So what

- **Weak criteria are caught at authoring time.** Because the standard is enforced at the *entry* gate
  (`/start-phase`), a presence-only criterion is rejected before it shapes any code — the highest-
  leverage point to catch it. The exit gate then *runs* the negative cases, not just the positive ones.
- **The "boundary" the gates couldn't cross is closed.** Plain gates force criteria to exist and run
  but can't judge their strength. The Gate Robustness Standard is precisely the control for that
  residual, imposed across all phases via the four-layer pattern in [02 — Gates](../02-gates-and-enforcement/).
- **Quality is not one coverage number.** Each phase has a different code surface — a PySpark job, a
  dbt model, a FastAPI endpoint, a Debezium config all need different strategies. The per-phase
  `## Test Strategy` defines what applies and why, rather than a single global threshold that would be
  wrong for most phases.

## Where this lives in the repo

- The robustness standard: [`procedures/validation-standard.md`](../../../procedures/validation-standard.md) + [adr-001](../../../decisions/adr-001-validation-robustness-standard.md).
- Fitness functions: [`procedures/fitness-function.md`](../../../procedures/fitness-function.md), [`/fitness-check`](../../../.claude/commands/fitness-check.md).
- Code quality stack: [`procedures/code-quality.md`](../../../procedures/code-quality.md), [`/review-phase`](../../../.claude/commands/review-phase.md).
- Seed-as-test-suite: [`procedures/seed-data.md`](../../../procedures/seed-data.md).
- The three-layer validation architecture: root [`CLAUDE.md`](../../../CLAUDE.md).
