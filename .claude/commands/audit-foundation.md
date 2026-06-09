Run a read-only consistency sweep of the project foundation and report whether it is airtight.

The foundation is the contract for how every phase is built — commands, procedures, ledgers,
naming, roadmap. This command verifies it has no internal contradictions, no undefined references,
and no stated-but-unenforced gate. It changes nothing.

Arguments: none. (Optionally a single invariant ID, e.g. `I3`, to run just that check.)

## Steps

1. Read `procedures/foundation-audit.md` in full — it defines invariants I1–I9.

2. Run each invariant as a read-only check against the current repository:
   - **I1** — cross-check `procedures/README.md` against the actual files in `procedures/`, and
     against every procedure reference in command files and phase templates.
   - **I2** — cross-check `CONTRACTS.md` against the Phase Index and each closed phase's
     `## Interface Contract`. (Vacuous pass if no phase is ✅ yet — state that.)
   - **I3** — cross-check the six-angle coverage matrix in `chaos/CLAUDE.md` against
     `chaos/scenarios/` and `chaos/stress-tests/`, and verify each scenario's availability phase
     matches its real dependency.
   - **I4** — compare the scenario `Category` enum and ST-NNN `Category` enum in `chaos-testing.md`.
   - **I5** — compare README Domain Model scale to `seed-data.md` S01 baseline.
   - **I6** — for each gate-like rule in the procedures, confirm a command enforces it (map to the
     specific check: `/close-phase` Check 6/8/9, `/start-phase`, `/review-phase` Check 4).
   - **I7** — grep the key facts (6 SLOs, 7 metrics, 8 features, confidence bands, version pins)
     across CLAUDE.md, README, code-quality.md, fitness-function.md and confirm they agree.
   - **I8** — confirm every file/dir reference resolves to something existing, a known forward
     phase artifact, or a `Deferred → Phase NN` procedure.
   - **I9** — confirm every Locked Global Decision row has an ADR owner.
   - **I10** — sweep every authored phase CLAUDE.md: each Validation Gate + Fitness Function criterion
     is behavioral and has a negative case (or `N/A — reason`); confirm `validation-standard.md` is
     referenced by the template and enforced at `/start-phase`, `/review-phase`, `/close-phase`.
     (Vacuous pass if no phase CLAUDE.md exists yet.)

3. Report using the output table from `procedures/foundation-audit.md`.

## Rules
- Read-only. This command must not edit any file, including the plan or any ledger.
- Do not mark an invariant PASS without actually performing the cross-check.
- A vacuous pass (nothing to reconcile yet) is reported as PASS with the note "no closed phases yet"
  — it is never skipped or left blank.
- If any invariant FAILS, list the exact file and the one-line fix. Do not apply the fix from this
  command — surface it so it can be fixed in an explicit, separate edit.
