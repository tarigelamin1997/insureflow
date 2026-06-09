# ADR-001 — Validation Robustness Standard

## Status
Accepted

## Context
The foundation (ADR-000) made every phase gate command-enforced: a phase cannot ship untested,
undocumented, with empty stubs, with contract drift, with unrun chaos, or with a skipped procedure.
But the gates verify that criteria **exist and run** — they cannot judge whether a criterion is
**strong**. A criterion that asserts presence or liveness ("the container is up") reports green while
the component it guards is broken ("the container is up but Postgres rejects writes"). This is the one
remaining hole: a weak criterion passing a gate manufactures false confidence, which is worse than no
check. The standard must apply uniformly to all 14 phases and be impossible to bypass — a one-size-
fits-all *bar*, even though each phase's actual criteria are specific to it.

## Decision
Adopt a Gate Robustness Standard (`procedures/validation-standard.md`): every criterion in a phase's
`## Validation Gate` and `## Fitness Functions` must be (1) **behavioral** — assert the component does
its job through its real interface, not that it exists/runs/is reachable — and (2) paired with a
**negative case** that injects the guarded failure and proves the gate fires. **No exceptions:** where
no failure can be injected, the criterion must state `Negative case: N/A — <one-line reason>`; silent
omission is a FAIL.

Imposed at four layers so it cannot be bypassed:
- **Define once** — `validation-standard.md` is the single source of truth; surfaced in CLAUDE.md.
- **Inherit via template** — `phase-claude-md.md` embeds it, so all phases get it at authoring time.
- **Enforce at every gate** — `/start-phase` rejects weak criteria before code; `/review-phase`
  confirms negative cases ran and failed-correctly; `/close-phase` executes them in the Validation Gate.
- **Audit continuously** — `/audit-foundation` invariant I10 sweeps every phase CLAUDE.md.

Negative cases reuse existing machinery (chaos scenarios for infra/data failures, fitness functions
for code-level contracts) rather than a parallel test system.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Behavioral bar only (negative cases recommended, not blocking) | Leaves the exact boundary open — a behavioral-but-never-failed check can still be inert. Relies on the judgment we are trying to remove from the critical path. |
| Negative case for guard criteria only (quality gates, healthchecks, masking) | Cleaner, less ceremony — but requires a per-criterion judgment of "is this a guard?", which reintroduces the discretionary gap. Rejected in favor of no-exceptions + justified `N/A`, which is mechanically checkable. |
| Leave it to `/review-phase` + CodeRabbit to catch weak criteria reactively | Too late and unreliable: by review time the weak criterion has already shaped the implementation, and a human reviewer may not spot a plausible-looking liveness check. The entry gate is the high-leverage point. |

## Consequences

### Makes easier
- A weak gate is caught at authoring time (`/start-phase`), before it shapes any code.
- Every gate is proven to fire, not assumed to — false-green is structurally prevented.
- Negative cases double as chaos-coverage and fitness-function artifacts; no duplicate effort.

### Makes harder
- Authoring a phase CLAUDE.md takes more thought — every criterion needs a negative case or a justified `N/A`.
- `/start-phase`, `/review-phase`, `/close-phase` each carry one more substantive check.

### Makes impossible
- Shipping a presence/liveness-only criterion.
- Passing a gate whose negative case was never executed.

### Impact on other phases
- All 14 phases: inherit the bar via the template and must satisfy it at all three gates.
- Phase 01: first live test — `/start-phase` must reject a presence-only healthcheck criterion and
  require its negative case (healthcheck goes `unhealthy` when Postgres rejects writes / is down).
- Builds directly on ADR-000 — same "a standard not wired into a command is a suggestion" principle.
