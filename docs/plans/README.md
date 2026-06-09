# Execution Plans Archive

Every approved execution plan is copied here as a permanent, in-repo artifact.

## The convention

When a plan is approved (via plan mode or otherwise) and then executed, copy it into this folder:

```
docs/plans/YYYY-MM-DD-short-kebab-title.md
```

- **Date prefix** = the date the plan was approved (absolute, not relative).
- Add a one-line **`> Status: Executed (date)`** header noting the outcome and any deviations from
  the literal plan (what changed during execution and why).
- Link forward/backward to related plans and to the ADR that records the decision permanently.

This is part of the project's "documentation as infrastructure" standard: a reader cloning the repo
can follow not just *what* was built and *why* (ADRs), but *how the work was planned and executed* —
the full cycle, end to end.

## Plans vs ADRs — what goes where

| | Plan (here) | ADR (`decisions/` or `NN-phase/decisions/`) |
|---|---|---|
| Captures | the step-by-step execution: workstreams, file inventory, order, verification | the decision: context, what was chosen, alternatives rejected, consequences |
| Lifespan | a snapshot of how a change was carried out | permanent, authoritative record of the choice |
| Source of truth? | no — a portfolio artifact | **yes** — the decision lives here |

A plan without a backing ADR is incomplete for any non-trivial change. The ADR is the durable record;
the plan is the scaffolding preserved alongside it.

## Index

| Plan | Decision record |
|---|---|
| [2026-06-09 — Foundation Airtightness](2026-06-09-foundation-airtightness.md) | `decisions/adr-000-foundation-airtightness.md` |
| [2026-06-09 — Validation Robustness Standard](2026-06-09-validation-robustness-standard.md) | `decisions/adr-001-validation-robustness-standard.md` |

Keep this index current — add a row each time a plan is archived.
