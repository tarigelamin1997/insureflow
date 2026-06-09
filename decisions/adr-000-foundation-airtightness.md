# ADR-000 — Foundation Airtightness: Gates, Ledgers, and the Entry Gate

## Status
Accepted

## Context
InsureFlow is a blueprint — the full mainframe (commands, procedures, naming, phase roadmap)
is laid down before Phase 01. A two-pass audit found the architecture and cross-document facts
internally consistent, but the *foundation methodology* had structural gaps that would surface
the moment implementation began. Three root causes accounted for every finding:

1. Documentation was gated, behavior was not. Every ADR, error, and CLAUDE.md section had an
   exit gate, but chaos execution and cross-phase contract validation were described as gates
   that no command enforced.
2. There was no single source of truth for cross-phase concerns. Procedure status, interface
   contracts, and chaos coverage lived as scattered prose and drifted (the procedures tree in
   CLAUDE.md listed files that did not exist and omitted three that did).
3. There were two exit gates (`/review-phase`, `/close-phase`) and zero entry gate, so
   "CLAUDE.md before code", "prerequisites met", and "author this phase's procedures" were
   policy without enforcement.

This ADR is the meta-decision that records why the foundation was restructured before any phase
shipped. Per the repository's own standard, a non-trivial change to the build methodology must
itself be an ADR. This is a root-level (cross-phase) decision, so it lives in `decisions/` at
the repo root rather than in a single phase.

## Decision
Introduce three ledgers, one entry gate, two new behavioral close-checks, and a repeatable
audit — documentation and tooling only, with zero change to the locked phase order or tech stack.

- **Ledgers (single sources of truth):**
  - `procedures/README.md` — procedure registry: every procedure → Status (`Written` /
    `Deferred → Phase NN`) → consumed-by phases.
  - `CONTRACTS.md` (root) — cross-phase interface ledger: every phase's `Produces → consumed-by`.
  - Chaos coverage matrix in `chaos/CLAUDE.md` — six angles × satisfying scenario × phase × ST-NNN.
- **Entry gate:** new `/start-phase` command — verifies prerequisites are ✅, CLAUDE.md is filled,
  required procedures exist (authoring any `Deferred → this phase` now), fitness stubs exist, and
  sets phase status to 🚧 in-progress.
- **Behavioral close-checks:** `/close-phase` gains Check 9 (every listed chaos scenario has a
  passing ST-NNN) and its Check 8 is rewritten from a downstream (inert) to an upstream contract
  check against `CONTRACTS.md`. Check 6 is broadened to flag open root errors.
- **Repeatable audit:** new `/audit-foundation` command + `procedures/foundation-audit.md` re-run
  the consistency sweep on demand, turning a one-time audit into a standing gate.
- **Decision ownership:** the Locked Global Decisions table in CLAUDE.md gains an ADR-owner column
  so every global choice has an assigned home for its full ADR.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Leave gaps, fix reactively during phases | The user's explicit priority is an airtight foundation *before* implementation; reactive fixes mean each phase re-discovers the same structural gap and contract drift compounds (the audit's M2). |
| Enforce everything inside existing commands (no new commands) | No place to enforce entry-time rules (prereqs, procedure authoring, CLAUDE.md completeness). Folding entry logic into `/new-phase` conflates scaffolding with readiness; a distinct `/start-phase` preserves single-responsibility and entry/exit symmetry. |
| Track procedure/contract/chaos state inline in CLAUDE.md only | CLAUDE.md is "navigation only" by its own philosophy; embedding mutable cross-phase state there guarantees drift. Dedicated ledger files keep state where it is maintained and audited. |
| Restructure to incremental observability (each phase owns its SLOs) | Larger change to locked phase scope/order. Rejected in favor of a retroactive-validation note; revisit only if SLO-blind early phases prove painful in practice. |

## Consequences

### Makes easier
- Every stated gate is now enforced by a command — chaos and contract validation can no longer be silently skipped.
- Cross-phase drift is caught by ledgers and a repeatable `/audit-foundation`, not by memory.
- A fresh session starting any phase has an unambiguous, gated entry path.

### Makes harder
- One more command in the lifecycle (`/start-phase`) and three ledger files to keep current — but each is the canonical source, reducing total maintenance surface.
- `/close-phase` is heavier (two more substantive checks).

### Makes impossible
- A phase can no longer close with unrun chaos scenarios, unverified upstream contracts, or open root errors.
- A `Deferred → Phase NN` procedure can no longer be silently skipped — `/start-phase` blocks until it is authored.

### Impact on other phases
- All phases: must pass `/start-phase` before implementation and now satisfy chaos + contract close-checks.
- Phase 07 (Catalog + Lineage): owns the OpenLineage → Marquez → OpenMetadata lineage-ownership ADR (assigned via the Locked Decisions ADR-owner column).
- Phases 04–11: SLO-based validation criteria are marked `[validated at Phase 12]` rather than at their own close.
```
