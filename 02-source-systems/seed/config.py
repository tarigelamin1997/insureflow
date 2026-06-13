"""Generation config, seeded RNG, and the baseline volume model.

The percentage-vs-fixed injection split that `procedures/seed-data.md` mandates lives here,
expressed as data:

- `BASELINE` holds the S01 full-domain row counts (50K policyholders, 80K policies, ...).
- `GenConfig.scaled(n)` multiplies a baseline count by `--scale` (rounded, floored at 1 for
  any non-zero baseline) - this is how **percentage-based** scenarios (S04 ~40%, S05 ~15%)
  scale: they operate on a population that already grew/shrank with `--scale`.
- **Fixed-absolute** injections (S02 = 50 duplicate-NIC pairs, S03 = 30 orphan claims) read
  their counts from `FIXED`, which `--scale` never touches. A `--scale 0.02` run still
  produces exactly 50 pairs and 30 orphans.

All randomness flows through one `random.Random` seeded from `--seed` (default 42). No module
here calls the global `random`, the clock, or `uuid` - determinism is structural.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Baseline:
    """S01 full-domain (scale 1.0) row counts - the README Domain Model volumes."""

    policyholders: int = 50_000
    policies: int = 80_000
    endorsements: int = 10_000
    agents: int = 200
    products: int = 40
    renewals: int = 20_000
    cancellations: int = 8_000
    claims: int = 25_000
    claim_events: int = 50_000
    assessments: int = 15_000
    settlements: int = 12_000
    reserves: int = 18_000
    third_party_details: int = 6_000
    premium_transactions: int = 200_000
    reinsurance_entries: int = 6_000
    gl_settlements: int = 120_000
    ifrs17_data: int = 10_000


@dataclass(frozen=True)
class FixedInjections:
    """Fixed-absolute deliberate-edge counts - invariant under `--scale`.

    Only S02/S03 are in scope for Phase 02. The S06-S12 values are recorded for when those
    scenarios are implemented, but their builders are not wired this phase (see registry).
    """

    s02_duplicate_nic_pairs: int = 50
    s03_orphan_claims: int = 30


@dataclass(frozen=True)
class PercentInjections:
    """Percentage-based injection rates - applied to the (already scaled) population."""

    s04_legacy_date_fraction: float = 0.40  # 40% of dated rows use DD/MM/YYYY
    s05_usd_fraction: float = 0.15  # 15% of premium transactions carry USD


BASELINE = Baseline()
FIXED = FixedInjections()
PERCENT = PercentInjections()


@dataclass
class GenConfig:
    """Resolved generation parameters for one run."""

    scenarios: list[str]
    scale: float
    seed: int

    def scaled(self, baseline_count: int) -> int:
        """Scale a baseline row count by `--scale`.

        Floored at 1 for any positive baseline so a tiny `--scale` (e.g. 0.02 on a 40-row
        table) never produces an empty parent table that would orphan its children. Fixed
        injections do NOT pass through here - they read `FIXED` directly.
        """
        scaled = round(baseline_count * self.scale)
        if baseline_count > 0:
            return max(1, scaled)
        return 0


def make_rng(seed: int) -> random.Random:
    """Construct the single seeded RNG used for the whole run.

    `random.Random(seed)` is deterministic across runs and machines for a fixed seed; it is
    used for synthetic-data variety only, never for security. (bandit S311 is suppressed at
    the call site with this justification.)
    """
    return random.Random(seed)  # noqa: S311 - deterministic test-data variety, not crypto
