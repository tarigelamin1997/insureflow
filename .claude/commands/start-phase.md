Gate a phase from scaffolded to ready-for-implementation. The entry gate.

This is the front gate of the phase lifecycle. It runs **after** `/new-phase` has scaffolded the
directory and the phase CLAUDE.md has been filled, and **before** any implementation file is
written. It is the mirror of `/close-phase`: that one guards the exit, this one guards the entry.

Arguments: phase identifier, e.g. `04-bronze-layer`. If no argument is provided, ask which phase
is being started.

## Why this gate exists

Three rules were previously policy without enforcement: "CLAUDE.md before code", "prerequisites
must be met", and "author this phase's deferred procedures first". This command enforces all three,
so a phase cannot begin implementation in an unready state.

## Steps

Run every check in order. Report PASS or FAIL for each. Do NOT proceed to implementation if any
check is FAIL — fix it first.

### Check 1 — Prerequisites are closed
- [ ] Read the phase CLAUDE.md `## Prerequisites` section
- [ ] For every upstream phase it depends on, confirm status is ✅ in the root `CLAUDE.md` Phase Index
- [ ] FAIL if any prerequisite phase is `⬜ Not started` or `🚧 In progress`
- [ ] Confirm any required-healthy services named in Prerequisites are reachable (if the stack is up)

### Check 2 — CLAUDE.md is implementation-ready
- [ ] Read the phase CLAUDE.md against the "Minimum Viable Phase CLAUDE.md" list in `procedures/phase-claude-md.md`
- [ ] FAIL if any `[TO BE FILLED]` placeholder remains
- [ ] FAIL if Interface Contract (Produces + Consumes), at least one Fitness Function, at least one Validation Gate command, Blast Radius, Test Strategy, or Chaos Scenarios section is empty

### Check 3 — Required procedures exist (author deferred ones now)
- [ ] Read the phase CLAUDE.md `## Procedures` table
- [ ] For each procedure listed, check `procedures/README.md` (the registry) for its status
- [ ] For any procedure marked `Deferred → this phase`: it MUST be authored now, before any code. This is its owning phase.
  - Write the procedure file following the repository's procedure standard
  - Update `procedures/README.md`: change its Status to `Written`, remove the owning-phase tag
- [ ] FAIL if any procedure this phase needs is still missing after this step

### Check 4 — Fitness-function stubs exist
- [ ] Run the `/fitness-check` logic for this phase: every property in `## Fitness Functions` has a file in `tests/contracts/` (an `xfail` stub is acceptable at start — it must be implemented before `/review-phase`)
- [ ] FAIL if a declared fitness function has no file at all

### Check 5 — Gate robustness (the criteria themselves are strong)
Read `procedures/validation-standard.md`, then adversarially review every criterion in the phase
CLAUDE.md `## Validation Gate` and `## Fitness Functions`:
- [ ] **Behavioral** — FAIL any criterion that only checks something exists, runs, or is reachable. It must assert the component does its job through its real interface. ("container up" → FAIL; "INSERT then SELECT returns the row" → PASS)
- [ ] **Negative case** — FAIL any criterion that does not state the failure it catches and the gate's response, OR an explicit `Negative case: N/A — <reason>`. A missing negative case with no justification is a hard FAIL.
- [ ] For each criterion, ask "what change would make this fire?" — if the answer is "nothing", it is no gate. FAIL.
- [ ] This is the highest-leverage check: a weak criterion caught here is fixed before it shapes any code.

### Check 6 — Mark in progress
- [ ] In the root `CLAUDE.md` Phase Index, set this phase's status from `⬜ Not started` to `🚧 In progress`

## Output Format

| Check | Status | Notes |
|---|---|---|
| Prerequisites closed | PASS/FAIL | which upstream phases |
| CLAUDE.md ready | PASS/FAIL | placeholders remaining |
| Required procedures exist | PASS/FAIL | deferred ones authored: list |
| Fitness stubs exist | PASS/FAIL | N stubs |
| Gate robustness | PASS/FAIL | weak/negative-case-missing criteria: list |
| Marked in progress | DONE | |

**If all checks PASS:** state explicitly "Phase NN is ready for implementation."
**If any check FAILS:** list every failing item with the exact fix required. Do not write any
implementation file until all failures are resolved.

## Rules
- This command may author **procedure files** (Check 3) and update the **phase index** (Check 6) and the **procedure registry** — nothing else. It writes no implementation code.
- A `Deferred → this phase` procedure that is not authored is a hard FAIL — it cannot be skipped.
- Do not mark a check PASS without actually running it.
