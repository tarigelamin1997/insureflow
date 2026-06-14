# ADR-002 — Three separate Postgres instances, not one instance with three schemas

## Status
Accepted

## Context
The platform ingests from three distinct legacy systems — PMS (policy management), CMS (claims management), and PFS (premium & finance). A single Postgres instance with three schemas (`pms`, `cms`, `pfs`) would be cheaper to run and simpler to wire. But InsureFlow's downstream value depends on faithfully reproducing real insurer data-estate problems: claims that reference policies which were never migrated (orphans, scenario S03), per-system CDC slot budgets, and independent failure domains. A single instance silently grants properties the real systems do not have — most damagingly, a cross-system foreign key. If CMS `claims.policy_id` could be declared `REFERENCES pms.policies(policy_id)` inside one database, the orphan-claim scenario the entire Silver/Gold referential-integrity story is built on becomes impossible to inject: Postgres would reject the orphan at write time.

## Decision
Run three separate Postgres containers — `postgres-pms`, `postgres-cms`, `postgres-pfs` — each its own instance with its own database, owner role, data volume (`insureflow-postgres-<sys>-data`), host port, and replication-slot budget. No cross-instance foreign keys are possible by construction: CMS and PMS are different database servers, so `claims.policy_id → policies.policy_id` is an application-level relationship, not an enforced constraint. This makes the S03 orphan-claims scenario a real, injectable cross-system data-quality gap that Phase 05/06 must detect, rather than a constraint the source silently prevents. Each instance also gets an isolated CDC surface: Phase 03 creates one Debezium connector and replication slot per instance, so a stalled slot on one source cannot exhaust another's `max_replication_slots`.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| One instance, three schemas (`pms`/`cms`/`pfs`) | Makes a cross-system FK declarable, which would prevent orphan-claim injection (S03) at the source — destroying the known-answer fixture Phase 06 referential-integrity gates depend on. Also collapses three failure domains into one (a single instance crash takes down all CDC) and forces all three sources to share one `max_replication_slots` budget. |
| One instance, one schema, prefix table names (`pms_policies`, …) | Same cross-FK and shared-failure problems as above, plus it discards the schema boundary that mirrors the real systems and muddies the reserved Kafka namespace `insureflow.{pms,cms,pfs}.{table}`. |

## Consequences

### Makes easier
- Orphan-claim (S03) and other cross-system DQ scenarios are injectable as genuine gaps — the source cannot "helpfully" reject them.
- Each source has an isolated CDC slot budget and failure domain — one source down does not stall the others' replication.
- The three-instance topology mirrors the real insurer estate Phase 03 Debezium config (one connector per host) targets.

### Makes harder
- Three containers to run, three healthchecks, three credential sets, three host ports — more moving parts than one instance.
- Any future "join across systems at source" is impossible in SQL; it must happen downstream (which is exactly where the Medallion architecture puts it anyway).

### Makes impossible
- A database-enforced foreign key from CMS `claims` to PMS `policies`. Cross-system referential integrity is intentionally an application/downstream concern — reversing this (collapsing to one instance) would silently re-introduce the constraint and break the orphan-claim fixture.

### Impact on other phases
- Phase 03 (CDC): one Debezium connector + replication slot per instance; slot names keyed per source.
- Phase 05 (Silver) / Phase 06 (Gold): the orphan-claim and cross-system integrity checks have a real gap to detect; S03's 30 orphans are the known-answer fixture.
