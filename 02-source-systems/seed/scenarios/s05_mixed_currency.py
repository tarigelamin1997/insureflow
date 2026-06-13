"""S05 - Mixed currency (PERCENTAGE-based injection, scales with --scale).

Tags a deterministic `PERCENT.s05_usd_fraction` (= 15%) of premium transactions with
`currency = 'USD'`. The remaining ~85% are SAR, of which a deterministic slice is left
`currency = NULL` (NULL => SAR downstream, per the C2 schema comment) and the rest explicit
`'SAR'` - so both the USD/SAR split AND the SAR/NULL ambiguity the spec calls for are present.

PERCENTAGE, not fixed: operates on the already-scaled `premium_transactions` population, so the
absolute USD count tracks `--scale` while the fraction stays ~15%. No new rows are added -
the `currency` field is mutated in place. The CHECK constraint `currency IN ('SAR','USD')`
passes on NULL, so the NULL slice is valid.

Bronze (Phase 04) preserves `currency`; Silver normalises USD -> SAR via a static rate; Gold
IFRS 17 marts report in SAR only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seed.config import PERCENT

if TYPE_CHECKING:
    import random

    from seed.config import GenConfig
    from seed.model import Dataset

# Of the non-USD remainder, this fraction is left NULL (NULL => SAR) vs explicit 'SAR'.
_NULL_SAR_FRACTION = 0.20


def build(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Tag ~15% of premium transactions USD; leave a SAR/NULL mix for the rest."""
    _ = cfg  # fraction is a percentage of the (already scaled) population
    usd_fraction = PERCENT.s05_usd_fraction
    for txn in dataset.premium_transactions:
        roll = rng.random()
        if roll < usd_fraction:
            txn.currency = "USD"
        elif rng.random() < _NULL_SAR_FRACTION:
            txn.currency = None  # NULL => SAR downstream
        else:
            txn.currency = "SAR"
