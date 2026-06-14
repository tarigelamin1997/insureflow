"""Scenario modules - one per seeded scenario.

Each module exposes a `build(dataset, cfg, rng)` function that mutates the shared `Dataset`
in place. Scenarios are applied in registry order (`seed.registry`) so that injection
scenarios (S02-S05) layer onto the S01 baseline that runs first.

In scope this phase: S01-S05. S06-S12 are architected (registered) but deliberately not
implemented - their registry entries raise `NotImplementedError`.
"""
