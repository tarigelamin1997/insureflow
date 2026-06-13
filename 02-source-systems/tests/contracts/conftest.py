"""Shared fixtures for the Phase 02 contract (fitness-function) tests.

These tests are behavioral: they assert against the LIVE Postgres engines, not against
files on disk. The proof therefore only runs when the three source instances are actually
reachable (i.e. after `docker compose up` + seed load, exercised at phase close by the
orchestrator). When no database is reachable — which is the case in the CI `fitness-functions`
job, which has no DB — every test in this directory `pytest.skip(...)`s with an explicit reason
naming what is missing. A skip is NOT a silent pass: the behavioral proof is deferred to the
live stack, and the skip reason says so.

Connection parameters come exclusively from the environment (never hardcoded), keyed to the
`.env.example` contract:

    POSTGRES_<SYS>_HOST       host the instance is reachable on   (default: localhost)
    POSTGRES_<SYS>_HOST_PORT  published host port                 (default: 5432/5433/5434)
    POSTGRES_<SYS>_USER       application owner role
    POSTGRES_<SYS>_PASSWORD   application owner password
    POSTGRES_<SYS>_DB         database name
    POSTGRES_REPLICATION_USER the replication role name (asserted to exist with rolreplication)

`<SYS>` is one of PMS / CMS / PFS. `POSTGRES_<SYS>_PORT` is accepted as an alias for the host
port if `POSTGRES_<SYS>_HOST_PORT` is unset. Defaults mirror `.env.example` so a developer who
brought the stack up with the example values can run the tests with zero extra configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

    import psycopg

# psycopg (v3) is an optional test dependency. If it is not installed (e.g. a minimal CI lane),
# every test skips rather than errors on import — the behavioral proof still runs on the live
# stack where the dependency is present.
try:
    import psycopg as _psycopg
except ImportError:  # pragma: no cover - exercised only in a psycopg-less environment
    _psycopg = None  # type: ignore[assignment]

# The three source instances and their default published host ports (from .env.example).
_DEFAULT_HOST_PORT = {"pms": "5432", "cms": "5433", "pfs": "5434"}
INSTANCES: tuple[str, ...] = ("pms", "cms", "pfs")


@dataclass(frozen=True)
class DsnSpec:
    """Resolved connection parameters for one source instance."""

    system: str
    host: str
    port: int
    user: str
    password: str
    dbname: str

    def conninfo(self) -> str:
        """Render a libpq connection string. A short connect_timeout keeps skips fast."""
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password} connect_timeout=3"
        )


def _env(name: str) -> str | None:
    """Read an env var, treating empty/whitespace as unset."""
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def dsn_for(system: str) -> DsnSpec:
    """Resolve the connection spec for one instance from the environment.

    Falls back to `.env.example` defaults for host (localhost), port, user, password, and db
    so the common "brought the stack up with example values" path needs no extra config.
    """
    sys_upper = system.upper()
    host = _env(f"POSTGRES_{sys_upper}_HOST") or "localhost"
    port_str = (
        _env(f"POSTGRES_{sys_upper}_HOST_PORT")
        or _env(f"POSTGRES_{sys_upper}_PORT")
        or _DEFAULT_HOST_PORT[system]
    )
    user = _env(f"POSTGRES_{sys_upper}_USER") or system
    password = _env(f"POSTGRES_{sys_upper}_PASSWORD") or f"{system}_pw_change_me"
    dbname = _env(f"POSTGRES_{sys_upper}_DB") or system
    return DsnSpec(
        system=system,
        host=host,
        port=int(port_str),
        user=user,
        password=password,
        dbname=dbname,
    )


def replication_role_name() -> str:
    """Return the replication role name expected to exist (env, default `replicator`)."""
    return _env("POSTGRES_REPLICATION_USER") or "replicator"


def _connect_or_skip(spec: DsnSpec) -> psycopg.Connection:
    """Open a connection to one instance, or `pytest.skip` with an explicit, non-silent reason."""
    if _psycopg is None:
        pytest.skip(
            "psycopg is not installed — behavioral contract test deferred to the live stack "
            "(run `pip install psycopg[binary]` and bring up the three Postgres instances). "
            "This is a deferred proof, NOT a pass.",
        )
    try:
        return _psycopg.connect(spec.conninfo())
    except _psycopg.OperationalError as exc:
        pytest.skip(
            f"postgres-{spec.system} not reachable at {spec.host}:{spec.port} "
            f"({type(exc).__name__}) — behavioral contract test deferred to the live stack "
            f"(`docker compose up` + seed load at phase close). This is a deferred proof, "
            f"NOT a pass.",
        )


@pytest.fixture
def pms_conn() -> Iterator[psycopg.Connection]:
    """Live connection to postgres-pms, or skip if unreachable."""
    conn = _connect_or_skip(dsn_for("pms"))
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def cms_conn() -> Iterator[psycopg.Connection]:
    """Live connection to postgres-cms, or skip if unreachable."""
    conn = _connect_or_skip(dsn_for("cms"))
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def all_conns() -> Iterator[dict[str, psycopg.Connection]]:
    """Live connections to all three instances, keyed by system, or skip if any is unreachable.

    Skips on the FIRST unreachable instance so a partial stack (e.g. only PMS up) reports a
    clear, specific reason rather than a confusing partial result.
    """
    conns: dict[str, psycopg.Connection] = {}
    try:
        for system in INSTANCES:
            conns[system] = _connect_or_skip(dsn_for(system))
        yield conns
    finally:
        for conn in conns.values():
            conn.close()
