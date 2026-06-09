# Procedure: Seed Data

## Guiding Principle

Seed data is not filler — it is a test suite. Every scenario targets a specific pipeline stage,
a specific transformation, or a specific quality gate. The seed is not done when data loads into
PostgreSQL. It is done when the pipeline behaves correctly with it end-to-end, and a pytest
assertion confirms the expected state in the target layer.

Generic seed data tests the happy path. Production breaks on edge cases. Design scenarios that
stress what is actually hard: duplicate identity resolution, late-arriving events, fiscal year
boundaries, ML feature boundary values.

---

## Scenario Inventory

InsureFlow seeds 12 named scenarios. Scenarios S02–S05 are the 4 deliberate data quality issues
documented in the README — the post-acquisition reality. S06–S12 stress the AI layer and serving
layer edge cases that happy-path data cannot exercise.

| ID | Scenario | What it stress-tests | Downstream target |
|---|---|---|---|
| S01 | Happy path baseline | End-to-end flow on clean data | All layers |
| S02 | Duplicate policyholders | Silver deduplication + `dim_policyholder` SCD Type 2 | Phase 05, 06 |
| S03 | Orphan claims | Gold referential integrity — `fact_claims` FK to `dim_policyholder` | Phase 06 |
| S04 | Date format inconsistency | Bronze type casting + Silver standardisation — DD/MM/YYYY vs ISO 8601 | Phase 04, 05 |
| S05 | Mixed currency | SAR vs USD in premium transactions — Bronze field handling + IFRS 17 reporting | Phase 04, 06 |
| S06 | NULL-heavy optional fields | Soda not-null checks on non-required columns | Phase 05 |
| S07 | Boundary values | Soda range checks + Pydantic validation — premium=0, claim=policy_limit, coverage_ratio=1.0 | Phase 05, 11 |
| S08 | High-velocity policyholder | Feature computation at scale — 500+ claims in 12 months | Phase 10a |
| S09 | SCD Type 2 transitions | `dim_policyholder` history — tier change, address change, multiple versions per key | Phase 06 |
| S10 | Late-arriving claims | CDC ordering + deduplication — claim events arriving 6+ months after loss_date | Phase 03, 05 |
| S11 | Reinsurance threshold proximity | ML feature `reinsurance_threshold_proximity` boundary stress | Phase 10a |
| S12 | IFRS 17 spanning contracts | `mart_loss_ratio_report` correctness across fiscal year boundary | Phase 06, 09 |

---

## Scenario Specifications

Each scenario is defined by: key data characteristics, row volumes, expected pipeline behaviour,
and the pass assertion — a concrete, verifiable claim about the state of a downstream layer
after the pipeline runs.

**Injection volumes are of two kinds:**
- **Percentage-based** (S04 40%, S05 15%, S06 25%) — scale with the baseline automatically when
  `--scale` changes the row counts.
- **Fixed-absolute deliberate edge events** (S02 50, S03 30, S07 20, S08 5×500, S09 100, S10 50,
  S11 30, S12 20) — these are rare-event injections, intentionally a constant count regardless of
  baseline size. A handful of orphan claims is a realistic post-acquisition reality whether the
  book is 1K or 50K policies; their pass assertions are written against the absolute count.

### S01 — Happy path baseline

**Key characteristics:** Clean data. All required fields populated. Normal statistical distributions.
No DQ issues. Covers all 4 insurance segments: Motor, Healthcare, P&C, Protection & Savings.

**Row volumes (default profile — full domain scale, matches README Domain Model):**
- PMS: 50,000 policyholders · 80,000 policies · 10,000 endorsements
- CMS: 25,000 claims · 50,000 claim events
- PFS: 200,000 premium transactions

These are the canonical domain volumes. Smaller runs use `--scale` (see Scale Profiles below);
the pass assertions hold at any scale.

**Expected behaviour:** All records flow Bronze → Silver → Gold without any Soda check failures.

**Pass assertion:**
```
Gold fact_policies row count = Silver policies row count (±0.1%)
Gold dim_policyholder has exactly 1 is_current=true per policyholder_id
Soda scan Silver: 0 failures
```

---

### S02 — Duplicate policyholders

**Key characteristics:** 50 policyholders appear twice in PMS with different `policyholder_id` values.
Same NIC, same name, different IDs — the post-acquisition merge scenario.

**Row volumes:** S01 baseline + 50 duplicate policyholder records

**Expected behaviour:** Silver deduplication consolidates to one canonical record per NIC.
`dim_policyholder` SCD Type 2 carries the merge event as a version transition.

**Pass assertion:**
```
Silver policyholder count = S01 count (50 duplicates merged, not doubled)
dim_policyholder: no NIC appears in more than one is_current=true row
```

---

### S03 — Orphan claims

**Key characteristics:** 30 claims in CMS reference `policy_id` values that do not exist in PMS.
These represent claims from the acquired entity whose policies were never migrated.

**Row volumes:** S01 baseline + 30 orphan claim records

**Expected behaviour:** Gold referential integrity check catches the 30 orphan claims.
They are flagged in Soda results and excluded from `fact_claims`. An alert or DQ result records
the count.

**Pass assertion:**
```
fact_claims row count = total claims - 30 (orphans excluded)
Soda scan Gold: referential integrity check reports 30 failures (expected, not silent)
```

---

### S04 — Date format inconsistency

**Key characteristics:** 40% of records in PMS use `DD/MM/YYYY` (pre-acquisition legacy format).
60% use ISO 8601. Both formats appear in the same column.

**Row volumes:** S01 baseline with mixed date formats applied to `policy_start_date` and `dob`

**Expected behaviour:** Bronze accepts both formats (raw fidelity). Silver standardises all dates
to ISO 8601. No records dropped.

**Pass assertion:**
```
Silver policies row count = Bronze policies row count (no records dropped due to date parsing)
Silver: all policy_start_date values parseable as ISO 8601 date
Bronze: raw column contains the original mixed-format strings
```

---

### S05 — Mixed currency

**Key characteristics:** 15% of premium transactions in PFS carry amounts in USD.
The `currency` field is populated. SAR transactions have `currency = 'SAR'` or null.

**Row volumes:** S01 baseline with 15% of transactions tagged USD

**Expected behaviour:** Bronze preserves the `currency` field. Silver normalises to SAR using a
static exchange rate. Gold IFRS 17 marts report in SAR only.

**Pass assertion:**
```
Silver: no USD amounts in premium_amount_sar column
Silver: usd_transactions_normalised Soda custom check passes
Gold mart_loss_ratio_report: all amounts in SAR (no USD values present)
```

---

### S06 — NULL-heavy optional fields

**Key characteristics:** 25% NULL rate across all optional columns in PMS, CMS, and PFS.
Some NULL values intentionally placed in columns that are not-null in Silver schema contracts.

**Row volumes:** S01 baseline with NULL injection across optional and required fields

**Expected behaviour:** Soda not-null checks fail for records with NULLs in required Silver columns.
Optional-column NULLs pass. The pipeline does not silently accept required-column NULLs.

**Pass assertion:**
```
Soda scan Silver: not-null checks fire for each required column that received a NULL
Records with required-column NULLs are excluded from Silver output or quarantined
Silver row count < Bronze row count (rejected records removed, not silently included)
```

---

### S07 — Boundary values

**Key characteristics:** Records at the exact boundary of every validated range:
- `premium_amount`: 0.00 (minimum), 999,999.99 (maximum)
- `claim_amount`: exactly equal to `policy_limit`
- `coverage_ratio`: exactly 0.0 and exactly 1.0
- `policyholder_age`: 18 (minimum insurable age in KSA), 100

**Row volumes:** 20 boundary records added to S01 baseline

**Expected behaviour:** Soda range checks and Pydantic models handle boundary values without
crashing. Values at the boundary (not outside it) must be accepted, not rejected.

**Pass assertion:**
```
All 20 boundary records reach Gold (not rejected by Soda range checks)
FastAPI Feature Store endpoint returns valid features for high-velocity boundary policyholders
No 500 errors when serving boundary-value features
```

---

### S08 — High-velocity policyholder

**Key characteristics:** 5 policyholders each with 500+ claims over 12 months.
Represents fraud-investigation-level claim frequency.

**Row volumes:** S01 baseline + 2,500 additional claim records (5 × 500)

**Expected behaviour:** Feature computation for `claim_frequency_12m` handles these correctly.
The feature value is high but valid — not capped, not errored.

**Pass assertion:**
```
Feature Store: claim_frequency_12m > 400 for the 5 high-velocity policyholders
Online store P99 latency remains < 10ms with high-velocity features in the store
No feature computation timeout or OOM error
```

---

### S09 — SCD Type 2 transitions

**Key characteristics:** 100 policyholders undergo changes that require new dimension versions:
- 40 policyholders change address (new `valid_from`, old record gets `valid_to`, `is_current=false`)
- 35 change insurance tier (Motor → Healthcare adds a product holding)
- 25 undergo both changes in sequence

**Row volumes:** S01 baseline + 100 update events sourced through CDC

**Expected behaviour:** `dim_policyholder` records correct SCD Type 2 history. Each change creates
a new row. No data loss. The previous version is accessible via `valid_from`/`valid_to` range.

**Pass assertion:**
```
dim_policyholder: 100 policyholders with multiple versions (is_current=true + ≥1 historical)
Point-in-time query as_of pre-change returns old tier/address
Point-in-time query as_of post-change returns new tier/address
No policyholder appears in more than one is_current=true row
```

---

### S10 — Late-arriving claims

**Key characteristics:** 50 claim events arrive in the CDC stream with `created_at` timestamps
6+ months before their Kafka offset timestamp. Simulates delayed system sync from an acquired
entity's legacy claims system.

**Row volumes:** S01 baseline + 50 late-arriving claim events

**Expected behaviour:** Silver deduplication handles out-of-order events correctly.
The canonical claim record reflects the authoritative state, not the arrival order.

**Pass assertion:**
```
Silver: no duplicate claim_ids (deduplication resolved the late arrivals)
Gold fact_claims: claim records reflect correct business dates, not Kafka arrival timestamps
Consumer lag returns to 0 after processing (no events stuck)
```

---

### S11 — Reinsurance threshold proximity

**Key characteristics:** 30 policies with `sum_insured` values within 5% of the reinsurance
retention threshold (the boundary at which the insurer passes risk to the reinsurer).

**Row volumes:** S01 baseline + 30 threshold-proximity policies

**Expected behaviour:** ML feature `reinsurance_threshold_proximity` computes correctly
for these policies. Values cluster near 0.0 (at threshold) and 1.0 (far below threshold).

**Pass assertion:**
```
Feature Store: reinsurance_threshold_proximity values are in [0.0, 1.0] for all 30 policies
No NULL or NaN values for the threshold-proximity feature
Confidence Scoring: these policies route to Medium or Low band (not auto-approved)
```

---

### S12 — IFRS 17 spanning contracts

**Key characteristics:** 20 insurance contracts with `coverage_start_date` in Q4 of one fiscal
year and `coverage_end_date` in Q1 of the next. These contracts must be correctly allocated
across two reporting periods in IFRS 17 liability calculations.

**Row volumes:** S01 baseline + 20 spanning contracts

**Expected behaviour:** `mart_loss_ratio_report` correctly pro-rates premium and claims
across fiscal year boundaries. No amounts are double-counted or lost.

**Pass assertion:**
```
mart_loss_ratio_report: sum of allocated premiums for spanning contracts equals total premium
  (no double-counting, no loss from rounding)
Phase 09 IFRS 17 compliance check: spanning contracts appear in both fiscal year report periods
```

---

## Technical Requirements

### Generator design

The seed data generator lives at `02-source-systems/seed/generate.py`.

- **Fixed random seed** — default `42`. Same parameters always produce the same dataset.
  Debugging requires reproducibility: "it broke with this data" must be reproducible by another
  session or engineer.
- **Parameterized** — accepts `--scenarios` (comma-separated list of scenario IDs),
  `--scale` (multiplier for row counts), `--seed` (override random seed).
- **Composable scenarios** — each scenario flag is independent. Running S02 + S06 together
  produces a dataset with both duplicate policyholders AND NULL-heavy fields.
- **Output** — SQL INSERT scripts per source system, loadable via `psql`.

```bash
# Examples
python seed/generate.py --scenarios S01              # Happy path only
python seed/generate.py --scenarios S01,S02,S03      # Happy path + duplicate policyholders + orphan claims
python seed/generate.py --scenarios all --scale 2    # All scenarios at 2x row volume
```

### Scale Profiles

The S01 baseline row volumes are the **full domain scale** (50K policyholders / 80K policies /
25K claims / 200K transactions) — identical to the README Domain Model. `--scale` multiplies the
percentage-based volumes; fixed-absolute edge injections stay constant.

| Profile | Invocation | Use |
|---|---|---|
| `default` (full) | `--scale 1` (default) | Production-representative volume. README and phase Validation Gates assume this. |
| `ci` (fast) | `--scale 0.02` | ~1K policyholders. Fast end-to-end pipeline runs in CI where full scale would be too slow. All scenario pass assertions still hold — only fixed-absolute injections become proportionally more prominent. |
| `stress` | `--scale 2`+ | Volume chaos (Angle 1). Used by `chaos/load/` to push the pipeline past nominal. |

Every scenario's pass assertion is scale-invariant: it asserts a relationship (counts merged,
orphans excluded, no duplicate PKs), not an absolute total that only holds at one scale.

### File locations

```
02-source-systems/
└── seed/
    ├── generate.py              # Parameterized generator
    ├── scenarios/
    │   ├── s01_happy_path.py
    │   ├── s02_duplicate_policyholders.py
    │   ├── ...
    │   └── s12_ifrs17_spanning.py
    ├── output/                  # Generated SQL files — gitignored
    │   ├── pms_seed.sql
    │   ├── cms_seed.sql
    │   └── pfs_seed.sql
    └── README.md                # How to run, scenario descriptions
```

### Assertion standard

Every scenario has a corresponding pytest assertion in
`02-source-systems/tests/unit/test_seed_scenarios.py`.

These tests validate the seed itself — not the full pipeline. They run against the raw SQL
output before data is loaded into PostgreSQL.

What each test must verify:
- Row counts match expected values for the scenario
- FK integrity holds within the seed (claims reference valid policy_ids for non-orphan records)
- Scenario-specific invariant: S02 verifies duplicate `policyholder_id` pairs exist,
  S03 verifies orphan `policy_id` references exist in claims

End-to-end pipeline assertions (does the platform handle the seed correctly?) are defined
in the `## Test Strategy` section of the relevant phase CLAUDE.md (Phase 05 for deduplication,
Phase 06 for referential integrity, Phase 10a for feature computation).

---

## Default Seed

The default scenario set for all development and CI runs is:

```bash
python seed/generate.py --scenarios S01,S02,S03,S04,S05              # dev: full domain scale
python seed/generate.py --scenarios S01,S02,S03,S04,S05 --scale 0.02 # CI: ci fast profile
```

This seeds the 4 deliberate DQ issues (S02–S05) on top of the happy path baseline (S01).
It reflects the post-acquisition reality described in the project README and is sufficient
for all phases through Phase 06. Dev runs use full domain scale; CI uses the `ci` profile
(`--scale 0.02`) for speed — the pass assertions are identical under both (see Scale Profiles).

Add S06–S12 when working on phases that require those scenarios (AI layer, serving, IFRS 17).
