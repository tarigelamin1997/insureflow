# ADR-003 — Per-table REPLICA IDENTITY strategy (FULL on four tables, DEFAULT on the rest)

## Status
Accepted

## Context
ADR-004 put every source instance in `wal_level=logical`, but that only governs *that* a change is logged — `REPLICA IDENTITY` governs *what* the WAL carries for an UPDATE/DELETE. With the implicit `DEFAULT`, Postgres emits only the primary-key columns of the old row; with `FULL`, it emits the entire old row. Phase 05 (Silver) and Phase 06 (Gold) need full before-images for a specific, known set of transformations — deduplication that keys on non-PK columns, SCD Type 2 attribute-change detection, out-of-order event reconciliation, and reserve revaluation — none of which can be computed from a PK-only before-image. But `FULL` roughly doubles WAL volume for wide tables and is paid on every row mutation whether or not a consumer needs it, so it cannot be a blanket default on a 17-table, CDC-source platform. The decision is therefore per-table, and it must be made here (at DDL time) rather than discovered as a silent gap in Phase 05.

## Decision
Set `REPLICA IDENTITY FULL` on exactly four tables and leave the other thirteen at `DEFAULT`:

- **`policyholders` (PMS)** — Silver dedups duplicate-NIC policyholders (scenario S02) keying on the non-PK `nic`, and tracks SCD Type 2 history on `address` / `customer_tier`. Both need the full old row on UPDATE/DELETE to detect what changed and to match on non-key columns.
- **`claims` (CMS)** — Phase 05 reconciles out-of-order claim/event streams (scenario S10) and must compare full prior claim state on UPDATE, not just `claim_id`.
- **`claim_events` (CMS)** — same out-of-order dedup path; event reordering needs the full prior event row to deduplicate correctly.
- **`reserves` (CMS)** — reserve revaluation is an UPDATE that overwrites the prior amount; computing the delta (and auditing the prior value) requires the before-image, which DEFAULT does not emit.

**Every table declares its REPLICA IDENTITY explicitly in the DDL** — `FULL` on the four, `DEFAULT` on the other thirteen — so no table relies on the implicit default. The four FULL tables emit `ALTER TABLE <t> REPLICA IDENTITY FULL;` immediately after the table; the thirteen non-FULL tables emit `ALTER TABLE <t> REPLICA IDENTITY DEFAULT;` (explicit > implicit: the DDL is the single, unambiguous source of truth — a reviewer never has to infer identity from absence, and a later `ALTER TABLE ... SET ...` that silently changed an identity would be visible against an explicit baseline). Each `ALTER` carries a one-line comment stating the reason. The choice is asserted in Phase 04+ against `pg_class.relreplident` (`f` = FULL, `d` = DEFAULT), never against the DDL file.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| `REPLICA IDENTITY FULL` on all 17 tables | Doubles WAL volume on every mutation across the whole platform for tables (e.g. `ifrs17_data`, `gl_settlements`, `endorsements`) whose downstream consumers never key on non-PK columns or need before-images. Pays a permanent CDC cost for fidelity nothing consumes. |
| `DEFAULT` on all 17 tables (rely on PK only) | Silver dedup on non-PK `nic` (S02), SCD Type 2 on `policyholders.address`/`customer_tier`, out-of-order claim/event dedup (S10), and reserve-delta computation all become impossible — the UPDATE/DELETE event would carry only the PK, so the transformation silently produces wrong history with no error. This is the exact downstream-corruption failure the Blast Radius section warns about. |
| `REPLICA IDENTITY USING INDEX` on a non-PK unique index (e.g. `nic`) | `nic` is deliberately NOT UNIQUE (S02 seeds duplicate-NIC pairs), so no unique index exists to point at; and USING INDEX still omits all other columns, so SCD on `address`/`customer_tier` would remain blind. Solves neither need. |

## Consequences

### Makes easier
- Phase 05 Silver dedup/SCD and Phase 06 SCD Type 2 receive complete before-images exactly where they key on non-PK columns — the transformation is correct by construction.
- WAL overhead from `FULL` is confined to four tables, so the platform pays the doubled-WAL cost only where a consumer actually needs it.

### Makes harder
- The four FULL tables incur higher WAL volume and slightly larger Debezium change events on every UPDATE/DELETE — an accepted, scoped cost.
- The FULL set is now a cross-phase coupling: if Phase 05 later needs full before-images on a currently-DEFAULT table, this ADR must be superseded and that table altered before its Silver job can be correct.

### Makes impossible
- A Silver/Gold transformation cannot recover non-PK before-image columns for any of the thirteen DEFAULT tables from the CDC stream alone — the data is simply not in the WAL. Adding such a transformation later requires flipping that table to FULL first (a schema change), not just new Spark code.

### Impact on other phases
- **Phase 03 (CDC):** Debezium captures these identities as-is; `REPLICA IDENTITY FULL` makes the `before` field of UPDATE/DELETE events fully populated for the four tables.
- **Phase 05 (Silver):** depends on FULL for `policyholders` (S02 dedup, SCD), `claims`/`claim_events` (S10 out-of-order dedup), and `reserves` (revaluation delta). This ADR is the upstream guarantee those jobs rely on.
- **Phase 06 (Gold):** SCD Type 2 on policyholder attributes inherits the `policyholders` FULL guarantee.
