"""S02 - Duplicate policyholders (FIXED-ABSOLUTE injection, scale-invariant).

Injects exactly `FIXED.s02_duplicate_nic_pairs` (= 50) additional policyholder rows, each a
duplicate of an existing baseline policyholder: SAME `nic` and `full_name`, a NEW
`policyholder_id`. This is the post-acquisition merge reality - the same person entered twice
under two system IDs. `policyholders.nic` is deliberately non-unique in the C2 schema, so the
duplicate loads cleanly; Silver (Phase 05) deduplicates on `nic`.

FIXED, not percentage: the count is read from `config.FIXED` and never multiplied by
`--scale`. A `--scale 0.02` run still injects exactly 50 duplicate rows - 50 orphan/duplicate
edge events are a realistic post-acquisition reality whether the book is 1K or 50K.

A "pair" = one original baseline policyholder + one injected duplicate sharing its NIC. The
self-assertion counts NICs that appear under >=2 distinct policyholder_ids; this scenario makes
exactly 50 such NICs (the originals are unique in S01, so each injection creates exactly one
new duplicate NIC).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seed.config import FIXED
from seed.model import Policyholder

if TYPE_CHECKING:
    import random

    from seed.config import GenConfig
    from seed.model import Dataset


def build(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Append exactly 50 duplicate-NIC policyholder rows (scale-invariant)."""
    _ = cfg  # count is fixed - intentionally independent of --scale
    if not dataset.policyholders:
        msg = "S02 requires S01 to have built policyholders first"
        raise RuntimeError(msg)

    n_pairs = FIXED.s02_duplicate_nic_pairs
    # Sample distinct originals deterministically so each injection duplicates a unique NIC.
    originals = rng.sample(dataset.policyholders, k=n_pairs)
    ph_ids = dataset.allocator("policyholders")
    for original in originals:
        new_id = ph_ids.take()
        # Same NIC + name (the merge signal); other attributes may differ slightly, exactly
        # as a re-keyed record from an acquired system would.
        dataset.policyholders.append(
            Policyholder(
                policyholder_id=new_id,
                nic=original.nic,
                full_name=original.full_name,
                dob=original.dob,
                gender=original.gender,
                email=original.email,
                phone=original.phone,
                address=f"{rng.randint(1, 999)} Legacy Ave",  # acquired-system address variant
                city=original.city,
                customer_tier=original.customer_tier,
            ),
        )
