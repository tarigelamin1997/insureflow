Run the completion checklist for the current phase before marking it done.

Arguments: phase identifier, e.g. `03-cdc-ingestion`. If no argument is provided, ask which phase is being closed.

## Checklist

Work through every item. Report PASS, FAIL, or MISSING for each. Do not mark a phase complete if any item is FAIL or MISSING.

### 1 — CLAUDE.md completeness
Read `NN-phase-name/CLAUDE.md` and verify:
- [ ] All sections from the template in `procedures/phase-claude-md.md` are present and filled (no `[TO BE FILLED]` placeholders remaining)
- [ ] Interface Contract has at least one entry in Produces and Consumes (or explicitly states "Produces: nothing" / "Consumes: nothing" with justification)
- [ ] SLA values are concrete numbers, not TBD
- [ ] Every Fitness Function entry maps to an existing file in `tests/contracts/`
- [ ] Validation Gate commands are listed

### 2 — ADRs
- [ ] Every decision listed in `## Decisions` in the phase CLAUDE.md has a corresponding file in `decisions/`
- [ ] No ADR file has Status: `Proposed` (all must be `Accepted` or `Superseded`)

### 3 — Fitness functions
- [ ] Every file listed under `## Fitness Functions` in the phase CLAUDE.md exists in `tests/contracts/`
- [ ] Run the fitness function tests and confirm they pass: `pytest NN-phase-name/tests/contracts/ -v`
- [ ] Report which tests passed and which failed

### 4 — Validation gate (positive + negative)
- [ ] Run every command listed under `## Validation Gate` in the phase CLAUDE.md
- [ ] Confirm each command exits with the expected output or exit code
- [ ] **Run each criterion's negative case too** (per `procedures/validation-standard.md`): inject the guarded failure and confirm the gate fires (rejects / goes unhealthy / alerts / quarantines). A criterion marked `Negative case: N/A — <reason>` is exempt only if the reason holds.
- [ ] FAIL if any negative case was not run, or did not produce the expected gate response — a gate proven only on the happy path is not proven
- [ ] Report both results per criterion

### 5 — README completeness
- [ ] `NN-phase-name/README.md` "How to Run" section is filled
- [ ] `NN-phase-name/README.md` "Validation" section is filled
- [ ] No placeholder text remaining

### 6 — Open errors check
- [ ] List all files in `NN-phase-name/errors/` **and** root `errors/`
- [ ] Read the Status field of every error file
- [ ] FAIL if any file in this phase has `Status: Open` — a phase with unresolved errors cannot be closed
- [ ] FAIL if any **root** `errors/` file has `Status: Open` — cross-phase blockers prevent any close
- [ ] Chaos-discovered errors (`Source: chaos-discovered`) are caught here too — they live in the owning phase's `errors/`, not a separate directory
- [ ] If all errors are resolved or no error files exist: PASS

### 7 — Root CLAUDE.md phase index
- [ ] Update the phase status in root `CLAUDE.md` Phase Index table from `🚧 In progress` to `✅ Complete`

### 7b — Merge the phase PR
- [ ] Confirm the phase's pull request is green: CI passing, and all CodeRabbit comments resolved or dismissed with a reason (this overlaps `/review-phase` Check 6 — re-verify nothing reopened)
- [ ] Merge the PR into `main` (squash or merge commit naming the phase). The merge is the durable "phase complete" marker. Do NOT push the phase commits directly to `main` — see `procedures/code-quality.md` Branching & Pull Request Workflow

### 8 — Upstream contract check
The contract check is **upstream-oriented**: in a sequential build the downstream consumer does
not exist yet at close time, so the only contract that can be verified is this phase's dependency
on its already-closed producers.
- [ ] Read this phase's `## Interface Contract` → `## Consumes` block
- [ ] For every entry, find the matching `Produces` row in root `CONTRACTS.md` (from an already-closed upstream phase) — verify the exact name matches (topic, table, bucket/prefix, endpoint, model, metric)
- [ ] FAIL on any `Consumes` entry that no upstream `Produces` row provides — that is an integration contract violation (a naming mismatch or a missing upstream output)
- [ ] If this phase consumes nothing (e.g. Phase 01/02), state "Consumes: nothing" and PASS
- [ ] After all checks pass: append this phase's `## Produces` entries as its row in `CONTRACTS.md`, set its status to ✅, and record which downstream phase(s) will consume them

### 9 — Chaos scenarios passed
- [ ] Read the phase CLAUDE.md `## Chaos Scenarios` section
- [ ] For each scenario listed, confirm a corresponding `ST-NNN` document exists in `chaos/stress-tests/` with `Status: Clean pass` (or `Gap found — fixed`, with the resulting ERR-NNN resolved)
- [ ] FAIL if any listed scenario has no ST-NNN, or its ST-NNN status is `Gap found — open`
- [ ] If the section explicitly states "None — this phase has no chaos scenarios" with a reason: PASS
- [ ] Update the Six-Angle Coverage Matrix in `chaos/CLAUDE.md` with the ST-NNN reference for any angle this phase's scenarios satisfy

### 10 — Documentation reflection (cross-surface backstop)
"Done" = reflected on every surface where this phase is visible, not just code merged. This is the
backstop catching any surface no check above owns — the gap that left the root README phase-table
stale after Phase 01. Checks 5/7/8/9 cover individual surfaces; this asserts the **full set** is
consistent, and explicitly owns the surfaces none of them do (root README, the registry, the
repo-structure tree, the Status line).
- [ ] Enumerate every surface this phase's change touches. At minimum: root `README.md` (phase
      table, Getting Started, Project Structure), root `CLAUDE.md` (Phase Index, Status line, any
      naming/decision table touched), `CONTRACTS.md`, `procedures/README.md` (registry status),
      `chaos/CLAUDE.md` (matrix), and the phase's own README/CLAUDE.md.
- [ ] Confirm each shows the current post-phase state: status marks flipped, new outputs documented,
      authored procedures moved `Deferred → Written`, new files present in the repo-structure tree.
- [ ] **Behavioral:** a reader opening any one surface cold sees the phase as it actually is — none
      still shows it not-started, no produced output left undocumented.
- [ ] **Negative case:** leave one surface deliberately stale (e.g. the root README phase row still
      ⬜) and confirm this check catches it before reporting PASS. `Negative case: N/A` is NOT
      permitted here — staleness is always injectable, so the check must prove it fires.
- [ ] FAIL if any surface is stale or any change is unreflected.

## Output Format

Report as a table:

| Check | Status | Notes |
|---|---|---|
| CLAUDE.md complete | PASS/FAIL/MISSING | |
| ADRs complete | PASS/FAIL/MISSING | |
| Fitness functions exist | PASS/FAIL/MISSING | |
| Fitness functions pass | PASS/FAIL/MISSING | |
| Validation gate passes | PASS/FAIL/MISSING | |
| README complete | PASS/FAIL/MISSING | |
| Open errors check | PASS/FAIL/MISSING | N open (phase), N open (root), N resolved |
| Phase index updated | PASS/FAIL/MISSING | |
| Upstream contracts aligned | PASS/FAIL/MISSING | CONTRACTS.md row appended |
| Chaos scenarios passed | PASS/FAIL/MISSING | N scenarios, N ST-NNN clean |
| Docs reflected (all surfaces) | PASS/FAIL/MISSING | surfaces checked; stale-case fired |

If any row is FAIL or MISSING, list exactly what needs to be fixed before the phase can be closed.
