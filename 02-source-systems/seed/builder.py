"""Pure dataset assembly - the importable core the CLI and the unit tests share.

`build_dataset(cfg)` returns a fully-populated `Dataset` for a config, with scenarios applied
in registry order through the single seeded RNG. It performs no I/O, so the self-assertion
tests call it directly (no Docker, no psql, no file writes) and the CLI calls it before
serialising. `assert_seed_self_consistency` encodes the seed-self invariants from
`procedures/seed-data.md` so both the CLI (fail-fast before writing SQL) and the tests share
one source of truth.
"""

from __future__ import annotations

from seed.config import GenConfig, make_rng
from seed.model import Dataset
from seed.registry import IMPLEMENTED, resolve
from seed.registry import REGISTRY as _REGISTRY


def build_dataset(cfg: GenConfig) -> Dataset:
    """Assemble the full in-memory dataset for `cfg`, applying scenarios in registry order."""
    ordered = resolve(cfg.scenarios)
    rng = make_rng(cfg.seed)
    dataset = Dataset()
    for scenario_id in ordered:
        _REGISTRY[scenario_id](dataset, cfg, rng)
    return dataset


def count_duplicate_nic_pairs(dataset: Dataset) -> int:
    """Count NIC values that appear under two or more distinct policyholder_ids."""
    by_nic: dict[str, set[int]] = {}
    for ph in dataset.policyholders:
        by_nic.setdefault(ph.nic, set()).add(ph.policyholder_id)
    return sum(1 for ids in by_nic.values() if len(ids) >= 2)  # noqa: PLR2004


def count_orphan_claims(dataset: Dataset) -> int:
    """Count claims whose policy_id matches no policy in the seed."""
    valid_policy_ids = {p.policy_id for p in dataset.policies}
    return sum(
        1 for c in dataset.claims if c.policy_id is not None and c.policy_id not in valid_policy_ids
    )


def assert_seed_self_consistency(dataset: Dataset, scenarios: list[str]) -> None:
    """Assert the seed-self invariants from procedures/seed-data.md.

    Raises AssertionError on any violation. Shared by the CLI (fail-fast) and the unit tests.
    Scenario-specific count checks fire only when that scenario is in the requested set.
    """
    active = {s.strip().upper() for s in scenarios}
    if scenarios == ["all"]:
        active = set(IMPLEMENTED)

    # No NULL primary keys anywhere (mirrors VG4 / test_no_null_pks at the seed level).
    _assert_no_null_pks(dataset)

    # Intra-seed FK integrity: every non-orphan claim's policy_id resolves; every PMS child
    # references a real parent; the one intra-PFS FK resolves.
    _assert_fk_integrity(dataset)

    if "S02" in active:
        pairs = count_duplicate_nic_pairs(dataset)
        expected = 50
        if pairs != expected:
            msg = f"S02 invariant: expected {expected} duplicate-NIC pairs, got {pairs}"
            raise AssertionError(msg)

    if "S03" in active:
        orphans = count_orphan_claims(dataset)
        expected = 30
        if orphans != expected:
            msg = f"S03 invariant: expected {expected} orphan claims, got {orphans}"
            raise AssertionError(msg)


def _assert_no_null_pks(dataset: Dataset) -> None:
    """No surrogate PK is None across all 17 tables."""
    pk_specs: list[tuple[str, str]] = [
        ("agents", "agent_id"),
        ("products", "product_id"),
        ("policyholders", "policyholder_id"),
        ("policies", "policy_id"),
        ("endorsements", "endorsement_id"),
        ("renewals", "renewal_id"),
        ("cancellations", "cancellation_id"),
        ("claims", "claim_id"),
        ("claim_events", "claim_event_id"),
        ("assessments", "assessment_id"),
        ("settlements", "settlement_id"),
        ("reserves", "reserve_id"),
        ("third_party_details", "third_party_id"),
        ("premium_transactions", "transaction_id"),
        ("reinsurance_entries", "reinsurance_id"),
        ("gl_settlements", "gl_settlement_id"),
        ("ifrs17_data", "ifrs17_id"),
    ]
    for table, pk in pk_specs:
        for row in getattr(dataset, table):
            if getattr(row, pk) is None:
                msg = f"NULL primary key found in {table}.{pk}"
                raise AssertionError(msg)


def _assert_child_fks(
    dataset: Dataset,
    table_fks: tuple[tuple[str, str], ...],
    parent_ids: set[int],
    parent_label: str,
) -> None:
    """Assert each (table, fk) child column resolves into `parent_ids`."""
    for table, fk in table_fks:
        for row in getattr(dataset, table):
            value = getattr(row, fk)
            if value not in parent_ids:
                msg = f"{table}.{fk} {value} has no {parent_label}"
                raise AssertionError(msg)


def _assert_policy_parents(dataset: Dataset) -> None:
    """Assert every policy's policyholder / product / agent reference resolves."""
    holder_ids = {h.policyholder_id for h in dataset.policyholders}
    product_ids = {p.product_id for p in dataset.products}
    agent_ids = {a.agent_id for a in dataset.agents}
    for pol in dataset.policies:
        if pol.policyholder_id not in holder_ids:
            msg = f"policies.policyholder_id {pol.policyholder_id} has no policyholder"
            raise AssertionError(msg)
        if pol.product_id not in product_ids:
            msg = f"policies.product_id {pol.product_id} has no product"
            raise AssertionError(msg)
        if pol.agent_id is not None and pol.agent_id not in agent_ids:
            msg = f"policies.agent_id {pol.agent_id} has no agent"
            raise AssertionError(msg)


def _assert_gl_fk(dataset: Dataset) -> None:
    """Assert the one intra-PFS FK (gl_settlements -> premium_transactions) resolves."""
    txn_ids = {t.transaction_id for t in dataset.premium_transactions}
    for gl in dataset.gl_settlements:
        if gl.transaction_id is not None and gl.transaction_id not in txn_ids:
            msg = f"gl_settlements.transaction_id {gl.transaction_id} has no transaction"
            raise AssertionError(msg)


def _assert_fk_integrity(dataset: Dataset) -> None:
    """Intra-seed referential integrity holds for non-orphan references."""
    policy_ids = {p.policy_id for p in dataset.policies}
    claim_ids = {c.claim_id for c in dataset.claims}
    _assert_policy_parents(dataset)
    _assert_child_fks(
        dataset,
        (("endorsements", "policy_id"), ("renewals", "policy_id"), ("cancellations", "policy_id")),
        policy_ids,
        "policy",
    )
    _assert_child_fks(
        dataset,
        (
            ("claim_events", "claim_id"),
            ("assessments", "claim_id"),
            ("settlements", "claim_id"),
            ("reserves", "claim_id"),
            ("third_party_details", "claim_id"),
        ),
        claim_ids,
        "claim",
    )
    _assert_gl_fk(dataset)
