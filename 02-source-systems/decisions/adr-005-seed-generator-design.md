# ADR-005 - Scenario-based seed generator: deterministic, composable, SQL-file output

## Status
Accepted

## Context
Phase 02 must load deliberate post-acquisition data-quality scenarios (S01 baseline + S02-S05) that downstream phases use as known-answer fixtures: Phase 05 Silver dedup keys on the 50 duplicate-NIC pairs, Phase 06 Gold referential integrity keys on the 30 orphan claims, Bronze/Silver date-casting keys on the S04 mixed-format dates, and IFRS 17 marts key on the S05 mixed currency. `procedures/seed-data.md` is the binding spec: it fixes the 12-scenario inventory, the S01 full-domain volumes, the percentage-vs-fixed injection split, and a determinism + idempotency requirement. Three design questions had to be settled before writing any generator code, and each has a real alternative that a later phase would have been stuck with:

1. **Reproducibility** - "it broke with this data" must be reproducible by another engineer/session, so the dataset must be a pure function of its parameters.
2. **Scenario composability** - S02-S05 must layer onto S01 independently (and S06-S12 must be addable later without rewriting the core), so the generator needs a clean extension point.
3. **Output target** - the seed must reach three separate Postgres instances (ADR-002) offline, reproducibly, and idempotently.

This phase implements S01-S05 only; S06-S12 are architected (registered) but out of scope, so the design also had to make "add a scenario later" cheap without implementing them now.

## Decision

**1 - Determinism via a single fixed-seed RNG.** All variety flows through one `random.Random(seed)` (default `42`), threaded explicitly into every scenario and field helper. No module calls the global `random`, the wall clock, `uuid`, or any other ambient entropy. `created_at`/`updated_at` are left to the schema `DEFAULT now()` and are NOT emitted, so the SQL text itself carries no timestamp. Result: a fixed `--seed` yields byte-identical SQL across runs and machines (verified by hashing two runs).

**2 - Composable scenario modules behind a registry.** Each scenario is a module exposing `build(dataset, cfg, rng)` that mutates one shared, fully-typed `Dataset` (one dataclass list per table). A registry (`seed/registry.py`) maps `S01..S12` to builders and fixes application order (S01 first, so injections layer on a real baseline). S06-S12 are registered with a placeholder that raises `NotImplementedError` naming the owning future phase - the `--scenarios` surface stays complete and the out-of-scope boundary is loud, never silent. Adding a scenario = writing a module + one registry line.

**3 - Percentage-vs-fixed injection split as data, not code paths.** Baseline volumes (`config.BASELINE`) pass through `cfg.scaled(n)` (multiplied by `--scale`); **fixed-absolute** injections (S02 = 50 duplicate-NIC pairs, S03 = 30 orphan claims) read `config.FIXED` directly and never touch `--scale`. Percentage injections (S04 ~40%, S05 ~15%) operate on the already-scaled population, so their absolute counts track `--scale` while their fractions stay constant. A `--scale 0.02` CI run therefore still produces exactly 50 pairs and 30 orphans.

**4 - SQL-file output, not direct DB load.** The generator serialises the in-memory `Dataset` to three per-instance `.sql` files (`pms_seed.sql`, `cms_seed.sql`, `pfs_seed.sql`) under `seed/output/` (gitignored), loadable by the Postgres entrypoint / `psql`. Each file is one `BEGIN; TRUNCATE <tables> RESTART IDENTITY CASCADE; INSERT ...; COMMIT;` transaction - **idempotent**: re-loading resets and re-seeds without duplicating or erroring. INSERTs use `OVERRIDING SYSTEM VALUE` to load the seed's own deterministic surrogate IDs against the `GENERATED ALWAYS AS IDENTITY` PKs, so intra-seed FKs resolve and `RESTART IDENTITY` keeps future app writes collision-free.

The generator passes `ruff check` + `ruff format`, `mypy --strict`, and `bandit -ll` (the one B608 hardcoded-SQL finding is justified inline: this is a code generator over a closed internal table/column set, output is an offline `.sql` file, and every value is escaped via `_lit`).

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| **Direct DB load** (generator opens psycopg connections and INSERTs into the three live instances) | Couples seed generation to a running stack, breaks the offline-first / single-`docker compose up` model, and makes the seed un-reviewable as a diff. The self-assertion tests could no longer run without Docker. SQL files are inspectable, replayable, and load via the standard postgres entrypoint. |
| **Faker / factory_boy for synthetic values** | Adds a dependency whose global-state seeding is easy to get subtly wrong (non-reproducible across versions/locales), for variety this phase does not need - stdlib `random.Random(seed)` is fully sufficient for names/NICs/money and is trivially deterministic. The 100%-offline constraint also discourages avoidable deps. |
| **One monolithic `generate.py`** (no per-scenario modules/registry) | Makes S02-S05 entangle with S01 and makes S06-S12 a future rewrite rather than an addition. The registry/`build()` contract is the property that lets "S02 + S06 together" compose and lets a later phase add a scenario by writing one module. |
| **Scale every injection** (treat S02/S03 as percentages too) | Destroys the known-answer fixture: at `--scale 0.02` the orphan/dup counts would no longer be 50/30, so Phase 05/06 gates would lose their constant-count assertion. `seed-data.md` explicitly classes rare-event injections as fixed-absolute - 30 orphans is realistic whether the book is 1K or 50K. |
| **Emit `created_at`/`updated_at` explicitly** (for "complete" rows) | Any emitted timestamp is either wall-clock (non-deterministic) or a hardcoded constant (misleading provenance). Leaving them to `DEFAULT now()` keeps the SQL byte-stable and lets the DB record the true load time. |

## Consequences

### Makes easier
- Any engineer/session reproduces the exact dataset from `--scenarios/--scale/--seed` alone; a bug report is replayable byte-for-byte.
- Phase 05/06 gates get stable known-answer fixtures (50 dup-NIC pairs, 30 orphans) at any scale, including the CI `--scale 0.02` profile.
- Adding S06-S12 later is a module + a registry line, not a refactor; the deferred placeholders already validate the `--scenarios` surface.
- The seed is reviewable as a SQL diff and loads idempotently, so a re-run during development never corrupts state.

### Makes harder
- The typed `Dataset` must stay in lockstep with the C2 schema - a column/type change in `schema/{pms,cms,pfs}/01-schema.sql` requires a matching dataclass edit (caught by `mypy --strict` and the round-trip load, not silently).
- Full-scale (`--scale 1`) materialises ~1M rows in memory before serialising; acceptable for a batch seed generator, but it is not a streaming writer.

### Makes impossible
- A non-reproducible seed: there is no entropy source other than `--seed`, so two runs with the same parameters cannot diverge.
- A silent out-of-scope scenario: selecting S06-S12 raises `NotImplementedError` naming the owning phase, so an unimplemented scenario can never quietly produce an empty/partial dataset.
- Scaling away the deliberate edge counts: S02/S03 read `FIXED` and never see `--scale`, so the 50/30 fixtures cannot drift with volume.

### Impact on other phases
- **Phase 03 (CDC):** consumes the loaded rows as the initial snapshot Debezium captures; the deterministic IDs make snapshot assertions stable.
- **Phase 05 (Silver):** S02 (50 dup-NIC pairs) and S04 (mixed dates) are its dedup/normalisation fixtures; depends on this generator's exact counts.
- **Phase 06 (Gold):** S03 (30 orphans) and S05 (mixed currency) are its referential-integrity / IFRS 17 fixtures.
- **Future scenario phases (05/06/09/10a):** add S06-S12 by implementing the registered placeholder modules; the registry/`build()` contract is the stable extension point this ADR establishes.
