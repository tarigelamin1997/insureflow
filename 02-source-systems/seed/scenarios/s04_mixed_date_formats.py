"""S04 - Date format inconsistency (PERCENTAGE-based injection, scales with --scale).

Rewrites a deterministic `PERCENT.s04_legacy_date_fraction` (= 40%) of dated rows from the
ISO-8601 baseline format to the legacy `DD/MM/YYYY` format, in the same TEXT column. Both
formats then coexist in `policyholders.dob` and `policies.policy_start_date` - exactly the
pre-/post-acquisition mix the schema's TEXT date columns exist to preserve (raw fidelity;
Silver normalises in Phase 05).

PERCENTAGE, not fixed: this operates on the already-scaled baseline population, so the
*absolute* number of legacy-format rows grows and shrinks with `--scale` while the *fraction*
stays ~40%. No new rows are added - existing values are reformatted in place.

Determinism: a row is selected for legacy formatting iff `rng.random() < fraction`, drawn from
the single seeded RNG in a fixed iteration order, so the same seed reformats the same rows.
The ISO string is parsed back to a date and re-rendered as `DD/MM/YYYY` - no value is lost,
only its textual format changes.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from seed import fields as fx
from seed.config import PERCENT

if TYPE_CHECKING:
    import random

    from seed.config import GenConfig
    from seed.model import Dataset


def _to_legacy(iso_value: str | None, rng: random.Random, fraction: float) -> str | None:
    """With probability `fraction`, re-render an ISO date string as DD/MM/YYYY."""
    if iso_value is None:
        return iso_value
    if rng.random() >= fraction:
        return iso_value
    parsed = dt.date.fromisoformat(iso_value)
    return fx.legacy_date(parsed)


def build(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Reformat ~40% of dob / policy_start_date values to legacy DD/MM/YYYY in place."""
    _ = cfg  # fraction is a percentage of the (already scaled) population
    fraction = PERCENT.s04_legacy_date_fraction
    for ph in dataset.policyholders:
        ph.dob = _to_legacy(ph.dob, rng, fraction)
    for pol in dataset.policies:
        pol.policy_start_date = _to_legacy(pol.policy_start_date, rng, fraction)
