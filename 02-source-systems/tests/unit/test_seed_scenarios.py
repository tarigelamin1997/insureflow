"""Seed-self assertions for the Phase 02 scenario generator (S01-S05).

These run against the in-memory `Dataset` the generator builds - NO Docker, NO psql, NO file
load. They validate the seed itself (per procedures/seed-data.md -> Assertion standard):
row-count invariants, intra-seed FK integrity, the deliberate-edge counts (S02=50, S03=30),
the S04 date-format mix, the S05 currency mix, the fixed-vs-scale behaviour, and determinism.

The generator package lives at `02-source-systems/seed`; conftest.py adds that directory to
sys.path so `import seed...` resolves (the package dir name `02-source-systems` is not a legal
dotted-module path).
"""

from __future__ import annotations

import pytest
from seed.builder import (
    build_dataset,
    count_duplicate_nic_pairs,
    count_orphan_claims,
)
from seed.config import GenConfig, make_rng
from seed.registry import REGISTRY, resolve
from seed.sql import INSTANCES, render_instance

_DQ_SCENARIOS = ["S01", "S02", "S03", "S04", "S05"]
_EXPECTED_DUP_PAIRS = 50
_EXPECTED_ORPHANS = 30


def _cfg(scale: float = 0.02, seed: int = 42) -> GenConfig:
    """Build a config for the default DQ scenario set at a given scale/seed."""
    return GenConfig(scenarios=list(_DQ_SCENARIOS), scale=scale, seed=seed)


# --- S02: exactly 50 duplicate-NIC pairs, fixed under --scale --------------------------


def test_s02_duplicate_nic_pairs_exactly_50_at_ci_scale() -> None:
    """S02 injects exactly 50 duplicate-NIC pairs at the CI scale (0.02)."""
    ds = build_dataset(_cfg(scale=0.02))
    assert count_duplicate_nic_pairs(ds) == _EXPECTED_DUP_PAIRS


def test_s02_duplicate_nic_pairs_exactly_50_at_full_scale() -> None:
    """S02 count is invariant under --scale: still 50 at scale 1.0 (fixed-absolute)."""
    ds = build_dataset(_cfg(scale=1.0))
    assert count_duplicate_nic_pairs(ds) == _EXPECTED_DUP_PAIRS


def test_s02_disabled_yields_zero_pairs() -> None:
    """Negative case: without S02 there are no duplicate-NIC pairs."""
    ds = build_dataset(GenConfig(scenarios=["S01"], scale=0.02, seed=42))
    assert count_duplicate_nic_pairs(ds) == 0


# --- S03: exactly 30 orphan claims, fixed under --scale --------------------------------


def test_s03_orphan_claims_exactly_30_at_ci_scale() -> None:
    """S03 injects exactly 30 orphan claims at the CI scale (0.02)."""
    ds = build_dataset(_cfg(scale=0.02))
    assert count_orphan_claims(ds) == _EXPECTED_ORPHANS


def test_s03_orphan_claims_exactly_30_at_full_scale() -> None:
    """S03 count is invariant under --scale: still 30 at scale 1.0 (fixed-absolute)."""
    ds = build_dataset(_cfg(scale=1.0))
    assert count_orphan_claims(ds) == _EXPECTED_ORPHANS


def test_s03_disabled_yields_zero_orphans() -> None:
    """Negative case: without S03 every claim references a real policy."""
    ds = build_dataset(GenConfig(scenarios=["S01"], scale=0.02, seed=42))
    assert count_orphan_claims(ds) == 0


# --- Intra-seed FK integrity ----------------------------------------------------------


def test_non_orphan_claims_reference_real_policies() -> None:
    """Every non-orphan claim's policy_id exists in policies."""
    ds = build_dataset(_cfg())
    policy_ids = {p.policy_id for p in ds.policies}
    non_orphan = [
        c for c in ds.claims if c.claim_number is not None and "ORPH" not in c.claim_number
    ]
    assert non_orphan, "expected baseline claims to exist"
    assert all(c.policy_id in policy_ids for c in non_orphan)


def test_pms_child_tables_reference_real_policies() -> None:
    """Every endorsement / renewal / cancellation references a real policy."""
    ds = build_dataset(_cfg())
    policy_ids = {p.policy_id for p in ds.policies}
    for rows in (ds.endorsements, ds.renewals, ds.cancellations):
        assert rows, "expected child rows to exist"
        assert all(r.policy_id in policy_ids for r in rows)


def test_cms_child_tables_reference_real_claims() -> None:
    """Every assessment / settlement / reserve / event / third-party references a claim."""
    ds = build_dataset(_cfg())
    claim_ids = {c.claim_id for c in ds.claims}
    for rows in (
        ds.claim_events,
        ds.assessments,
        ds.settlements,
        ds.reserves,
        ds.third_party_details,
    ):
        assert rows, "expected CMS child rows to exist"
        assert all(r.claim_id in claim_ids for r in rows)


def test_gl_settlement_fk_resolves_when_present() -> None:
    """The one intra-PFS FK (gl_settlements -> premium_transactions) resolves when set."""
    ds = build_dataset(_cfg())
    txn_ids = {t.transaction_id for t in ds.premium_transactions}
    linked = [g for g in ds.gl_settlements if g.transaction_id is not None]
    assert all(g.transaction_id in txn_ids for g in linked)


# --- No NULL primary keys -------------------------------------------------------------


def test_no_null_primary_keys_across_all_tables() -> None:
    """Zero NULL primary keys across all 17 tables."""
    ds = build_dataset(_cfg())
    pk_by_table = {
        "agents": "agent_id",
        "products": "product_id",
        "policyholders": "policyholder_id",
        "policies": "policy_id",
        "endorsements": "endorsement_id",
        "renewals": "renewal_id",
        "cancellations": "cancellation_id",
        "claims": "claim_id",
        "claim_events": "claim_event_id",
        "assessments": "assessment_id",
        "settlements": "settlement_id",
        "reserves": "reserve_id",
        "third_party_details": "third_party_id",
        "premium_transactions": "transaction_id",
        "reinsurance_entries": "reinsurance_id",
        "gl_settlements": "gl_settlement_id",
        "ifrs17_data": "ifrs17_id",
    }
    assert len(pk_by_table) == 17  # noqa: PLR2004 - the platform's 17-table contract
    for table, pk in pk_by_table.items():
        rows = getattr(ds, table)
        assert all(getattr(r, pk) is not None for r in rows), f"NULL PK in {table}"


# --- S04: both date formats present ---------------------------------------------------


def test_s04_produces_both_date_formats() -> None:
    """S04 yields both ISO-8601 (-) and legacy DD/MM/YYYY (/) dob values."""
    ds = build_dataset(_cfg())
    dobs = [p.dob for p in ds.policyholders if p.dob is not None]
    has_iso = any("-" in d for d in dobs)
    has_legacy = any("/" in d for d in dobs)
    assert has_iso, "expected some ISO-8601 dates"
    assert has_legacy, "expected some legacy DD/MM/YYYY dates"


def test_s04_disabled_yields_only_iso() -> None:
    """Negative case: without S04 all dates remain ISO-8601 (no slashes)."""
    ds = build_dataset(GenConfig(scenarios=["S01"], scale=0.02, seed=42))
    dobs = [p.dob for p in ds.policyholders if p.dob is not None]
    assert all("/" not in d for d in dobs)


# --- S05: both currencies present -----------------------------------------------------


def test_s05_produces_both_currencies() -> None:
    """S05 yields USD and SAR premium transactions, plus some NULL (=> SAR)."""
    ds = build_dataset(_cfg())
    currencies = {t.currency for t in ds.premium_transactions}
    assert "USD" in currencies
    assert "SAR" in currencies
    assert None in currencies


def test_s05_disabled_yields_only_sar() -> None:
    """Negative case: without S05 every premium transaction is SAR."""
    ds = build_dataset(GenConfig(scenarios=["S01"], scale=0.02, seed=42))
    assert {t.currency for t in ds.premium_transactions} == {"SAR"}


# --- Fixed-vs-scale behaviour ---------------------------------------------------------


def test_percentage_volumes_scale_but_fixed_injections_do_not() -> None:
    """Baseline row counts scale with --scale; S02/S03 injections stay constant."""
    small = build_dataset(_cfg(scale=0.02))
    large = build_dataset(_cfg(scale=0.1))
    # Percentage-based population grows with scale.
    assert len(large.policyholders) > len(small.policyholders)
    assert len(large.premium_transactions) > len(small.premium_transactions)
    # Fixed-absolute injections are identical at both scales.
    assert count_duplicate_nic_pairs(small) == count_duplicate_nic_pairs(large)
    assert count_orphan_claims(small) == count_orphan_claims(large)


# --- Determinism ----------------------------------------------------------------------


def test_same_seed_yields_identical_sql() -> None:
    """A fixed seed produces byte-identical SQL for every instance."""
    cfg = _cfg()
    ds1 = build_dataset(cfg)
    ds2 = build_dataset(_cfg())
    for instance in INSTANCES:
        sql1 = render_instance(
            instance,
            ds1,
            scenarios=_DQ_SCENARIOS,
            scale=cfg.scale,
            seed=cfg.seed,
        )
        sql2 = render_instance(
            instance,
            ds2,
            scenarios=_DQ_SCENARIOS,
            scale=cfg.scale,
            seed=cfg.seed,
        )
        assert sql1 == sql2, f"non-deterministic SQL for {instance}"


def test_different_seed_changes_output() -> None:
    """A different seed produces different data (the seed actually drives variety)."""
    ds_a = build_dataset(GenConfig(scenarios=_DQ_SCENARIOS, scale=0.02, seed=42))
    ds_b = build_dataset(GenConfig(scenarios=_DQ_SCENARIOS, scale=0.02, seed=7))
    nics_a = [p.nic for p in ds_a.policyholders]
    nics_b = [p.nic for p in ds_b.policyholders]
    assert nics_a != nics_b


# --- Registry / scope -----------------------------------------------------------------


def test_all_expands_to_implemented_only() -> None:
    """`--scenarios all` resolves to the implemented set, not the deferred ones."""
    assert resolve(["all"]) == list(_DQ_SCENARIOS)


def test_deferred_scenarios_raise_not_implemented() -> None:
    """S06-S12 are architected but raise NotImplementedError if invoked."""
    cfg = GenConfig(scenarios=["S06"], scale=0.02, seed=42)
    baseline = build_dataset(GenConfig(scenarios=["S01"], scale=0.02, seed=42))
    rng = make_rng(42)
    with pytest.raises(NotImplementedError, match="S06"):
        REGISTRY["S06"](baseline, cfg, rng)
