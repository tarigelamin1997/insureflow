# ADR-001 — One shared digest-pinned Postgres image for all three source DBs

## Status
Accepted

## Context
Phase 02 stands up three PostgreSQL 16 source instances (`postgres-pms`, `postgres-cms`, `postgres-pfs`). Phase 01 established that Terraform owns image provisioning + digest pinning and Compose references the SAME digest from a single `.env.example` source, so a `docker compose up` is reproducibly offline. The open question for this phase is how many image references to introduce: one shared digest-pinned `postgres:16` used by all three services, or a per-system variable each service pins independently. The three systems are the same RDBMS at the same major version; what makes them three real legacy systems (ADR-002) is their database name, owner role, data volume, replication-slot budget, and host port — not the binary image.

## Decision
Use ONE shared image variable, `POSTGRES_IMAGE`, digest-pinned to `postgres@sha256:<64-hex>` in `.env.example`. All three service blocks in `docker-compose.yml` reference `${POSTGRES_IMAGE}`. Terraform (`02-source-systems/terraform/`) declares ONE `variable "postgres_image"` (with the `@sha256:[0-9a-f]{64}$` format validation from the Phase 01 pattern) and ONE `docker_image "postgres"` resource (`keep_locally = true`). The digest is sourced into Terraform via `TF_VAR_postgres_image` from the same `.env` line — closing the Phase 01 "same digest in compose + terraform" seam. Re-pinning is a single documented `docker buildx imagetools inspect postgres:16 --format '{{.Manifest.Digest}}'` against the multi-arch index digest.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Three image variables (`POSTGRES_PMS_IMAGE`, `…_CMS_…`, `…_PFS_…`), one `docker_image` resource each | Three digests to keep in lockstep with no upside — the systems run identical Postgres. It triples the surface for the exact drift the single-source rule exists to prevent (one var re-pinned, two forgotten → a silent version skew across sources that Debezium would later hit), and stages the same bits three times. |
| Float the tag (`postgres:16`) instead of pinning a digest | Breaks the 100%-offline guarantee Phase 01 paid for — a later offline `docker compose up` would pull a drifted or absent tag. The Terraform `validation` block exists specifically to reject this. |

## Consequences

### Makes easier
- One digest to audit, re-pin, and keep in lockstep with Compose — the single-source rule has a single line to protect.
- Terraform stages the image exactly once; `terraform apply` is fast and the offline cache holds one Postgres image, not three copies.

### Makes harder
- Pinning a different Postgres version for just one source (e.g. testing PFS on Postgres 17) now requires introducing a second variable first — a deliberate friction that surfaces the divergence as an explicit decision rather than a silent edit.

### Makes impossible
- Per-system image divergence cannot happen by accident — there is one digest, so all three sources are guaranteed bit-identical until someone consciously splits the variable. Reversing this (true per-system images) requires a new ADR.

### Impact on other phases
- Phase 03 (CDC): Debezium connects to three hosts running a guaranteed-identical Postgres — one logical-decoding behaviour to reason about, not three.
- All later phases: inherit the single-digest re-pin procedure documented in `.env.example`.
