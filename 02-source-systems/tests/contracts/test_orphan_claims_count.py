"""Fitness function: exactly 30 orphan claims exist in the seeded CMS data (scenario S03).

Property: an orphan claim is a `claims` row whose `policy_id` has no matching row in PMS
          `policies`. The S03 scenario injects exactly 30 such orphans on top of the S01
          baseline (per procedures/seed-data.md). This is the known-answer fixture that
          Phase 06 referential-integrity gates depend on.
Phase: 02 — Source Systems
Fails when: the injected orphan count drifts from 30, S03 is disabled, or every claim is made
            to reference a valid policy.
Negative case: regenerate the seed with S03 disabled → the count ≠ 30 → this test fails.

STUB — implemented before /review-phase. xfail until the seed generator and DBs exist.
"""

import pytest


@pytest.mark.xfail(reason="STUB — implemented after schema + seed land (Chunk 2+)", strict=True)
def test_orphan_claims_count_is_exactly_30() -> None:
    """Exactly 30 claims reference a non-existent policy_id after S01-S05 load."""
    msg = "Phase 02 implementation pending"
    raise NotImplementedError(msg)
