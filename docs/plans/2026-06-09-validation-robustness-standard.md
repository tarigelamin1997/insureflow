# Plan — Validation Robustness Standard (project-wide enforcement)

> **Status: Executed (2026-06-09).** All four enforcement layers shipped. The permanent decision
> record is `decisions/adr-001-validation-robustness-standard.md`; the canonical standard is
> `procedures/validation-standard.md`. This file preserves the execution plan as a portfolio artifact.
> Follows on from [the foundation-airtightness plan](2026-06-09-foundation-airtightness.md).

## Context

The foundation closes every **structural** gap (no spec-first, undocumented parts, empty stubs,
contract drift, unrun chaos, skipped procedure). One boundary remained: the gates force the right
checks to *exist and run*, but cannot judge whether a check is **strong**. A presence/liveness
criterion ("container is up") passes a weak gate while the thing it guards is broken ("Postgres is up
but rejects writes"). That was the last open hole.

This plan imposes a **Gate Robustness Standard** across the entire project so no phase can *author*
or *pass* a weak gate. Documentation + command wiring only — zero architectural change.

**User decision (locked):** maximum rigor — **every** validation criterion must be (1) *behavioral*
(asserts the component does its job, not that it exists) and (2) paired with a **negative case**
(proves the gate fails when it should). No exceptions. Anti-ceremony safeguard: where no failure can
be injected, the criterion must state `Negative case: N/A — <one-line reason>`; silent omission is a
FAIL (consistent with the repo's existing "requires justification" rules).

## The "how": impose at four layers

The lesson that made the foundation airtight — *a standard not wired into a command is a
suggestion* — applied again. Define it once, make every phase inherit it automatically, enforce it at
all three gates, and audit it forever.

```
DEFINE ONCE ──▶ INHERIT VIA TEMPLATE ──▶ ENFORCE AT EVERY GATE ──▶ AUDIT CONTINUOUSLY
 validation-       phase-claude-md.md       /start-phase (entry)      foundation-audit
 standard.md       (all 14 phases           /review-phase (code)      invariant I10
 + adr-001         inherit it)              /close-phase (exit)       (/audit-foundation)
```

## Layer 1 — Define once (single source of truth)
- **New `procedures/validation-standard.md`** — Rule 1 (behavioral, not presence/liveness),
  Rule 2 (negative case, no exceptions; `N/A — reason` where un-injectable), Rule 3 (per-phase
  content comes from the existing fitness-function/code-quality catalogs — this is the bar on top),
  the negative-case mechanism (reuse chaos scenarios + fitness functions), worked examples per layer.
- **New `decisions/adr-001-validation-robustness-standard.md`** (Accepted) — the decision record.
- **`CLAUDE.md`** — bar added to Validation Architecture + a Global Build Standards bullet.
- **`procedures/README.md`** — registers `validation-standard.md` as Written, consumed-by all phases.

## Layer 2 — Inherit via template (reaches all 14 phases automatically)
- **`phase-claude-md.md`** — embedded in the Validation Gate + Fitness Functions guidance and the
  Minimum-Viable checklist (positive + negative format required per criterion).
- **`fitness-function.md`** — "a fitness function must be able to fail" (behavioral + refutable).
- **`code-quality.md`** — per-phase Test Strategy must state each test type's negative case.

## Layer 3 — Enforce at every gate (cannot be skipped)
- **`/start-phase` Check 5 (ENTRY — primary):** adversarially review the just-authored criteria;
  FAIL any presence-only criterion or any missing negative case / `N/A`. Catches a weak gate before code.
- **`/review-phase` Checks 4–5 (CODE):** negative cases must exist as real tests AND have been run
  and failed-correctly.
- **`/close-phase` Check 4 (EXIT):** the Validation Gate run executes each negative case and confirms it fired.
- **`chaos-testing.md`:** chaos scenarios declared the canonical negative-case mechanism — one
  injection satisfies the gate's negative case and the six-angle coverage matrix at once.

## Layer 4 — Audit continuously (stays enforced)
- **`foundation-audit.md` invariant I10** + **`/audit-foundation`** step: sweep every phase CLAUDE.md
  for behavioral + negative-case compliance and confirm the four-layer wiring is intact.

## File Inventory (as executed)
**New (2):** `procedures/validation-standard.md` · `decisions/adr-001-validation-robustness-standard.md`
**Edited (11):** `CLAUDE.md` · `procedures/README.md` · `procedures/phase-claude-md.md` ·
`procedures/fitness-function.md` · `procedures/code-quality.md` · `procedures/chaos-testing.md` ·
`procedures/foundation-audit.md` · `.claude/commands/start-phase.md` · `.claude/commands/review-phase.md` ·
`.claude/commands/close-phase.md` · `.claude/commands/audit-foundation.md`

## Verification
- All 12 references to `validation-standard.md` resolve; the define→inherit→enforce→audit chain has no broken link.
- `/audit-foundation` I10 passes vacuously now ("no phase CLAUDE.md authored yet") with wiring confirmed.
- **Live proof (deferred to Phase 1):** authoring `01-infrastructure/CLAUDE.md` will force `/start-phase`
  to reject a presence-only healthcheck criterion and require its negative case ("healthcheck goes
  `unhealthy` when Postgres rejects writes / is down").
