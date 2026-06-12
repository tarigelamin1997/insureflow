# ADR-001 — Compose owns runtime substrate; Terraform owns image provisioning

## Status
Accepted

## Context
Phase 01 must honour two locked decisions that overlap: a single `docker compose up` brings the entire
stack live, and Terraform (Docker provider) is the IaC layer. Both tools can create Docker networks,
volumes, and containers, so if both own the runtime substrate they collide over a resource named
`insureflow`. A non-overlapping division of responsibility is required — one that preserves the
single-command entry point, gives Terraform genuine behavioral work, and serves the 100%-offline
constraint where images must be staged before a run.

## Decision
Compose owns the **runtime substrate**: the `insureflow` bridge network, the named volumes, and every
service container. `docker compose up` brings the stack live in one command with no prerequisite step.
Terraform (`kreuzwerker/docker ~> 3.0`) owns **image provisioning and digest pinning**: one
`docker_image` resource per service, pinned by digest, with `keep_locally = true` so the offline cache
survives `terraform destroy`. The digest is single-sourced from `CANARY_IMAGE` in `.env(.example)` —
Compose reads `${CANARY_IMAGE}`, Terraform reads the same value via `TF_VAR_canary_image` — so the two
consumers can never drift to different images. `terraform apply` pre-stages the exact images Compose
then runs, making every subsequent `docker compose up` reproducibly offline.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Terraform owns network + volumes; Compose references them `external: true` (Option A) | Breaks the locked single-command promise — `terraform apply` becomes a mandatory bootstrap before every fresh `up` — and adds an external-network failure mode where `docker compose up` fails cryptically if the network was not pre-created. |
| Terraform manages the whole stack as `docker_container` resources, no Compose | Contradicts the locked "single `docker compose up`" entry point and loses Compose ergonomics (`logs`, `ps`, `exec`, `depends_on: service_healthy`). |
| Compose owns everything, drop Terraform | Terraform (Docker provider) is a locked project decision; dropping it is out of scope. |

## Consequences

### Makes easier
- The single-command run is preserved; no bootstrap step before `docker compose up`.
- Offline reproducibility: pinned digests are staged ahead of the run, so later runs need no registry.
- Each tool has exactly one job; a new service in a later phase = one Compose block + one `docker_image` resource.

### Makes harder
- A digest bump touches two consumers (`.env` and the pull) — mitigated by single-sourcing the digest in `.env`.
- `terraform apply` requires `TF_VAR_canary_image` to be set (the documented run path sources it from `.env`).

### Makes impossible
- Terraform cannot own the running-container lifecycle without reversing this ADR — Compose is the source of truth for running services.

### Impact on other phases
- Every later phase follows this split: add the service to `docker-compose.yml` and add a digest-pinned `docker_image` resource to `01-infrastructure/terraform`.
- Phase 12 (Observability) scrapes Compose-defined services. No upstream dependency — Phase 01 is the root.
