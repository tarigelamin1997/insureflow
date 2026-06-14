"""Fitness function: zero NULL primary keys across all 17 source tables.

Property: every table in PMS (7), CMS (6), and PFS (4) has a NOT-NULL primary key, and no
          seeded row carries a NULL PK. NULL PKs at the source break keying in Bronze/Silver and
          every FK join in Gold.
Phase: 02 — Source Systems
Fails when: a PK column is made nullable, a PK constraint is dropped, or a NULL-PK row is
            seeded.
Negative case: inject a NULL-PK fixture row (only possible after dropping the PK NOT-NULL
               constraint) → the per-table count > 0 → the summed total > 0 → this test fails.

Behavioral: counts NULL PKs in the LIVE tables. Skips (does not pass) when no DB is reachable —
see conftest. The (table, pk) map below mirrors schema/{pms,cms,pfs}/01-schema.sql exactly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from psycopg import sql

if TYPE_CHECKING:
    import psycopg

# (table, primary-key column) for every one of the 17 tables, grouped by instance.
# Source of truth: 02-source-systems/schema/{pms,cms,pfs}/01-schema.sql.
PK_BY_INSTANCE: dict[str, tuple[tuple[str, str], ...]] = {
    "pms": (
        ("agents", "agent_id"),
        ("products", "product_id"),
        ("policyholders", "policyholder_id"),
        ("policies", "policy_id"),
        ("endorsements", "endorsement_id"),
        ("renewals", "renewal_id"),
        ("cancellations", "cancellation_id"),
    ),
    "cms": (
        ("claims", "claim_id"),
        ("claim_events", "claim_event_id"),
        ("assessments", "assessment_id"),
        ("settlements", "settlement_id"),
        ("reserves", "reserve_id"),
        ("third_party_details", "third_party_id"),
    ),
    "pfs": (
        ("premium_transactions", "transaction_id"),
        ("reinsurance_entries", "reinsurance_id"),
        ("gl_settlements", "gl_settlement_id"),
        ("ifrs17_data", "ifrs17_id"),
    ),
}

_EXPECTED_TABLE_COUNT = 17


def _null_pk_count(conn: psycopg.Connection, table: str, pk: str) -> int:
    """Count rows in `table` whose primary-key column `pk` IS NULL.

    Identifiers come from PK_BY_INSTANCE (a fixed, in-repo constant mirroring the DDL), never
    from external input. They are composed with psycopg.sql.Identifier — the canonical safe
    identifier-quoting path — so there is no string interpolation into the statement at all.
    """
    query = sql.SQL("SELECT count(*) FROM {table} WHERE {pk} IS NULL").format(
        table=sql.Identifier(table),
        pk=sql.Identifier(pk),
    )
    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()
    assert row is not None, f"{table}: count query returned no row"
    return int(row[0])


def test_table_map_covers_all_seventeen() -> None:
    """The (table, pk) map covers exactly 17 tables (runs even with no DB up)."""
    total = sum(len(v) for v in PK_BY_INSTANCE.values())
    assert total == _EXPECTED_TABLE_COUNT, (
        f"PK map covers {total} tables, expected {_EXPECTED_TABLE_COUNT} — it must mirror the "
        f"17 schema tables exactly."
    )


def test_no_null_primary_keys_across_all_tables(
    all_conns: dict[str, psycopg.Connection],
) -> None:
    """Aggregate count of NULL primary keys across all 17 tables is 0."""
    offenders: list[str] = []
    grand_total = 0
    for system, tables in PK_BY_INSTANCE.items():
        conn = all_conns[system]
        for table, pk in tables:
            n = _null_pk_count(conn, table, pk)
            grand_total += n
            if n:
                offenders.append(f"{system}.{table}.{pk}={n}")
    assert grand_total == 0, (
        f"found {grand_total} NULL primary key(s) across the 17 source tables: "
        f"{', '.join(offenders)} — a NULL PK breaks Bronze/Silver keying and every Gold FK join "
        f"(negative case: drop a PK NOT-NULL constraint and insert a NULL-PK row)."
    )
