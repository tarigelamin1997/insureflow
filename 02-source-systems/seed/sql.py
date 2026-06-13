"""Deterministic SQL serialisation of a `Dataset` into per-instance INSERT scripts.

Design points that the loading model in `procedures/seed-data.md` requires:

- **Idempotent load.** Each instance file opens with a single transaction and a
  `TRUNCATE <all tables> RESTART IDENTITY CASCADE` preamble. Re-loading the file therefore
  resets the tables and re-inserts the same rows - it never duplicates and never errors on
  a second `psql` run. The whole file is wrapped in `BEGIN; ... COMMIT;` so a partial load
  cannot leave the instance half-seeded.
- **Explicit surrogate IDs.** PKs are `GENERATED ALWAYS AS IDENTITY`; to load the seed's own
  deterministic IDs (so intra-seed FKs resolve) every INSERT uses
  `OVERRIDING SYSTEM VALUE`. `RESTART IDENTITY` then rewinds the identity sequence so future
  application writes do not collide with seeded IDs.
- **Determinism.** No wall-clock, no UUIDs, no RNG here - serialisation is a pure function of
  the dataset. `created_at`/`updated_at` are left to the schema `DEFAULT now()` and are NOT
  emitted, so the SQL text is byte-identical across runs and machines for a fixed seed.

Literal rendering is explicit and total (`_lit`): every Python value maps to one SQL literal,
with `'` doubled for string escaping. There is no string interpolation of untrusted input -
all values originate in the generator itself - but escaping is still applied so an apostrophe
in a generated name (e.g. an address) cannot break the statement.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .model import Dataset

# Per-instance table load order. FK parents precede children so that, even though the seed
# carries no deferred constraints, an INSERT never references a not-yet-inserted parent.
PMS_TABLES: tuple[str, ...] = (
    "agents",
    "products",
    "policyholders",
    "policies",
    "endorsements",
    "renewals",
    "cancellations",
)
CMS_TABLES: tuple[str, ...] = (
    "claims",
    "claim_events",
    "assessments",
    "settlements",
    "reserves",
    "third_party_details",
)
PFS_TABLES: tuple[str, ...] = (
    "premium_transactions",
    "reinsurance_entries",
    "gl_settlements",
    "ifrs17_data",
)

INSTANCES: dict[str, tuple[str, ...]] = {
    "pms": PMS_TABLES,
    "cms": CMS_TABLES,
    "pfs": PFS_TABLES,
}


def _lit(value: object) -> str:
    """Render a single Python value as a SQL literal.

    Total over the value types the model uses: None, bool, int, Decimal, str.
    Strings are single-quoted with embedded quotes doubled.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    msg = f"Unsupported SQL literal type: {type(value)!r}"
    raise TypeError(msg)


def _rows_to_insert(table: str, rows: Sequence[object]) -> str:
    """Render a multi-row INSERT for one table, or a comment if there are no rows."""
    if not rows:
        return f"-- {table}: no rows\n"
    first = rows[0]
    if not is_dataclass(first) or isinstance(first, type):
        msg = f"Row for {table} is not a dataclass instance"
        raise TypeError(msg)
    columns = [f.name for f in fields(first)]
    col_list = ", ".join(columns)
    values_lines = []
    for row in rows:
        rendered = ", ".join(_lit(getattr(row, col)) for col in columns)
        values_lines.append(f"  ({rendered})")
    values_block = ",\n".join(values_lines)
    # nosec B608 — this function's job is to GENERATE SQL text. `table` is one of the 17
    # hardcoded model table names and `col_list` is built from dataclass field names (a
    # closed, internal set); no external/user input reaches the statement. Row VALUES are
    # rendered through `_lit`, which single-quotes and escapes every string. The output is a
    # `.sql` file loaded offline via psql, not a query executed against a live connection.
    return f"INSERT INTO {table} ({col_list}) OVERRIDING SYSTEM VALUE\nVALUES\n{values_block};\n"  # nosec B608


def _header(instance: str, scenarios: Sequence[str], scale: float, seed: int) -> str:
    """Generate the provenance header for an instance file."""
    scen = ",".join(scenarios)
    return (
        f"-- =============================================================================\n"
        f"-- InsureFlow Phase 02 seed - {instance.upper()} instance.\n"
        f"-- GENERATED FILE - do not edit by hand. Regenerate with:\n"
        f"--   python 02-source-systems/seed/generate.py "
        f"--scenarios {scen} --scale {scale} --seed {seed}\n"
        f"-- Deterministic: a fixed --seed yields byte-identical output.\n"
        f"-- Idempotent: TRUNCATE ... RESTART IDENTITY CASCADE precedes the inserts, so\n"
        f"-- re-loading this file resets and re-seeds without duplicating or erroring.\n"
        f"-- =============================================================================\n"
    )


def render_instance(
    instance: str,
    dataset: Dataset,
    *,
    scenarios: Sequence[str],
    scale: float,
    seed: int,
) -> str:
    """Render the full SQL script for one source instance (pms / cms / pfs)."""
    tables = INSTANCES[instance]
    parts: list[str] = [_header(instance, scenarios, scale, seed)]
    parts.append("BEGIN;\n")
    # Idempotency: reset every table this instance owns, in one statement, rewinding
    # the identity sequences so OVERRIDING SYSTEM VALUE inserts stay collision-free.
    truncate_list = ", ".join(tables)
    parts.append(f"TRUNCATE {truncate_list} RESTART IDENTITY CASCADE;\n\n")
    for table in tables:
        rows = getattr(dataset, table)
        parts.append(_rows_to_insert(table, rows))
        parts.append("\n")
    parts.append("COMMIT;\n")
    return "".join(parts)
