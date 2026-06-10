# Procedure: Code Quality

## Guiding Principle

Code quality is enforced at three independent moments: before code enters git (pre-commit), on every push (CI), and before a phase merges (review gate). Each moment catches different failure modes. Missing any one of them means a class of issues reaches production.

Quality is not a single coverage number. Each phase has a different code surface — a PySpark job, a dbt model, a FastAPI endpoint, and a Debezium connector config all require different test strategies. Per-phase test strategies are defined in the phase CLAUDE.md `## Test Strategy` section, not here.

---

## Full Quality Stack

### Layer 1 — Pre-commit (before code enters git)

Configured in `.pre-commit-config.yaml` at repo root. Fires on every `git commit`.

| Hook | Purpose | Blocks commit on |
|---|---|---|
| `ruff` | Lint + format Python | Any lint error or formatting violation |
| `mypy` | Type check Python | Any type error |
| `bandit` | Security lint Python | Medium or high severity findings |
| `ggshield` | GitGuardian secret scanning | Any detected secret, credential, or token |

**ruff config:** `pyproject.toml` — line length 100, target Python 3.11, all rules enabled except those explicitly disabled per phase.

**mypy config:** `pyproject.toml` — `strict = true`. Every Python file must have type annotations. No `# type: ignore` without an inline justification comment explaining why.

**bandit config:** `.bandit` — severity threshold `MEDIUM`. Low severity findings are warnings, not blockers.

**ggshield:** Requires GitGuardian account (free for open source). Config in `.gitguardian.yaml`. Blocks on any secret match. No baseline exceptions without explicit team approval.

### Layer 2 — CI (every push, every PR)

GitHub Actions workflow: `.github/workflows/quality.yml`

```
On: push to any branch, pull_request to main

Jobs (run in parallel):
  lint:
    - ruff check
    - mypy --strict
    - bandit -r . -lll

  security:
    - ggshield secret scan

  unit-tests:
    - pytest {phase}/tests/unit/ -v --tb=short
    - Coverage report generated (not enforced globally — see per-phase Test Strategy)

  data-quality:        # only on phases that have these
    - dbt test
    - soda scan

  fitness-functions:
    - pytest {phase}/tests/contracts/ -v

Scheduled (weekly, not per push):
  dependency-audit:
    - pip-audit
    - Report findings — does not block unless CRITICAL severity
```

### Layer 3 — PR review gate (before merge)

Two independent checks, both required:

**CodeRabbit** — automatic. Fires on every PR via GitHub App. Reviews the diff for:
- Correctness bugs
- Security issues
- Code style violations not caught by ruff
- Missing error handling at system boundaries
- Performance anti-patterns

CodeRabbit comments must be addressed or explicitly dismissed with a reason before merge. Configuration in `.coderabbit.yaml` at repo root — rules are tailored per directory (PySpark rules differ from FastAPI rules differ from dbt macros).

**`/review-phase`** — manual. Run by the developer before merging. See `.claude/commands/review-phase.md`.

---

## Per-Phase Test Strategy

Each phase CLAUDE.md has a `## Test Strategy` section that defines:
- Which test types apply to this phase
- What the acceptance threshold is for each type
- What counts as a blocking failure vs. a warning
- For each test type, its **negative case** — the failure it is proven to catch (per `procedures/validation-standard.md`). A test type listed with only a positive threshold and no negative case (or `N/A — <reason>`) is incomplete. A quality gate that has never rejected bad data is unproven.

**Test types by phase category:**

### Infrastructure phases (01)
- `docker compose up` all services reach healthy state
- Terraform `plan` exits 0 with no unexpected changes
- All service ports respond to TCP connection
- No unit tests for config files — infrastructure is validated by running it

### Source system phases (02)
- Schema validation: all tables exist, all columns match expected types
- Seed data: row counts match expected values, no null PKs, FK integrity holds
- No application code → no unit tests

### CDC + streaming phases (03)
- Consumer lag = 0 after initial sync
- Message count at Kafka topic >= row count at source
- Avro schema registered in Schema Registry for every topic
- Deserialization test: consumer can decode a sample message without error

### Storage layer phases (04 Bronze, 05 Silver, 06 Gold)
- **Bronze:** row count parity with source (±0.1%), PII fields masked, Iceberg table readable via DuckDB
- **Silver:** Soda checks all pass, no duplicate PKs, no nulls on declared non-nullable fields
- **Gold:** dbt test suite passes (schema + referential integrity + custom business rules), SCD Type 2 has exactly one `current=true` per business key
- Unit tests for any transformation function that contains business logic — not for simple column renames

### Governance + catalog phases (07, 08, 09)
- Assets registered in OpenMetadata: count matches expected
- Lineage graph: source → Bronze → Silver → Gold chain is complete and traversable
- Data contracts: contract validation passes on current data, and fails correctly on injected bad data
- RBAC: role with restricted access cannot query restricted columns

### AI layer phases (10a, 10b, 10c)
- **Feature Store:** point-in-time test — features computed as-of T contain no data with event_time > T
- **Feature Store:** P99 latency test — online store endpoint responds in < 10ms under 50 concurrent requests
- **RAG:** retrieval test — top-3 results for a known query contain the expected document
- **Confidence Scoring:** every inference response has `confidence_band` field present, no exceptions
- **Confidence Scoring:** band thresholds match spec — High > 0.85, Medium 0.60–0.85, Low < 0.60

### Serving phases (11)
- FastAPI contract tests: every endpoint returns declared response schema
- FastAPI error tests: invalid input returns 422, not 500
- Superset dashboards load without error (smoke test)

### Observability phases (12)
- All services expose `/metrics` endpoint and Prometheus can scrape them
- All 6 SLO alert rules exist in Grafana and are in `normal` state on healthy stack
- Alert fires correctly when SLO is intentionally breached (inject a breach, confirm alert)

---

## Safety: Tag Before Risky Changes

Before any batch of changes that could break working functionality — a migration, a refactor spanning multiple files, a dependency upgrade — create a git tag:

```bash
git tag -a v{phase}-checkpoint-{description} -m "{what this checkpoint saves}"
# Example: git tag -a v04-checkpoint-pre-pii-refactor -m "Bronze working before PII masking refactor"
```

Cost: 5 seconds. Value: instant rollback point if the change batch makes things worse.

A risky change batch is any commit or sequence of commits that:
- Modifies more than 3 files related to the same component
- Upgrades a dependency with a major version bump
- Changes a shared interface — Kafka topic schema, Iceberg table schema, API response shape
- Is being applied to a component that is currently healthy and working

Tag BEFORE the change, not after. If something breaks mid-change and you tag after, the safety point is gone.

---

## Branching & Pull Request Workflow

`main` is always green and is never committed to directly. Every change reaches `main` through a pull
request, so the review gates — CodeRabbit and `/review-phase` — actually run.

- **One branch per phase.** A phase is built on a branch named after it: `01-infrastructure`,
  `04-bronze-layer`, `10a-feature-store`. Non-phase work uses a typed branch: `chore/...`, `docs/...`,
  `fix/...`. The phase branch maps 1:1 to the phase; merging it is the phase's completion.
- **Open a PR as soon as there's something to review.** Push the branch and open a PR against `main`.
  **CodeRabbit reviews every PR automatically** (config in `.coderabbit.yaml`, rules tailored per
  directory). CI runs on the same PR.
- **CodeRabbit comments are resolved before merge.** Each comment is either addressed or explicitly
  dismissed with a reason. `/review-phase` Check 6 verifies this; do not merge with open CodeRabbit
  findings.
- **Merge only after the gates pass.** `/review-phase` (code) and `/close-phase` (docs + contracts +
  chaos) must both pass, and CodeRabbit must be satisfied, before the PR merges. Prefer a squash or
  merge commit that names the phase — the merge is the durable "phase complete" marker in history.

Where this sits in the lifecycle: the branch is created at `/start-phase`, the PR is opened once
implementation has something to show, and the merge happens after `/close-phase`.

---

## What Is Never Acceptable

- `# type: ignore` without an inline comment explaining the specific reason
- A test that always passes regardless of what the code does (mock-everything tests that test nothing)
- Skipping a bandit HIGH severity finding without a written justification in the code
- A secret, token, or connection string hardcoded anywhere — use `.env` + `python-dotenv`, reference `os.environ`
- A fitness function stub with `pytest.mark.xfail` that stays as a stub after the phase ships
