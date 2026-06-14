"""Fitness function: exactly 50 duplicate-NIC policyholder pairs exist (scenario S02).

Property: S02 injects 50 extra policyholders that reuse an existing NIC under a NEW
          `policyholder_id` — the post-acquisition merge reality (per procedures/seed-data.md
          and seed/scenarios/s02_duplicate_policyholders.py). Because S01 originals are unique
          on NIC, each injection creates exactly one NIC that appears under >= 2 distinct
          policyholder_id values. A "pair" is one such duplicated NIC. This is the known-answer
          fixture Phase 05 deduplication and Phase 06 SCD Type 2 gates depend on.
Phase: 02 — Source Systems
Fails when: the injected pair count drifts from 50, S02 is disabled, or the source is
            deduplicated before CDC.
Negative case: regenerate the seed with S02 disabled (or its count perturbed) → the count of
               NICs appearing under >= 2 policyholder_ids ≠ 50 → this test fails.

Behavioral: counts duplicate NICs in the LIVE postgres-pms table. Skips (does not pass) when no
DB is reachable — see conftest. Mirrors the seed-self assertion in tests/unit, but against the
loaded database rather than the in-memory dataset.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg

_EXPECTED_DUPLICATE_NIC_PAIRS = 50

# A "duplicate-NIC pair" = a nic value carried by >= 2 distinct policyholder_id rows. Counting
# the number of such nic values is exactly the seed's S02 pair definition (each of the 50
# injections duplicates one previously-unique NIC).
_DUPLICATE_NIC_PAIR_SQL = """
SELECT count(*) FROM (
    SELECT nic
    FROM policyholders
    GROUP BY nic
    HAVING count(DISTINCT policyholder_id) > 1
) AS duplicated_nics
"""


def test_duplicate_nic_pairs_is_exactly_50(pms_conn: psycopg.Connection) -> None:
    """Exactly 50 NIC values appear under two or more distinct policyholder_id values."""
    with pms_conn.cursor() as cur:
        cur.execute(_DUPLICATE_NIC_PAIR_SQL)
        row = cur.fetchone()
    assert row is not None, "duplicate-NIC count query returned no row"
    pairs = int(row[0])
    assert pairs == _EXPECTED_DUPLICATE_NIC_PAIRS, (
        f"found {pairs} duplicate-NIC pair(s) in postgres-pms.policyholders, expected exactly "
        f"{_EXPECTED_DUPLICATE_NIC_PAIRS} (scenario S02) — drift here means the Phase 05 dedup "
        f"fixture is wrong (negative case: load the seed with S02 disabled → pairs ≠ 50)."
    )
