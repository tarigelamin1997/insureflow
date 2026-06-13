# Phase 02 Seed Generator

Parameterized, deterministic scenario seed generator for the three InsureFlow source systems
(PMS / CMS / PFS). Produces per-instance SQL `INSERT` scripts that load the S01 happy-path
baseline plus the four deliberate post-acquisition data-quality scenarios (S02-S05).

Binding spec: [`procedures/seed-data.md`](../../procedures/seed-data.md).
Design rationale: [`decisions/adr-005-seed-generator-design.md`](../decisions/adr-005-seed-generator-design.md).

---

## What it generates

| File (in `output/`, gitignored) | Instance | Tables |
|---|---|---|
| `pms_seed.sql` | `postgres-pms` | agents, products, policyholders, policies, endorsements, renewals, cancellations |
| `cms_seed.sql` | `postgres-cms` | claims, claim_events, assessments, settlements, reserves, third_party_details |
| `pfs_seed.sql` | `postgres-pfs` | premium_transactions, reinsurance_entries, gl_settlements, ifrs17_data |

Each file is a single `BEGIN; TRUNCATE ... RESTART IDENTITY CASCADE; INSERT ...; COMMIT;`
transaction - **idempotent**: re-loading resets and re-seeds without duplicating or erroring.
Column names/types/enums in every `INSERT` match the Chunk-2 schema
(`schema/{pms,cms,pfs}/01-schema.sql`) exactly.

---

## How to run

Run from the **repository root** (the documented invocation):

```bash
# Default dev seed - full domain scale (~50K policyholders / 80K policies / 200K txns)
python 02-source-systems/seed/generate.py --scenarios S01,S02,S03,S04,S05

# CI / fast profile - ~1K policyholders, identical pass assertions
python 02-source-systems/seed/generate.py --scenarios S01,S02,S03,S04,S05 --scale 0.02

# Equivalent shorthand: 'all' expands to the IMPLEMENTED set (S01-S05), not the deferred ones
python 02-source-systems/seed/generate.py --scenarios all --scale 0.02
```

### Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--scenarios` | `S01,S02,S03,S04,S05` | Comma list of `S01`..`S12`, or `all`. Unknown IDs error; `S06`-`S12` are architected but raise `NotImplementedError` if selected (see Scope). |
| `--scale` | `1.0` | Float multiplier for **percentage-based** volumes. **Fixed-absolute** injections (S02=50, S03=30) ignore it. Must be `> 0`. |
| `--seed` | `42` | RNG seed. A fixed seed yields **byte-identical** output across runs/machines. |

Output lands in `02-source-systems/seed/output/` (created on demand, **gitignored** - the seed
is regenerated deterministically, never committed).

---

## Scenarios

### Implemented this phase (S01-S05)

| ID | Scenario | Injection kind | What it seeds |
|---|---|---|---|
| **S01** | Happy-path baseline | scaled population | Clean, fully-populated rows for all 17 tables, valid intra-instance FKs, all 4 segments. All dates ISO-8601, all currencies SAR (S04/S05 mutate a subset). |
| **S02** | Duplicate policyholders | **fixed = 50** | Exactly 50 extra policyholder rows reusing an existing NIC + name under a new `policyholder_id` (the post-acquisition merge). `policyholders.nic` is non-unique, so they load cleanly. |
| **S03** | Orphan claims | **fixed = 30** | Exactly 30 claims whose `policy_id` references a never-allocated (reserved high-band) policy - claims from an acquired entity whose policies were never migrated. `claims.policy_id` has no FK (cross-instance), so they load cleanly. |
| **S04** | Mixed date formats | **percentage ~40%** | Rewrites ~40% of `policyholders.dob` and `policies.policy_start_date` from ISO-8601 to legacy `DD/MM/YYYY` in the same TEXT column - both formats coexist. |
| **S05** | Mixed currency | **percentage ~15%** | Tags ~15% of `premium_transactions` as `USD`; the rest are `SAR` with a deterministic slice left `NULL` (NULL => SAR downstream). |

**Fixed-vs-percentage is the load-bearing distinction.** Fixed-absolute counts (S02=50, S03=30)
are read from `config.FIXED` and are invariant under `--scale` - a `--scale 0.02` run still
produces exactly 50 duplicate-NIC pairs and 30 orphan claims, because the deliberate edge events
are a realistic post-acquisition reality whether the book is 1K or 50K. Percentage injections
(S04/S05) operate on the already-scaled population, so their absolute counts scale while their
fractions stay constant.

### Architected but out of scope for Phase 02 (S06-S12)

S06-S12 are **registered but not implemented** this phase. They are listed in
`seed/registry.py` (`DEFERRED`) with their owning future phase, and selecting one raises a clear
`NotImplementedError`. They are implemented when their consuming phase arrives:

| ID | Scenario | Owning phase |
|---|---|---|
| S06 | NULL-heavy optional fields | Phase 05 |
| S07 | Boundary values | Phase 05 / 11 |
| S08 | High-velocity policyholder | Phase 10a |
| S09 | SCD Type 2 transitions | Phase 06 |
| S10 | Late-arriving claims | Phase 03 / 05 |
| S11 | Reinsurance threshold proximity | Phase 10a |
| S12 | IFRS 17 spanning contracts | Phase 06 / 09 |

Adding one = writing its `seed/scenarios/sNN_*.py` module (a `build(dataset, cfg, rng)` function)
and moving its ID from `DEFERRED` into `REGISTRY`.

---

## Module layout

```
seed/
|- generate.py     # CLI: argparse -> build dataset -> self-assert -> write 3 SQL files
|- builder.py      # build_dataset(cfg) + the seed-self invariant checks (importable, no I/O)
|- registry.py     # S01..S12 -> builder map; S06-S12 = NotImplementedError placeholders
|- config.py       # GenConfig, seeded RNG, BASELINE / FIXED / PERCENT volume model
|- model.py        # typed dataclasses mirroring the 17 schema tables + the Dataset container
|- fields.py       # deterministic synthetic-field helpers (names, NICs, dates, money, enums)
|- sql.py          # Dataset -> per-instance SQL serialisation (TRUNCATE preamble, OVERRIDING SYSTEM VALUE)
|- scenarios/
|  |- s01_happy_path.py
|  |- s02_duplicate_policyholders.py
|  |- s03_orphan_claims.py
|  |- s04_mixed_date_formats.py
|  |- s05_mixed_currency.py
|- output/         # generated SQL - gitignored
```

Scenarios compose by mutating one shared, fully-typed `Dataset` in registry order (S01 first).
The whole pipeline is driven by one seeded `random.Random` - no clock, UUID, or global RNG -
which is what makes the output deterministic.

---

## Determinism & idempotency

- **Determinism:** `python ... --seed 42` twice produces byte-identical `.sql` (verify with
  `sha256sum output/*.sql`). All randomness is seeded; `created_at`/`updated_at` are left to the
  schema `DEFAULT now()` and are not emitted.
- **Idempotency:** each file's `TRUNCATE ... RESTART IDENTITY CASCADE` preamble (inside one
  transaction) means re-loading resets and re-seeds - no duplication, no error.

---

## Tests

Seed-self assertions (no Docker, no psql - they run against the in-memory dataset):

```bash
pytest 02-source-systems/tests/unit -q
```

They verify: exactly 50 duplicate-NIC pairs and 30 orphan claims (at `--scale 0.02` and `1.0`),
intra-seed FK integrity, zero NULL PKs, both S04 date formats present, both S05 currencies
present, the fixed-vs-scale behaviour, and determinism (same seed => identical SQL).

End-to-end pipeline assertions (does the platform handle the seed?) live in the consuming
phases' CLAUDE.md `## Test Strategy` (Phase 05 dedup, Phase 06 referential integrity).

## Code quality

The generator is Python and inherits the repo tooling baseline:

```bash
ruff check 02-source-systems/seed 02-source-systems/tests/unit
ruff format --check 02-source-systems/seed 02-source-systems/tests/unit
mypy --strict 02-source-systems/seed
bandit -ll -r 02-source-systems/seed
```
