"""Fitness function: logical-replication CDC config is active on every source DB.

Property: each of postgres-pms / postgres-cms / postgres-pfs runs with wal_level=logical,
          max_wal_senders >= 3, max_replication_slots >= 3, and exposes a role with
          rolreplication = true. Asserted against the LIVE engine via pg_settings / pg_roles —
          NOT by reading a .conf file on disk (a file can say `logical` while the running
          server is `replica`).
Phase: 02 — Source Systems
Fails when: wal_level is replica/minimal, senders or slots drop below 3, or the replication
            role is missing / lacks rolreplication.
Negative case: start a DB with the default (`replica`) WAL config, or DROP the replication
               role / remove its REPLICATION attribute → the corresponding assertion below
               goes red. (This file inspects the running server, so flipping the on-disk
               `postgresql.conf` without a restart would NOT mask the failure — exactly the
               point of asserting the live engine.)

Behavioral: queries the running engine. Skips (does not pass) when no DB is reachable — see
conftest. The proof runs against the live stack at phase close.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conftest import INSTANCES, dsn_for, replication_role_name

if TYPE_CHECKING:
    from collections.abc import Sequence

    import psycopg

_MIN_SENDERS_SLOTS = 3


def _scalar(conn: psycopg.Connection, sql: str, params: Sequence[object] = ()) -> object:
    """Run a single-value query and return the first column of the first row."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    assert row is not None, f"expected one row from: {sql}"
    return row[0]


@pytest.mark.parametrize("system", INSTANCES)
def test_wal_level_is_logical(all_conns: dict[str, psycopg.Connection], system: str) -> None:
    """Each source instance reports wal_level=logical on the live engine."""
    wal_level = _scalar(all_conns[system], "SHOW wal_level")
    assert wal_level == "logical", (
        f"postgres-{system}: wal_level is {wal_level!r}, expected 'logical' — Debezium logical "
        f"decoding cannot start without it (VG2 negative case: a DB started with the default "
        f"'replica' fails here)."
    )


@pytest.mark.parametrize("setting", ["max_wal_senders", "max_replication_slots"])
def test_replication_budget_at_least_three(
    all_conns: dict[str, psycopg.Connection],
    setting: str,
) -> None:
    """max_wal_senders and max_replication_slots are >= 3 on every instance."""
    for system in INSTANCES:
        value = int(
            str(
                _scalar(
                    all_conns[system],
                    "SELECT setting FROM pg_settings WHERE name = %s",
                    (setting,),
                ),
            ),
        )
        assert value >= _MIN_SENDERS_SLOTS, (
            f"postgres-{system}: {setting} is {value}, expected >= {_MIN_SENDERS_SLOTS} — "
            f"too few would starve Phase 03 CDC slots (negative case: drop the GUC below 3)."
        )


@pytest.mark.parametrize("system", INSTANCES)
def test_replication_role_present(
    all_conns: dict[str, psycopg.Connection],
    system: str,
) -> None:
    """A role with rolreplication = true exists on every instance (the Debezium login)."""
    role = replication_role_name()
    rolrepl = _scalar(
        all_conns[system],
        "SELECT rolreplication FROM pg_roles WHERE rolname = %s",
        (role,),
    )
    assert rolrepl is True, (
        f"postgres-{system}: role {role!r} is missing or lacks REPLICATION "
        f"(rolreplication={rolrepl!r}) — Phase 03 Debezium logs in as this role (negative case: "
        f"DROP ROLE or ALTER ROLE … NOREPLICATION)."
    )


@pytest.mark.parametrize("system", INSTANCES)
def test_logical_slot_can_be_created_and_dropped(
    all_conns: dict[str, psycopg.Connection],
    system: str,
) -> None:
    """A logical replication slot can be created and dropped — the end-to-end CDC capability.

    This is the strongest behavioral proof: it exercises logical decoding itself, which only
    works when wal_level=logical AND a slot budget is free. A server on wal_level=replica
    errors on slot creation (negative case), turning this red.
    """
    conn = all_conns[system]
    slot = f"insureflow_fitness_probe_{system}"
    with conn.cursor() as cur:
        # Defensive cleanup in case a prior aborted run left the probe slot behind.
        cur.execute(
            "SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots "
            "WHERE slot_name = %s",
            (slot,),
        )
        cur.execute("SELECT pg_create_logical_replication_slot(%s, 'pgoutput')", (slot,))
        created = cur.fetchone()
        assert created is not None, f"postgres-{system}: logical slot creation returned no row"
        cur.execute(
            "SELECT count(*) FROM pg_replication_slots WHERE slot_name = %s AND slot_type = "
            "'logical'",
            (slot,),
        )
        present = cur.fetchone()
        assert present is not None, f"postgres-{system}: slot-presence query returned no row"
        assert (
            present[0] == 1
        ), f"postgres-{system}: logical slot {slot!r} was not registered as active"
        cur.execute("SELECT pg_drop_replication_slot(%s)", (slot,))
    conn.commit()


def test_env_dsn_resolves_without_db() -> None:
    """dsn_for resolves a complete spec from env/defaults (runs even with no DB up).

    Guards the conftest plumbing: a typo in an env-var name would surface here rather than as a
    confusing skip. Pure config resolution — no connection attempted.
    """
    for system in INSTANCES:
        spec = dsn_for(system)
        missing = [
            field for field in ("host", "port", "user", "dbname") if not getattr(spec, field)
        ]
        assert not missing, f"incomplete DSN for {system}: missing {missing} in {spec!r}"
