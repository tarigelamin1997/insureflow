> **Status: Executed (2026-06-14).** Phase 02 shipped — PR #8 merged (`e8c24e2`), `v0.2.0` tagged + released, `/audit-foundation` 11/11 PASS. Decision records: `02-source-systems/decisions/adr-001…adr-005`. Deviations from the literal plan are listed below.

## Deviations during execution

- **`SendMessage` unavailable in the harness** → the "one *continued* subagent via SendMessage" model wasn't supported. Used a **fresh Opus 4.8 builder per chunk** instead. No material loss: the phase brief's session-independence let each builder orient from the repo + brief, and the orchestrator re-stated the invariant list (orphan=30, dup-NIC=50, no NULL PK, CDC config) in each chunk prompt.
- **Scope was S01–S05, not S01–S12.** The approved brief scoped the seed to the S01 baseline + the four post-acquisition data-debt scenarios (S02–S05). S06–S12 are architected (registry raises `NotImplementedError`) and deferred to their consuming phases.
- **Added a C2 schema-spec checkpoint.** Per the user's "hand the builder a spec" decision, the orchestrator drafted the full 17-table schema spec (column-level, `REPLICA IDENTITY` per table, the S02/S03/S04/S05 mechanics) for **human approval before** the C2 builder wrote any DDL.
- **C4 split into C4a (implement) + C4b (live run).** The user ran Docker locally; the orchestrator drove the live validation — **16/16 fitness tests pass** and the VG3 negative **fired** (S01-only load → the dup/orphan gates went red), then restored the full seed.
- **Mid-build fixes the gates forced:** the replication-role GRANT coupling → parameterized `02-grant-select.sh`; a host **port-5432 collision** with a native Postgres → default host ports moved to 15432/15433/15434; a stale PMS schema-header comment; and a CI mypy **coverage gap** (the `seed` package + unit tests were unchecked) → a second mypy invocation with `MYPYPATH`.
- **CodeRabbit ran in two passes** — incremental fixes during the build, then a full review at close (6 fixed + 1 dismissed-with-reason). The `/close-phase` convention of flipping the index/CONTRACTS ✅ **inside** the closing PR was kept; only the Status-line wording was softened so `v0.2.0` wasn't claimed as released before the tag existed.

---

# Plan — Phase 02 (Source Systems) built via a spun subagent

## Context

Phase 01 (Infrastructure) is shipped and released (`v0.1.0`). Phase 02 — Source Systems — is next: three PostgreSQL 16 services (`postgres-pms/cms/pfs`), their schemas, the 12-scenario seed data with deliberate post-acquisition data-debt, and CDC-ready Postgres config so Phase 03 Debezium plugs in cleanly.

This plan is about **how we build it**, not just what. The user's decided operating model: the orchestrator chat spins **one Opus subagent** (1M ctx), drives it through the repo's existing gated workflow **sequentially**, reviews a reasonable amount of work at each checkpoint, and **the human approves the merge**. No parallel agent teams. The subagent's separate context window keeps the orchestrator lean (context-offload), and the handoff is automated (orchestrator relays via the Agent tool / SendMessage — no human copy-paste).

The build reuses the Phase-01 machinery verbatim: `/new-phase` → fill phase `CLAUDE.md` → `/start-phase` (6 entry checks) → implement on branch → PR (CodeRabbit + CI) → `/review-phase` → `/close-phase` (now incl. Check 10 doc-reflection) → human merge → tag `v0.2.0`.

**Verified correction:** `procedures/seed-data.md` is already `Written` (not deferred). Phase 02 has **no** deferred procedure to author first — unlike Phase 01. The subagent must not invent one (it would stall `/start-phase` Check 3). `kafka-connector.md` / `airflow-dag-factory.md` are Phase 03's.

## Delegation model (locked)

- **One** continued Opus subagent, spun from this chat; sequential; continued across chunks via SendMessage (shared context).
- Orchestrator verifies after each chunk and reports up; human reviews each checkpoint; human authorizes the final merge + tag.
- Re-state the invariant list in each SendMessage (orphan=30, dup-NIC=50, no NULL PK, CDC config) — don't rely on the subagent recalling it from Chunk 0 late in a crowded context.

## Orchestration — 6 chunks, a checkpoint each

| Chunk | Subagent does | Orchestrator verifies | Human checkpoint |
|---|---|---|---|
| **C0 — Scaffold + Brief** | `/new-phase`; fill `02-source-systems/CLAUDE.md` to Minimum Viable; `xfail` FF stubs; `/start-phase` (6 checks) | All 6 PASS; every VG+FF criterion behavioral + negative case; service names exactly `postgres-pms/cms/pfs`; Consumes matches `CONTRACTS.md` row 01 verbatim; no procedure authored | Approve the brief + the behavioral criteria **before any code** (highest leverage) |
| **C1 — Substrate** | 3 Postgres services in `docker-compose.yml` (network/volumes/`x-healthcheck-defaults`+`SELECT 1`/`start_period` 60s); CDC config (`wal_level=logical`, senders/slots ≥3, repl user); 3 digest-pinned Terraform images + `@sha256` vars; extend `.env.example`; open PR | `docker compose config` parses; Phase-01 contract tests still pass; same digest in compose+terraform; CDC params actually set | Substrate correct + CDC config sufficient for Phase 03? |
| **C2 — Schemas / DDL** | DDL for PMS(7)/CMS(6)/PFS(4) tables; FKs permit orphan claims; `REPLICA IDENTITY` per table; init scripts | All tables present; orphan path structurally possible; REPLICA IDENTITY explicit + justified; PK/NOT NULL where invariants need; 4 segments covered | **Most ambiguity-prone.** Schemas right for the domain? REPLICA IDENTITY FULL-vs-DEFAULT right? |
| **C3 — Seed generator** | `seed/generate.py` + `s01..s12` + gitignored `output/`; S01 50K/80K/25K/200K; %-based vs fixed-absolute split; `--scenarios/--scale/--seed`; idempotent; unit tests | Deterministic (seed 42); fixed counts constant under `--scale`; idempotent loads; S03=30 orphans, S02=50 dup-NIC; output gitignored | Right data-debt at right volume; determinism + idempotency both real; CI `--scale 0.02` fast + valid? |
| **C4 — Fitness + Validation Gate** | Implement `tests/contracts/` (behavioral + refutable): orphan count, dup-NIC, no NULL PK, CDC config via `pg_settings`/`pg_replication_slots`; finalize VG with paired negatives | No `xfail` left; FF count ≥ declared; each test refutable; CDC test asserts behavior not file presence; negatives fire | Do the FFs actually prove the invariants (fail when violated)? Spot-check one live |
| **C5 — Gates + merge** | `/review-phase` then `/close-phase` (incl. Check 8 append `CONTRACTS.md` row, Check 10 doc-reflection all surfaces) | review "clear"; close PASS incl. doc-reflection negative case; Consumes matches Phase 01; Kafka namespace reserved (not implemented) | **Merge approval:** all gates green, all surfaces reflect Phase 02 → merge → ✅ → tag `v0.2.0` |

Checkpoints are adjustable — C0 and C5 are gate-running and can be auto-flowed if you want fewer stops; the build chunks (C1–C4) and the merge are the ones worth your eyes.

## ADRs Phase 02 writes (`02-source-systems/decisions/`, numbered from 001)

1. **adr-001** — one shared digest-pinned Postgres image across the 3 services vs three image vars.
2. **adr-002** — three separate Postgres instances (not one instance, three schemas) → orphan claims are a real cross-DB gap, not an enforceable FK.
3. **adr-003** — REPLICA IDENTITY FULL vs DEFAULT per table (FULL where Phase 03 needs before-images; DEFAULT elsewhere to limit WAL).
4. **adr-004** — CDC-readiness as a source property: `wal_level=logical`, senders/slots ≥3, dedicated replication role.
5. **adr-005** — seed determinism + injection model (seed 42, %-vs-fixed split, idempotent loads, gitignored output).

Deferred to Phase 03 (do NOT write here): Debezium connector config, topic creation/Avro registration, slot lifecycle, `insureflow.{src}.{table}` instantiation. Phase 02 only reserves the namespace + makes sources CDC-capable.

## Top risks to bake into the subagent's instructions

1. **Schema column-set ambiguity (C2):** the 17 tables aren't fully specified in the repo — instruct the subagent to **stop and surface** any guessed column set, never invent schema silently. Drift here cascades to seed, tests, and Phases 04–06.
2. **REPLICA IDENTITY:** force an explicit per-table FULL/DEFAULT decision into adr-003, reviewed at C2 — not discovered after Phase 03 breaks.
3. **Seed split backwards:** S02/S03/S07–S12 are **fixed counts** regardless of `--scale`; only S04/S05/S06 scale. A subagent may "helpfully" scale the orphan count and break S03's absolute-30 assertion.
4. **Determinism ≠ idempotency** — verify both separately in C3.
5. **CI seed scale:** CI must run `--scale 0.02`, not full domain scale (slow/flaky otherwise).
6. **No deferred procedure** — tell it explicitly: author no procedure (`seed-data.md` already Written).
7. **Exact service names** — `postgres-pms/cms/pfs` are asserted by an existing Phase-01 contract test; any deviation fails CI.
8. **Compose↔Terraform digest seam** — same digest from one `.env.example` source across both, ×3 services (3 chances to drift).
9. **Chaos section** — Phase 02 has no runnable chaos (earliest Phase 03); write the explicit "None — reason" form or `/start-phase` Check 2 fails.
10. **Doc-reflection front line** — update surfaces incrementally as C1 touches root `docker-compose.yml`/`.env.example`, so C5's Check 10 isn't a big-bang scramble.

## Verification

- **Per chunk:** the orchestrator checks listed in the table above; each chunk ends with the subagent reporting artifacts + any flagged ambiguity, and the orchestrator confirming before the human checkpoint.
- **Gate-level:** `/start-phase` 6/6 PASS (C0); CI + CodeRabbit green on the PR (C1+); `/review-phase` "clear for /close-phase"; `/close-phase` 10/10 PASS including the doc-reflection negative case (deliberately stale one surface → Check 10 fires).
- **End-to-end:** `docker compose up -d` brings the 3 Postgres services healthy; the seed generator loads idempotently at `--scale 0.02`; fitness tests prove exactly 30 orphan claims, 50 dup-NIC pairs, zero NULL PKs, and CDC config live (`pg_settings`/`pg_replication_slots`); `/audit-foundation` green post-merge (I2 + I11 reconcile Phase 02).

## Critical files

- `02-source-systems/CLAUDE.md` — the phase brief that gates everything (created in C0)
- `docker-compose.yml` — extended with the 3 Postgres services + CDC config (C1)
- `procedures/seed-data.md` — binding spec for the generator + scenario volumes (C3)
- `01-infrastructure/tests/contracts/test_service_naming.py` — hardcodes the exact service names
- `CONTRACTS.md` — Consumes-match source + the Produces row appended at close
- `01-infrastructure/terraform/` + `.env.example` — digest-pinning pattern to mirror ×3
