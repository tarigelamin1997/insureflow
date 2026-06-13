"""S03 - Orphan claims (FIXED-ABSOLUTE injection, scale-invariant).

Injects exactly `FIXED.s03_orphan_claims` (= 30) additional claim rows whose `policy_id`
references a policy that does NOT exist in PMS - claims from the acquired entity whose policies
were never migrated. `claims.policy_id` is a plain cross-instance column with NO foreign key
(PMS is a separate Postgres instance, ADR-002), so the orphan loads cleanly; Gold (Phase 06)
referential-integrity checks catch and exclude them.

FIXED, not percentage: the count is read from `config.FIXED` and never multiplied by
`--scale`. A `--scale 0.02` run still injects exactly 30 orphans.

Orphan `policy_id` values are allocated from a high, reserved band (`_ORPHAN_POLICY_BASE`)
that the baseline policy allocator never reaches, so an orphan can never accidentally match a
real policy_id at any scale. The orphan band is deterministic (no RNG), so the orphan policy
references are byte-stable across runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seed import fields as fx
from seed.config import FIXED
from seed.model import Claim

if TYPE_CHECKING:
    import random

    from seed.config import GenConfig
    from seed.model import Dataset

# Reserved high band for non-existent policy references. The baseline policy allocator starts
# at 1 and the full-scale baseline tops out at 80K, so 9_000_000_001+ can never collide.
_ORPHAN_POLICY_BASE = 9_000_000_000
_ORPHAN_HOLDER_BASE = 9_500_000_000


def build(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Append exactly 30 orphan claims (policy_id matches no policy; scale-invariant)."""
    _ = cfg  # count is fixed - intentionally independent of --scale
    n_orphans = FIXED.s03_orphan_claims
    cl_ids = dataset.allocator("claims")
    for k in range(n_orphans):
        clid = cl_ids.take()
        loss = fx.random_date(rng, 2020, 2022)
        dataset.claims.append(
            Claim(
                claim_id=clid,
                claim_number=f"CLM-ORPH-{clid:08d}",
                policy_id=_ORPHAN_POLICY_BASE + k + 1,  # never-allocated policy -> orphan
                policyholder_id=_ORPHAN_HOLDER_BASE + k + 1,
                loss_date=fx.iso_date(loss),
                report_date=fx.iso_date(loss),
                claim_amount=fx.money(rng, 1_000, 300_000),
                claim_type=rng.choice(("collision", "theft", "medical", "fire")),
                status=rng.choice(fx.CLAIM_STATUS),
            ),
        )
