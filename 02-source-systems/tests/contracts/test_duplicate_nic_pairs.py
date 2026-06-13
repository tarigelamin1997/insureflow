"""Fitness function: exactly 50 duplicate-NIC policyholder pairs exist (scenario S02).

Property: S02 injects 50 policyholders that appear twice in PMS with the same NIC but
          different `policyholder_id` values — the post-acquisition merge reality
          (per procedures/seed-data.md). This is the known-answer fixture Phase 05
          deduplication and Phase 06 SCD Type 2 gates depend on.
Phase: 02 — Source Systems
Fails when: the injected pair count drifts from 50, S02 is disabled, or the source is
            deduplicated before CDC.
Negative case: regenerate the seed with S02 disabled → pairs ≠ 50 → this test fails.

STUB — implemented before /review-phase. xfail until the seed generator and DBs exist.
"""

import pytest


@pytest.mark.xfail(reason="STUB — implemented after schema + seed land (Chunk 2+)", strict=True)
def test_duplicate_nic_pairs_is_exactly_50() -> None:
    """Exactly 50 NIC values appear under two distinct policyholder_id values."""
    msg = "Phase 02 implementation pending"
    raise NotImplementedError(msg)
