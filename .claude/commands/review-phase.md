Run the code quality review gate for a phase before it merges.

This command is independent from `/close-phase`. It runs before `/close-phase`. Both are required before a phase ships — this one checks code quality, `/close-phase` checks documentation and contract completeness.

Arguments: phase identifier, e.g. `04-bronze-layer`. If no argument is provided, ask which phase is being reviewed.

## Steps

1. Read `procedures/code-quality.md` in full before proceeding.

2. Read `NN-phase-name/CLAUDE.md` — specifically `## Test Strategy` — to understand what quality checks apply to this specific phase.

3. Run the following checks in order. Report PASS, FAIL, or SKIP (with reason) for each.

### Check 1 — Static analysis
```bash
ruff check NN-phase-name/
mypy NN-phase-name/ --strict
bandit -r NN-phase-name/ -lll
```
- FAIL if any ruff errors (warnings are acceptable)
- FAIL if any mypy errors
- FAIL if any bandit MEDIUM or HIGH findings without inline justification comments
- PASS if only bandit LOW findings remain

### Check 2 — Secret scan
```bash
ggshield secret scan path NN-phase-name/
```
- FAIL on any detected secret
- If ggshield is not installed, flag as MISSING and require manual review of all config files and env references before proceeding

### Check 3 — Unit tests
```bash
pytest NN-phase-name/tests/unit/ -v --tb=short --cov=NN-phase-name --cov-report=term-missing
```
- Report coverage percentage
- FAIL if the coverage threshold defined in the phase `## Test Strategy` is not met
- FAIL if any test fails
- SKIP (with note) if the phase has no unit tests by design (infrastructure, source systems, config-only phases) — must be explicitly stated in `## Test Strategy`

### Check 4 — Fitness functions
```bash
pytest NN-phase-name/tests/contracts/ -v --tb=short
```
- FAIL if any fitness function fails
- FAIL if any fitness function is still a `pytest.mark.xfail` stub — stubs must be implemented before merge
- FAIL if the count of fitness function files is less than the count of entries in the phase `## Fitness Functions` section
- **Robustness (`procedures/validation-standard.md`):** FAIL any fitness function with no refutation — for each test, confirm there is a concrete change that makes it fail (a committed negative-case test, or a documented manual refutation that was run). A test that cannot fail does not ship.

### Check 5 — Phase-specific quality checks + negative cases
Read the phase `## Test Strategy` and `## Validation Gate` and run whatever phase-specific checks are defined:
- dbt test (Gold layer)
- Soda scan (Silver, Gold)
- Latency test (Feature Store, FastAPI)
- Contract validation (Data Contracts phase)
- Any other checks defined in the Test Strategy

**For every criterion, run its negative case, not just its positive assertion** (per the Gate
Robustness Standard): inject the guarded failure and confirm the gate fires — the Soda check rejects
the injected null, the healthcheck goes `unhealthy` under its injected fault, the masking test fails on
a raw NIC. A criterion marked `Negative case: N/A — <reason>` is exempt only if the reason holds.
- FAIL if any criterion's negative case was not executed, or did not produce the expected gate response.

Report each individually (positive result + negative-case result).

### Check 6 — CodeRabbit review status
- Check if a PR exists for this phase branch
- If yes: confirm CodeRabbit has reviewed it and all non-dismissed comments are resolved
- If no PR yet: note that CodeRabbit review is pending — this check cannot be completed until a PR is open
- Do NOT skip this check — CodeRabbit review is required before merge

### Check 7 — No hardcoded secrets or config
Scan all files in the phase directory for:
- Hardcoded connection strings, passwords, tokens, API keys
- References to `localhost` or `127.0.0.1` that should use Docker service names
- Any `.env` file committed (not `.env.example`)

FAIL on any finding.

## Output Format

Report as a table:

| Check | Status | Findings |
|---|---|---|
| Static analysis | PASS/FAIL/SKIP | |
| Secret scan | PASS/FAIL/MISSING | |
| Unit tests | PASS/FAIL/SKIP | Coverage: X% |
| Fitness functions | PASS/FAIL | N passed, N failed, N stubs, N non-refutable |
| Phase-specific checks + negative cases | PASS/FAIL/SKIP | List each: positive + negative-case result |
| CodeRabbit review | PASS/PENDING/FAIL | |
| No hardcoded config | PASS/FAIL | |

**If all checks PASS:** state explicitly "Phase NN is clear for `/close-phase`."

**If any check FAILS:** list every failing item with the exact fix required. Do not proceed to `/close-phase` until all failures are resolved.

## Rules
- This command does not modify any files — it only reads, runs checks, and reports
- Do not mark a check as PASS without actually running it
- SKIP is only valid when the phase Test Strategy explicitly states a check does not apply and gives a reason
- A phase with zero unit tests and no explicit justification in Test Strategy is a FAIL on Check 3, not a SKIP
