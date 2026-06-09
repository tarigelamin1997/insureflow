Execute a chaos scenario against the running InsureFlow stack and validate the platform response.

Arguments: scenario name, e.g. `scenario-06-kafka-partition-loss`. If no argument is provided, list all available scenarios from `chaos/scenarios/` and ask which one to run.

## Before Running

1. Read `procedures/chaos-testing.md` in full.
2. Read `chaos/CLAUDE.md` — confirm the scenario is available for the current phase completion state.
3. Read `chaos/scenarios/{scenario-name}.md` in full — understand every step before executing anything.

## Steps

### Step 1 — Prerequisite check
- Confirm all phases listed in the scenario `## Prerequisites` are closed (status ✅ in root CLAUDE.md phase index)
- Confirm all required Docker services are healthy: `docker compose ps`
- If any prerequisite fails: stop. Report what is missing. Do not proceed.

### Step 2 — Baseline state
- Run every command listed in the scenario `## Baseline State` section
- Confirm each returns the expected result
- If baseline is not clean (e.g., existing alerts already firing, Soda checks already failing): stop. The stack must be healthy before injecting chaos.

### Step 3 — Inject
- Run the exact command or script from the scenario `## Injection` section
- Log the injection timestamp
- Do not modify anything beyond what the scenario specifies

### Step 4 — Observe
Work through the scenario `## Observation Checklist` in order:
- For each item: run the verification command, record the actual result, compare to expected
- Wait the documented time window if the response is not immediate
- Record all observations with timestamps

### Step 5 — Evaluate
Compare observed results against `## Pass Criteria` and `## Fail Criteria`:
- Every pass criterion must be verified as true
- No fail criterion must be true
- Report PASS or FAIL for each criterion individually

### Step 6 — Cleanup
- Run the cleanup script or commands from `## Cleanup` regardless of pass/fail outcome
- Run every command in `## Verify recovery`
- Confirm the stack returns to the baseline state established in Step 2
- Do NOT close the scenario until cleanup is verified complete

### Step 7 — Report

Output:

```
Chaos Scenario: {name}
Injected at: {timestamp}
Cleanup complete at: {timestamp}

Observation Results:
  [observation 1]: expected X → observed Y → MATCH / MISMATCH
  [observation 2]: expected X → observed Y → MATCH / MISMATCH
  ...

Pass Criteria:
  [criterion 1]: TRUE / FALSE
  [criterion 2]: TRUE / FALSE
  ...

Outcome: PASS / FAIL

Findings:
  [anything unexpected observed during the scenario, even if the outcome is PASS]
```

## Rules
- Never skip cleanup. A scenario that ends with the stack in a broken state is worse than not running the scenario.
- Never modify the scenario `.md` file to match what was observed — if the platform behaved differently than expected, that is a finding, not a reason to update the expected outcome.
- If the inject script itself fails (non-zero exit), stop immediately, run cleanup, report the script failure.
- Do not run more than one scenario concurrently.
- A FAIL outcome means the phase that owns the affected behaviour must be reopened and the defect fixed before `/close-phase` can complete.
