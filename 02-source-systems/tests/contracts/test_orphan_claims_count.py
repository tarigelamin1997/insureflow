"""Fitness function: exactly 30 orphan claims exist in the seeded CMS data (scenario S03).

Property: an orphan claim is a CMS `claims` row whose non-NULL `policy_id` has no matching row
          in PMS `policies`. PMS and CMS are SEPARATE Postgres instances (ADR-002), so there is
          no foreign key and no single-database join can answer this — the set difference is
          computed in Python across two live connections. S03 injects exactly 30 such orphans
          (policy_id allocated from a reserved high band the baseline never reaches) on top of
          the S01 baseline (per procedures/seed-data.md and
          seed/scenarios/s03_orphan_claims.py). This is the known-answer fixture Phase 06
          referential-integrity gates depend on.
Phase: 02 — Source Systems
Fails when: the injected orphan count drifts from 30, S03 is disabled, or every claim is made
            to reference a valid policy.
Negative case: regenerate the seed with S03 disabled (or its count perturbed) → the cross-
               instance orphan count ≠ 30 → this test fails. (Equivalently: migrate the missing
               policies into PMS so every claim resolves → count drops to 0.)

Behavioral: reads real rows from BOTH live instances and computes the difference. Skips (does
not pass) when either instance is unreachable — see conftest. This is the only contract test
that proves the cross-instance gap is real, not an enforceable FK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg

_EXPECTED_ORPHAN_CLAIMS = 30


def _pms_policy_ids(pms_conn: psycopg.Connection) -> set[int]:
    """All policy_id values that exist in PMS (the authoritative policy universe)."""
    with pms_conn.cursor() as cur:
        cur.execute("SELECT policy_id FROM policies")
        return {int(row[0]) for row in cur.fetchall()}


def _cms_claim_policy_refs(cms_conn: psycopg.Connection) -> list[int]:
    """policy_id of every CMS claim that references a policy (non-NULL refs only).

    A NULL policy_id is a claim with no policy reference at all — not an orphan of a *missing*
    policy — so it is excluded, matching the S03 definition (an orphan carries a concrete
    policy_id that simply does not exist in PMS).
    """
    with cms_conn.cursor() as cur:
        cur.execute("SELECT policy_id FROM claims WHERE policy_id IS NOT NULL")
        return [int(row[0]) for row in cur.fetchall()]


def test_orphan_claims_count_is_exactly_30(
    pms_conn: psycopg.Connection,
    cms_conn: psycopg.Connection,
) -> None:
    """Exactly 30 CMS claims reference a policy_id absent from PMS (cross-instance set diff)."""
    pms_policy_ids = _pms_policy_ids(pms_conn)
    claim_refs = _cms_claim_policy_refs(cms_conn)

    orphans = [pid for pid in claim_refs if pid not in pms_policy_ids]
    orphan_count = len(orphans)

    assert orphan_count == _EXPECTED_ORPHAN_CLAIMS, (
        f"found {orphan_count} orphan claim(s) (CMS claims whose policy_id is absent from PMS "
        f"policies), expected exactly {_EXPECTED_ORPHAN_CLAIMS} (scenario S03). PMS has "
        f"{len(pms_policy_ids)} policies; {len(claim_refs)} claims carry a policy_id. Drift here "
        f"means the Phase 06 referential-integrity fixture is wrong (negative case: load the "
        f"seed with S03 disabled → orphans ≠ 30)."
    )
