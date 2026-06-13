"""Fitness function: zero NULL primary keys across all 17 source tables.

Property: every table in PMS (7), CMS (6), and PFS (4) has a NOT-NULL primary key, and no
          seeded row carries a NULL PK. NULL PKs at the source break keying in Bronze/Silver
          and every FK join in Gold.
Phase: 02 — Source Systems
Fails when: a PK column is made nullable, a PK constraint is dropped, or a NULL-PK row is
            seeded.
Negative case: inject a NULL-PK fixture row (or drop the PK constraint) → the aggregate count
               of NULL PKs > 0 → this test fails.

STUB — implemented before /review-phase. xfail until the schema + DBs exist.
"""

import pytest


@pytest.mark.xfail(reason="STUB — implemented after schema + seed land (Chunk 2+)", strict=True)
def test_no_null_primary_keys_across_all_tables() -> None:
    """Aggregate count of NULL primary keys across all 17 tables is 0."""
    msg = "Phase 02 implementation pending"
    raise NotImplementedError(msg)
