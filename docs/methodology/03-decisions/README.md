# 03 — Decisions

## What

Every non-trivial architectural or technical choice is recorded as an **Architecture Decision Record
(ADR)** at the moment the decision is made — not after implementation, not after the phase closes. An
ADR captures the situation that forced the choice, exactly what was chosen, the alternatives that were
rejected *and why*, and the consequences (what it makes easier, harder, and impossible).

ADRs live where the decision is owned: phase-local choices in `NN-phase/decisions/`, project-wide
choices in root [`decisions/`](../../../decisions/). The template and rules are in
[`procedures/adr-template.md`](../../../procedures/adr-template.md).

## Why

**Why record decisions at all?** Because the most expensive question in any codebase is "why did they
do it this way?" — and the most dangerous answer is a guess. Six months on, a reasonable-looking
change can quietly reverse a decision that was made for a constraint no longer visible in the code. An
ADR makes the reasoning survivable: a reader understands not just the choice, but the constraints that
ruled out the obvious default, before they touch anything.

**Why alternatives are mandatory (minimum two).** "We considered nothing else" means the ADR
shouldn't exist — the decision was trivial. The rejected options, with InsureFlow-specific reasons,
are the most valuable part: they stop the next person from re-litigating a path that was already
walked and abandoned. A rejection reason like "too complex" is not acceptable; it must state what
specifically makes the option unsuitable here.

**Why "Makes impossible" is the load-bearing field.** It's the cross-phase safety net. If a decision
forecloses an option a later phase might reach for, that foreclosure is written down where the later
phase will find it — so the constraint is discovered by reading, not by hitting a wall.

**Why the `Retroactive` status exists.** Sometimes the build diverges from the design — an approach is
planned, then discarded mid-implementation. Rather than a separate deviation-tracking system, the
divergence is captured as an ADR written after the fact, `Status: Retroactive`, reconstructing what was
planned and why it was abandoned. A retroactive ADR is permanent and carries the same standing as an
accepted one. One documentation shape for both forward and backward decisions keeps the system simple.

**Why accepted ADRs are never edited.** Changing the body of an accepted ADR erases the reasoning
history. Instead, the old ADR is marked `Superseded by ADR-NNN`, a new ADR is written, and the new
one references why the original is being reversed. The history of *how the thinking changed* is itself
worth preserving.

## So what

- **No orphaned decisions.** The Locked Global Decisions table in root `CLAUDE.md` carries an
  **ADR-owner** column — every locked choice is assigned a phase (or root) that will hold its full
  ADR. The ADR may be written later, but ownership is fixed now, so no decision floats unaccounted for.
- **The repo explains its own "why-nots."** Because alternatives and consequences are recorded, the
  repository answers not just what was built but what was deliberately *not* built — which is exactly
  what a reviewer evaluating engineering judgment is looking for.
- **Decisions about the methodology are themselves ADRs.** The foundation gates
  ([adr-000](../../../decisions/adr-000-foundation-airtightness.md)) and the validation standard
  ([adr-001](../../../decisions/adr-001-validation-robustness-standard.md)) are recorded the same way
  as technical choices. The system holds itself to its own standard.

## Where this lives in the repo

- The template and field rules: [`procedures/adr-template.md`](../../../procedures/adr-template.md).
- The command that walks a decision through it: [`/write-adr`](../../../.claude/commands/write-adr.md).
- Project-wide ADRs: [`decisions/`](../../../decisions/). Phase-local ADRs: each `NN-phase/decisions/`.
- The locked-decisions summary + ownership: root [`CLAUDE.md`](../../../CLAUDE.md).
