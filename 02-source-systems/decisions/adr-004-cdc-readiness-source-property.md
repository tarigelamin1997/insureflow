# ADR-004 — CDC-readiness is a source property, configured at the substrate

## Status
Accepted

## Context
Phase 03 (Debezium + Kafka) is the CDC consumer, but logical replication is a property of the SOURCE Postgres, not of the connector. Three settings must be true on every source instance before any connector can create a replication slot: `wal_level=logical`, `max_wal_senders >= 3`, `max_replication_slots >= 3`, plus a login role carrying the `REPLICATION` attribute. The trap is `wal_level`: it is a postmaster-level GUC that takes effect only at server start. Setting it at runtime via `ALTER SYSTEM … ; SELECT pg_reload_conf()` silently leaves the running server at `replica` — the change applies on the next restart that may never come in a long-lived container — and Phase 03 then fails much later with an opaque "could not create logical replication slot" error, far from the cause. CDC-readiness must therefore be baked into how the source comes up, and it must be asserted against the LIVE engine, not a `.conf` file on disk.

## Decision
Configure CDC-readiness at the substrate, in two places owned by this chunk:

1. **WAL mode via `command:` flags** on each Postgres service in `docker-compose.yml`, applied at postmaster start (not a runtime reload):
   `postgres -c wal_level=logical -c max_wal_senders=10 -c max_replication_slots=10`.
   `wal_level=logical` is the gate; senders/slots are set to 10 (postgres:16's own default) but stated EXPLICITLY so the value is reviewable and survives any future base-image default change — the contract requires only `>= 3`, and 10 leaves head-room for multiple Phase-03 connectors per source.

2. **A dedicated replication role** created once by `02-source-systems/schema/init/00-replication-role.sh` (mounted into `/docker-entrypoint-initdb.d/`), with `LOGIN REPLICATION` and a password from `.env` — least privilege, not the superuser owner, so the CDC credential can be rotated or revoked independently. `REPLICATION` is a cluster-level attribute (`pg_roles.rolreplication`), so the role works for logical decoding on the instance's database.

Per-table `REPLICA IDENTITY` is deliberately NOT set here — there are no tables yet. It is a per-table cost/fidelity decision deferred to Chunk 2 (its own ADR). The fitness function `test_cdc_config_present.py` and Validation Gate VG2 assert all of the above against the running engine (`SHOW wal_level`, `pg_settings`, `pg_roles`, and a create/drop of a test logical slot), never against a file.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Set `wal_level=logical` at runtime via `ALTER SYSTEM` + `pg_reload_conf()` | `wal_level` is postmaster-level — a reload does NOT apply it; the running server stays `replica` while the config file reads `logical`. Phase 03 then fails on slot creation with an opaque error far from the cause. This is exactly the failure VG2's "read from the live server" negative case exists to catch. |
| Reuse the superuser `POSTGRES_USER` as the Debezium login | Violates least privilege — the CDC credential would carry full ownership, and could not be rotated or revoked without disrupting the application owner role. A dedicated `REPLICATION`-only role isolates the CDC blast radius. |
| Mount a full custom `postgresql.conf` instead of `command:` flags | Heavier and more opaque for three settings; a whole file must be kept in sync with the base image's other defaults. The `-c` flags are minimal, visible in the service block, and override only what differs. |

## Consequences

### Makes easier
- Phase 03 Debezium can create replication slots immediately — the source is already in logical-decoding mode with a ready replication role.
- The CDC contract is asserted behaviorally against the live engine, so a misconfigured source fails this phase's gate, not Phase 03's connector.

### Makes harder
- `wal_level=logical` increases WAL volume versus `replica` even before any consumer connects — an accepted cost for a CDC-source platform.
- Changing the WAL settings requires a container restart (postmaster-level), not a hot reload — by design.

### Makes impossible
- A source that looks CDC-ready on disk but is `replica` at runtime cannot pass: the gate reads the live server. Reversing to a reload-based approach would re-open the silent-failure path.

### Impact on other phases
- Phase 03 (CDC): consumes this exact contract — `wal_level=logical`, senders/slots ≥ 3, a `REPLICATION` role to log in as. One connector + slot per source instance (per ADR-002).
- Chunk 2 (this phase): owns per-table `REPLICA IDENTITY` (FULL vs DEFAULT), which builds on the logical WAL mode established here.
