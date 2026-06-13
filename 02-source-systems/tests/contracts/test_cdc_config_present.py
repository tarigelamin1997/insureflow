"""Fitness function: logical-replication CDC config is active on every source DB.

Property: each of postgres-pms / postgres-cms / postgres-pfs runs with wal_level=logical,
          max_wal_senders >= 3, max_replication_slots >= 3, and exposes a role with
          rolreplication = true. Asserted against the LIVE engine via pg_settings /
          pg_replication_slots / pg_roles — NOT by reading a .conf file on disk (a file can
          say `logical` while the running server is `replica`).
Phase: 02 — Source Systems
Fails when: wal_level is replica/minimal, senders or slots drop below 3, or the replication
            role is missing.
Negative case: start a DB with default (`replica`) WAL config → the wal_level assertion fails
               and creating a logical slot errors.

STUB — implemented before /review-phase. xfail until the DBs exist.
"""

import pytest


@pytest.mark.xfail(reason="STUB — implemented after Postgres services land (Chunk 1+)", strict=True)
def test_cdc_config_present_on_all_sources() -> None:
    """Each source DB reports wal_level=logical, senders/slots >= 3, replication role present."""
    msg = "Phase 02 implementation pending"
    raise NotImplementedError(msg)
