# Procedure: Foundation Audit

## Guiding Principle

The foundation (commands, procedures, ledgers, naming, roadmap) is the contract for how every
phase is built. It must stay 100% self-consistent. This procedure is the repeatable, read-only
sweep that proves it — turning a one-time audit into a standing gate. Run it before any
`/close-phase`, and after any edit to a command, procedure, ledger, or root CLAUDE.md.

A blueprint is "airtight" when every reference resolves to either something that exists or
something explicitly marked `Deferred → Phase NN`, every stated gate is enforced by a command,
and every cross-phase fact agrees across all documents.

This procedure changes nothing. It only reads, checks, and reports.

---

## Invariants

Each invariant is a binary check. Report PASS or FAIL with the specific offending file/line.

### I1 — Procedure registry reconciles with disk
- Every procedure marked `Written` in `procedures/README.md` exists as a file in `procedures/`.
- Every procedure file in `procedures/` (except this one and `README.md`) appears in the registry.
- Every procedure referenced anywhere (phase templates, command files, CLAUDE.md) is either
  `Written` or `Deferred → Phase NN` in the registry — never referenced as existing when missing.

### I2 — Contract ledger reconciles with phase contracts
- Every phase with status ✅ in the CLAUDE.md Phase Index has a `Produces` row in `CONTRACTS.md`.
- Every `Consumes` entry in a closed phase's Interface Contract resolves to a `Produces` row of an
  upstream closed phase (exact name match, using Global Naming Conventions).
- No name in `CONTRACTS.md` conflicts with the Global Naming Conventions table in CLAUDE.md.

### I3 — Chaos coverage reconciles
- Every one of the six angles has at least one satisfying scenario in the coverage matrix
  (`chaos/CLAUDE.md`).
- Each scenario's "runnable from" phase is consistent with its actual dependency (e.g. a scenario
  whose pass criterion needs SLO alerting is gated at Phase 12, not earlier).
- Every scenario listed in a ✅ phase's `## Chaos Scenarios` has a `Status: Clean pass` (or
  `Gap found — fixed`) ST-NNN in `chaos/stress-tests/`.

### I4 — Enum alignment
- The scenario-file `Category` enum (`chaos-testing.md`) can classify every scenario, including
  time-based-degradation and cascading-failure scenarios.
- The ST-NNN `Category` enum lists all six angles.

### I5 — Scale consistency
- The README Domain Model scale (policyholders / policies / claims / transactions) equals the
  `seed-data.md` S01 baseline row volumes.

### I6 — Every stated gate is command-enforced
For each "must"/"gate"/"before X" rule in a procedure, a command actually enforces it:
- Chaos scenarios run before close → `/close-phase` Check 9.
- Upstream contracts verified → `/close-phase` Check 8.
- Prerequisites met + deferred procedures authored + CLAUDE.md filled before code → `/start-phase`.
- Open errors (phase + root) block close → `/close-phase` Check 6.
- No `xfail` fitness stub ships → `/review-phase` Check 4.
- Every affected documentation surface reflected at close → `/close-phase` Check 10.
FAIL if a rule is stated but no command checks it.

### I7 — Cross-document fact consistency
These numbers/values must be identical everywhere they appear (CLAUDE.md, README, code-quality.md,
fitness-function.md): 6 SLOs · 7 MetricFlow metrics · 8 ML features · confidence bands
(High > 0.85, Medium 0.60–0.85, Low < 0.60) · version pins (Kafka 4.0, Debezium 2.7, dbt 1.8,
Airflow 2.10).

### I8 — No undefined references
- Every file/directory referenced in CLAUDE.md, README, and command files either exists, or is a
  known forward reference (a phase artifact built later) consistent with the blueprint, or a
  `Deferred → Phase NN` procedure. No reference is silently broken.

### I9 — Decision ownership
- Every row in the Locked Global Decisions table has an ADR-owner assignment.

### I10 — Gate robustness
For every authored phase CLAUDE.md, sweep the `## Validation Gate` and `## Fitness Functions`:
- Every criterion is **behavioral** — none checks only existence/liveness/reachability.
- Every criterion has a **negative case** (the guarded failure + expected gate response) or an
  explicit `Negative case: N/A — <reason>`. A missing negative case with no justification is a FAIL.
- The standard itself (`procedures/validation-standard.md`) is referenced by the template
  (`phase-claude-md.md`) and enforced by `/start-phase`, `/review-phase`, `/close-phase` — confirm
  the wiring is intact (the four-layer chain has no broken link).
- Vacuous pass if no phase CLAUDE.md is authored yet — state "no phase CLAUDE.md authored yet".

### I11 — Documentation reflection
For every phase marked ✅ in the Phase Index, every surface that displays its state or outputs is
current — no surface contradicts the phase's actual closed state:
- Root `README.md` (phase table status, Getting Started, Project Structure), root `CLAUDE.md`
  (Phase Index, Status line, naming/decision tables), `CONTRACTS.md`, `procedures/README.md`
  registry, `chaos/CLAUDE.md` matrix, and the phase's own README/CLAUDE.md all show the phase as
  closed and its outputs as documented.
- FAIL on any surface still showing a closed phase as not-started, or any produced output absent
  from the surfaces that should list it (e.g. a `Produces` output with no `CONTRACTS.md` row).
- Confirm the four-layer wiring is intact: defined in CLAUDE.md Global Build Standards, carried by
  the template (`phase-claude-md.md` → Definition of Done), enforced at `/close-phase` Check 10.
- Vacuous pass if no phase is ✅ yet — state "no closed phases yet".

Report as a table, one row per invariant:

| Invariant | Status | Offending item (if FAIL) |
|---|---|---|
| I1 Procedure registry ↔ disk | PASS/FAIL | |
| I2 Contract ledger ↔ phases | PASS/FAIL | |
| I3 Chaos coverage | PASS/FAIL | |
| I4 Enum alignment | PASS/FAIL | |
| I5 Scale consistency | PASS/FAIL | |
| I6 Gates command-enforced | PASS/FAIL | |
| I7 Cross-doc facts | PASS/FAIL | |
| I8 No undefined references | PASS/FAIL | |
| I9 Decision ownership | PASS/FAIL | |
| I10 Gate robustness | PASS/FAIL | weak/negative-case-missing criteria |
| I11 Documentation reflection | PASS/FAIL | stale surface for a closed phase |

**Green** = all PASS. State "Foundation is airtight." Any FAIL lists the exact file and fix.

## Notes
- This is read-only. If it finds a gap, fix it in a separate, explicit edit — never silently.
- Many checks have nothing to reconcile until phases start closing (I2, I3 ST-NNN column). At
  blueprint stage they pass vacuously — record that explicitly ("no closed phases yet"), do not
  skip the row.
