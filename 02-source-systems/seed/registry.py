"""Scenario registry - maps scenario IDs to builder callables, in application order.

The registry is the single extension point for the scenario-module pattern: adding a scenario
means writing a `build(dataset, cfg, rng)` module and registering it here. Scenarios run in the
order listed (S01 first so injection scenarios have a baseline to mutate).

Scope this phase: S01-S05 are implemented. S06-S12 are ARCHITECTED but NOT implemented - they
are registered with `_not_implemented`, which raises `NotImplementedError` naming the owning
future phase. This keeps the `--scenarios` selection surface complete (the CLI validates IDs
against the registry) while making the out-of-scope boundary explicit and loud, never silent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from seed.scenarios import (
    s01_happy_path,
    s02_duplicate_policyholders,
    s03_orphan_claims,
    s04_mixed_date_formats,
    s05_mixed_currency,
)

if TYPE_CHECKING:
    import random

    from seed.config import GenConfig
    from seed.model import Dataset


class ScenarioBuilder(Protocol):
    """Callable that mutates the shared dataset for one scenario."""

    def __call__(self, dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
        """Apply the scenario's rows/mutations to `dataset`."""
        ...


# Scenarios implemented in Phase 02 (S01 baseline + the four DQ scenarios).
IMPLEMENTED: tuple[str, ...] = ("S01", "S02", "S03", "S04", "S05")

# Scenarios architected but deferred - each maps to its owning future phase (per
# procedures/seed-data.md Scenario Inventory). Implementing one = writing its module and
# moving its ID from here into the registry below.
DEFERRED: dict[str, str] = {
    "S06": "NULL-heavy optional fields (Phase 05 Soda not-null checks)",
    "S07": "Boundary values (Phase 05 / 11 range + Pydantic checks)",
    "S08": "High-velocity policyholder (Phase 10a feature computation)",
    "S09": "SCD Type 2 transitions (Phase 06 dim_policyholder history)",
    "S10": "Late-arriving claims (Phase 03 / 05 CDC ordering + dedup)",
    "S11": "Reinsurance threshold proximity (Phase 10a ML feature boundary)",
    "S12": "IFRS 17 spanning contracts (Phase 06 / 09 fiscal-year allocation)",
}


def _make_deferred(scenario_id: str, description: str) -> ScenarioBuilder:
    """Build a placeholder that raises a clear NotImplementedError when selected."""

    def _not_implemented(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
        _ = (dataset, cfg, rng)
        msg = (
            f"{scenario_id} is architected but NOT implemented in Phase 02 "
            f"(out of scope): {description}. "
            f"Implement its scenario module, then register it in seed/registry.py."
        )
        raise NotImplementedError(msg)

    return _not_implemented


# The authoritative ID -> builder map. Insertion order is application order.
REGISTRY: dict[str, ScenarioBuilder] = {
    "S01": s01_happy_path.build,
    "S02": s02_duplicate_policyholders.build,
    "S03": s03_orphan_claims.build,
    "S04": s04_mixed_date_formats.build,
    "S05": s05_mixed_currency.build,
}
for _sid, _desc in DEFERRED.items():
    REGISTRY[_sid] = _make_deferred(_sid, _desc)

ALL_SCENARIO_IDS: tuple[str, ...] = tuple(REGISTRY)


def resolve(scenarios: list[str]) -> list[str]:
    """Validate and order a requested scenario list against the registry.

    Accepts `all` (expands to every IMPLEMENTED scenario - deferred ones are not auto-run).
    Returns the requested IDs in canonical registry order so application order is stable
    regardless of how the caller listed them. Raises ValueError on an unknown ID.
    """
    if scenarios == ["all"]:
        return list(IMPLEMENTED)
    requested = set()
    for raw in scenarios:
        sid = raw.strip().upper()
        if sid not in REGISTRY:
            valid = ", ".join(ALL_SCENARIO_IDS)
            msg = f"Unknown scenario {raw!r}. Valid IDs: {valid}, or 'all'."
            raise ValueError(msg)
        requested.add(sid)
    return [sid for sid in REGISTRY if sid in requested]
