# 05 — Resilience & Chaos

## What

Chaos testing is a cross-cutting concern, not a phase. The [`chaos/`](../../../chaos/) directory holds
everything needed to deliberately break the platform and verify it responds correctly — schema drift,
data anomalies, service outages, network faults, load bursts. Scenarios become available as each phase
completes and are run at that phase's close gate.

A chaos scenario is a documented experiment: a hypothesis ("if Kafka loses a partition, CDC pauses and
an SLO alert fires within 5 minutes"), an injection, an observation checklist, a pass/fail criterion,
and a cleanup. Results are permanent artifacts — **`ST-NNN`** stress-test documents — never terminal
output that scrolls away.

Coverage is tracked against **six angles**: volume stress, subtle data corruption, time-based
degradation, concurrent operations, cascading failures, and recovery completeness. The six-angle
matrix in [`chaos/CLAUDE.md`](../../../chaos/CLAUDE.md) maps each angle to the scenario that satisfies
it, and every angle must have at least one executed scenario before Phase 12 can close.

## Why

**Why deliberately break a system you're trying to build?** Because "it works" is a claim about the
happy path, and production is not the happy path. A platform earns the label *production-grade* only by
demonstrating it survives and recovers from failure — rejects bad data at the right gate, detects
schema drift, holds its SLOs under load, and self-heals after an outage. Writing "the platform should
handle failures" is not testing; a passing chaos scenario is one where the exact expected response was
documented *before* injection and the observed response matched it.

**Why run scenarios as each phase closes, not at the end.** Deferring chaos to "when the full stack is
built" means a failure mode that should have been caught in Phase 03 has had nine phases to propagate.
Catching it at the phase that owns the behavior keeps the blast radius small and the diagnosis cheap.

**Why six angles instead of "we tested failures."** Each angle catches a class the others miss. The
four obvious categories (schema, data, infrastructure, load) cover volume, corruption, concurrency, and
partial recovery — but two failure classes hide in the gaps: **time-based degradation** (a scheduled
pipeline misses N runs; does the alert fire at the threshold or 30 minutes late?) and **cascading
failures** (two individually-survivable degradations combine into a silent blind spot — Schema
Registry unreachable *and* corrupt timestamps entering Bronze at once). Naming the angles is what makes
"did we really cover failure?" answerable instead of a feeling.

**Why a clean pass still gets documented.** An `ST-NNN` that finds nothing still proves the recovery
mechanism was *tested*, not assumed. "Gaps discovered: None" requires at least one recorded
observation that the expected response actually occurred. The absence of a finding is itself a finding
worth keeping.

## So what

- **Chaos is the negative-case engine for validation.** A validation criterion that guards an infra or
  data failure mode uses a chaos scenario as its negative case (see [04 — Validation](../04-validation/)).
  The two systems reinforce each other: one injection satisfies the gate's proof *and* an angle of the
  coverage matrix.
- **Failures found by chaos are pre-incidents.** A defect surfaced by a scenario is logged as an error
  with `Source: chaos-discovered` — a failure that *would* have reached production if chaos hadn't found
  it first (see [06 — Error Discipline](../06-error-discipline/)). It lives in the owning phase's
  `errors/`, so the close gate blocks on it.
- **Recovery completeness is a first-class angle.** It's not enough that the platform survives the hit;
  after the fix, does it fully self-heal with no data gaps — does Debezium replay the missed events,
  does the next Feature Store cycle produce correct values rather than compounding the error? Surviving
  and recovering are tested as separate properties.
- **Blast radius is reasoned about up front.** Each phase's `CLAUDE.md` states what breaks downstream if
  it fails — immediate impact and cascading impact — so the consequence of a failure is designed-for,
  not discovered during one.

## Where this lives in the repo

- Chaos context and the coverage matrix: [`chaos/CLAUDE.md`](../../../chaos/CLAUDE.md).
- The scenario + `ST-NNN` standard, and the six-angle framework: [`procedures/chaos-testing.md`](../../../procedures/chaos-testing.md).
- Running a scenario: [`/run-chaos`](../../../.claude/commands/run-chaos.md). The close-gate check: `/close-phase` Check 9.
- The service dependency map and blast-radius table: root [`CLAUDE.md`](../../../CLAUDE.md).
