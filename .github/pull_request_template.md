<!--
InsureFlow PR template. main is protected — every change merges through a PR.
See procedures/code-quality.md (Branching & Pull Request Workflow).
-->

## Summary
<!-- What does this PR change, in one or two sentences? -->

## Phase
<!-- The phase this belongs to (e.g. 04-bronze-layer), or "foundation / tooling" if cross-cutting. -->

## Why
<!-- The reason for the change. Link the ADR if one exists: decisions/adr-NNN or NN-phase/decisions/adr-NNN. -->

## Gates
<!-- Tick what applies. For a phase PR, /review-phase and /close-phase must pass before merge. -->
- [ ] `/review-phase` passed  (or N/A — not a phase)
- [ ] Chaos scenarios run where applicable via `/run-chaos`  (or N/A)
- [ ] CodeRabbit comments resolved or dismissed-with-reason
- [ ] CI green (secret scan + required checks)

## Notes
<!-- Anything a reviewer should know: risks, follow-ups, or deviations from the approved plan. -->
