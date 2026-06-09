# Master Execution Plan — Foundation Airtightness

> **Status: Executed (2026-06-09).** All 9 workstreams shipped. The permanent decision record is
> `decisions/adr-000-foundation-airtightness.md`; this file preserves the full execution plan as a
> portfolio artifact. Two deviations from the literal plan: (1) the chaos scenario `Category` enum
> was extended by the two genuinely-missing categories (Time-based Degradation, Cascading Failure)
> rather than mechanically copying all six ST-NNN angles; (2) one extra file, `resolve-error.md`,
> was edited to drop a residual `chaos/errors/` reference caught by `/audit-foundation`.
>
> **Follow-on:** the one residual boundary this plan identified — that gates enforce criteria *exist
> and run* but not that they are *strong* — is closed by ADR-001 / the Gate Robustness Standard. See
> [the validation-robustness plan](2026-06-09-validation-robustness-standard.md).

## Context

InsureFlow is a blueprint: the full mainframe (commands, procedures, naming, phase
roadmap) is being laid down before any phase is implemented. A two-pass audit of the
whole project found the *architecture* and *cross-doc facts* are consistent, but the
*foundation methodology* has gaps that would cause friction the moment Phase 01 starts.

The root diagnosis — every finding traces to one of three causes:

1. **Documentation is gated, behavior is not.** Every ADR, error, and CLAUDE.md section
   has an exit gate. Chaos execution and cross-phase contract validation are *described*
   as gates but no command enforces them.
2. **No single source of truth for cross-phase concerns.** Procedure status, interface
   contracts, and chaos coverage live as scattered prose, so they drift.
3. **Two exit gates, zero entry gate.** `/review-phase` and `/close-phase` guard the end;
   nothing guards the start, so "CLAUDE.md before code", "prereqs met", and "author the
   phase's procedures" are policy without enforcement.

Goal: make the foundation 100% self-consistent and self-enforcing **before** Phase 01.
This is documentation/tooling only — **zero architectural change**, the locked phase
order and tech decisions are preserved.

**User decisions (locked for this plan):**
- Domain scale is canonical **50K/80K/25K/200K**; seed-data.md reconciles to it.
- Observability stays Phase 12 → use a **retroactive-validation note** for SLO criteria.
- Procedure registry lives in a **dedicated `procedures/README.md`**.
- Chaos-discovered errors live in the **owning phase's `errors/`**; drop `chaos/errors/`.

## Design Principles
1. One ledger per cross-phase concern (procedures, contracts, chaos coverage) — a file, not prose.
2. Every gate named in a procedure must be enforced by a command, or it is not a gate.
3. Symmetry: one entry gate (`/start-phase`) + two exit gates (`/review-phase`, `/close-phase`).
4. Self-consistency: this change set gets its own ADR; airtightness becomes a repeatable audit.
5. Preserve locked phase order and architecture — wiring and docs only.

---

## Findings Closed by This Plan

| ID | Severity | Finding | Workstream |
|---|---|---|---|
| B | MED | Chaos-error location contradiction (chaos/errors vs phase errors); dir in no tree | WS3 |
| C | MED | scenario-13 marked Phase 05 but needs Phase-12 SLO alerting; false "SLO active@05" | WS3 |
| D | LOW-MED | Seed baseline 1K vs domain 50K, no reconciliation | WS4 |
| E | LOW | Scenario Category enum (4) vs ST-NNN enum (6) mismatch | WS3 |
| G | LOW | OpenMetadata vs Marquez/OpenLineage lineage ownership unstated | WS7 |
| M1 | MED | Chaos declared a close-gate but `/close-phase` never checks it | WS3 |
| M2 | MED | `/close-phase` Check 8 contract check points downstream (inert in sequential build) | WS2 |
| M3 | MED | No lifecycle step authors a phase's required procedure | WS1+WS5 |
| M4 | LOW-MED | Observability-last makes SLO validation retroactive, unstated | WS6 |
| M5 | LOW | "CLAUDE.md before code" + "review before close" + prereq check unenforced | WS5 |
| P | LOW | Procedure tree omits 3 existing files; no Written/Deferred status marker | WS1 |
| X | LOW | Locked Global Decisions asserted with no assigned ADR owner | WS0 |

---

## Workstreams

### WS0 — Anchor the change set (self-consistency)
- New `decisions/` at repo root = home for project-level ADRs not owned by a single phase.
- New `decisions/adr-000-foundation-airtightness.md` (Status: Accepted) — the meta-decision:
  why we wire gates + ledgers. Makes this effort comply with the repo's own ADR standard.
- In `CLAUDE.md` Locked Global Decisions table, add an **"ADR owner"** column mapping each
  decision (Iceberg, OpenMetadata, Soda, Kafka KRaft, Qdrant, LLaMA, sklearn…) to the
  phase or root location that will hold its full ADR. ADRs written when that phase arrives;
  ownership assigned now so none are orphaned.

### WS1 — Procedure registry (closes P, M3-part)
- New `procedures/README.md` = the registry: each procedure → **Status** (`Written` /
  `Deferred → Phase NN`) → **consumed-by** phases. Authoritative list.
- Add the 3 existing-but-unlisted procedures: `code-quality.md`, `error-logging.md`,
  `chaos-testing.md`.
- Mark deferred ones with their owning phase: `docker-healthcheck`→01, `kafka-connector`→03,
  `iceberg-table`/`spark-job`→04, `soda-check`→05, `dbt-model`→06, `airflow-dag-factory`→03.
- In `CLAUDE.md`, replace the comment-annotated procedures tree with a pointer to the registry.
- Rule established here, enforced in WS5: a `Deferred → Phase NN` procedure **must be authored
  as the first implementation step of Phase NN**.

### WS2 — Contract ledger + fix the contract gate (closes M2)
- New root `CONTRACTS.md` = matrix of every phase's **Produces → consumed-by**. Phase
  Interface Contracts stay the detail; this is the rollup the gate checks.
- Rewrite `close-phase.md` **Check 8** from downstream (inert — consumer doesn't exist yet)
  to **upstream**: verify this phase's `Consumes` exactly matches the `Produces` of
  already-closed upstream phases (via CONTRACTS.md + their CLAUDE.md). On close, append this
  phase's `Produces` to CONTRACTS.md.
- Redefine the "after every second phase" global standard in `CLAUDE.md` as: reconcile
  CONTRACTS.md across the last two adjacent closed phases.

### WS3 — Chaos: coverage matrix + wire the gate + fix contradictions (closes B, C, E, M1)
- **Coverage matrix** in `chaos/CLAUDE.md`: six angles × satisfying scenario × required-by
  phase × ST-NNN status. Makes "every angle covered before Phase 12" verifiable.
- **Gate (M1):** add `close-phase.md` **Check 9** — every scenario in the phase's
  `## Chaos Scenarios` has a *passing* ST-NNN in `chaos/stress-tests/`; FAIL otherwise.
- **Fix C:** re-tag `scenario-13` (time-based degradation) availability to **Phase 12**
  (it needs SLO alerting); correct the false "SLO alerts active" at Phase 05 cell.
  Re-verify 14→Phase 06, 15→Phase 08 still hold (they do).
- **Fix E:** extend the scenario-file `Category` enum in `chaos-testing.md` to cover the two
  angles the injection-type categories miss (Time-based Degradation, Cascading Failure).
- **Fix B:** chaos-discovered errors → owning phase `errors/` (`Source: chaos-discovered`,
  back-ref ST-NNN). **Drop `chaos/errors/`** everywhere. Align `error-logging.md` +
  `new-error.md` to `chaos-testing.md`. Broaden `close-phase.md` **Check 6** to also flag
  open **root** `errors/` (cross-phase blockers).

### WS4 — Reconcile seed scale to 50K/80K/25K/200K (closes D)
- In `procedures/seed-data.md`, set **S01 baseline** to domain scale: PMS 50K policyholders /
  80K policies, CMS 25K claims, PFS 200K transactions.
- Classify injections: **percentage-based auto-scale** (S04 40%, S05 15%, S06 25%) vs
  **fixed-absolute deliberate edge events** (S02 50, S03 30, S07 20, S08 5×500, S09 100,
  S10 50, S11 30, S12 20) — keep absolutes as documented rare-event injections.
- Add a **"Scale Profiles"** subsection: `default` = full domain scale; `--scale` multiplier;
  a `ci` fast profile for pipeline speed — with the note that every scenario's pass assertion
  holds at any scale.
- Light edit `README.md` Domain Model so README and seed-data.md state identical numbers.

### WS5 — Entry gate: new `/start-phase` command (closes M3, M5)
- New `.claude/commands/start-phase.md`, run after `/new-phase` scaffolds + CLAUDE.md is
  filled, **before any code**. It verifies:
  - All upstream phases in `## Prerequisites` are ✅ in the phase index.
  - Phase CLAUDE.md passes the "Minimum Viable" check (no `[TO BE FILLED]`).
  - Every procedure in the phase's Procedures table exists; any `Deferred → this phase`
    must be authored now (blocks until written) — enforces WS1's rule.
  - Fitness-function stubs exist (reuses `/fitness-check` logic).
  - Sets phase index status ⬜ → **🚧 in-progress**.
- `CLAUDE.md`: add `/start-phase` to the command table; add 🚧 to the phase-index legend.
- `new-phase.md`: add a hand-off line pointing to `/start-phase` as the next step.

### WS6 — Roadmap honesty: SLO deferral note (closes M4)
- `CLAUDE.md`: add a roadmap note — SLO-dependent validations for phases 04–11 are validated
  retroactively at Phase 12; this is also why `scenario-13` is Phase 12.
- `procedures/phase-claude-md.md`: one line in the Validation Gate guidance — SLO criteria for
  pre-12 phases are marked `[validated at Phase 12]`.

### WS7 — Lineage ownership clarification (closes G)
- One canonical sentence in `CLAUDE.md` (architecture) + `README.md` (governance): pipelines
  emit **OpenLineage** events → **Marquez** collects → **OpenMetadata** ingests for the
  unified catalog/lineage/contract/quality surface. Full justification = ADR assigned to
  Phase 07 in the WS0 ownership table.

### WS8 — Capstone: make airtightness repeatable
- New `procedures/foundation-audit.md` + `.claude/commands/audit-foundation.md`: a read-only
  checklist that re-runs this exact consistency sweep on demand — registry vs disk,
  CONTRACTS.md vs phase Interface Contracts, chaos matrix vs scenarios/ST-NNN, enum alignment,
  scale consistency, command-gate wiring. Turns the one-time audit into a standing gate (run
  before each `/close-phase` and after any foundation edit).
- `CLAUDE.md`: add `/audit-foundation` to the command table.

---

## File Inventory (as executed)

**New (6 files + 1 dir):**
- `decisions/` (dir) + `decisions/adr-000-foundation-airtightness.md`
- `CONTRACTS.md`
- `procedures/README.md` (procedure registry)
- `procedures/foundation-audit.md`
- `.claude/commands/start-phase.md`
- `.claude/commands/audit-foundation.md`

**Edited (11):**
- `CLAUDE.md` — registry pointer, CONTRACTS reference, locked-decisions ADR-owner column,
  command table (+start-phase, +audit-foundation), 🚧 legend, SLO roadmap note, lineage line
- `README.md` — seed-scale reconciliation, lineage line
- `procedures/seed-data.md` — baseline 50K…, scale profiles, injection classification
- `procedures/chaos-testing.md` — Category enum extended
- `procedures/error-logging.md` — chaos error → owning phase errors/
- `procedures/phase-claude-md.md` — SLO-deferral note in Validation Gate
- `chaos/CLAUDE.md` — coverage matrix, scenario-13 re-tag, drop chaos/errors/
- `.claude/commands/new-error.md` — chaos error location
- `.claude/commands/resolve-error.md` — chaos error location (residual caught by /audit-foundation)
- `.claude/commands/close-phase.md` — Check 6 broaden, Check 8 upstream rewrite, Check 9 chaos
- `.claude/commands/new-phase.md` — hand-off to /start-phase

---

## Execution Order (dependency-aware)
1. **WS0** — anchor + decisions home (everything references it).
2. **WS1** — procedure registry (unblocks /start-phase + audit).
3. **WS4, WS7** — flat content fixes (seed scale, lineage), independent, batchable.
4. **WS3** — chaos (matrix, gate, error-location, enum, scenario-13), self-contained.
5. **WS2** — contract ledger + Check 8 rewrite.
6. **WS5** — /start-phase (depends on WS1 registry + WS2 contracts).
7. **WS6** — roadmap SLO note.
8. **WS8** — audit command; then run it to prove green.

---

## Verification (how we prove airtight)
- Run `/audit-foundation` → **zero findings** (ran on completion: 9/9 invariants PASS).
- Every gate named in any procedure is enforced by a command: chaos (Check 9), contracts
  (Check 8 upstream), prereqs + procedure-authoring (/start-phase), errors (Check 6).
- Three ledgers exist and reconcile with phase files: `procedures/README.md`, `CONTRACTS.md`,
  chaos coverage matrix.
- Every Locked Global Decision has an assigned ADR owner.
- No file references a path without a defined status (exists, or `Deferred → Phase NN`).
- Re-check original findings B/C/D/E/G + M1–M5 + P + X — all closed.
- Manual read-through of the full lifecycle: `/new-phase` → `/start-phase` → implement →
  `/review-phase` → `/run-chaos` → `/close-phase` has no undefined step and no unenforced gate.
