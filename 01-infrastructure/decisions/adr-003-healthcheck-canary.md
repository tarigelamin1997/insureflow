# ADR-003 — Canary reference fixture as the behavioral validation target

## Status
Accepted

## Context
Phase 01 builds the infrastructure substrate but, by scope, stands up no data-phase service. Yet the
Gate Robustness Standard (`procedures/validation-standard.md`) requires every validation criterion to
be behavioral — to assert a thing *does its job* through its real interface — and the two substrate
behaviors that matter most, the healthcheck pattern and shared-network service-name DNS, need a live
target to be proven. A spec with no executable target is presence-only, which the standard calls "no
gate." Standing up a real later-phase service to act as that target would violate phase ownership
(those services are locked to phases 02/04/…) and balloon Phase 01.

## Decision
Introduce one minimal, permanent reference service, `canary` (`nginx:alpine`, digest-pinned), that
serves a page from the named volume `insureflow-canary-html` on the shared `insureflow` network. It is
the behavioral target for VG2 (healthcheck reaches `healthy`, and flips to `unhealthy` when the served
file is removed) and VG3 (resolves by service name over the shared network, and fails off it). It
doubles as a permanent connectivity/health smoke test that later phases can run to confirm the
substrate still works after they add services. Future refinement (not this phase): move it behind
Compose `profiles: ["smoke"]` once real services exist, so the production stack does not ship a stray
nginx.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Zero services — validate only `terraform` and `docker compose config` | The healthcheck pattern and shared-network DNS would be documented but never executed — presence-only criteria, which `validation-standard.md` rejects as "no gate." |
| Reuse a real later-phase service (MinIO, Postgres) as the target | Violates phase ownership (locked to phases 04/02) and pulls later-phase scope into Phase 01. |
| Stand up a local `registry:2` as the fixture | Has real offline value but drags in image-cache/registry concerns well beyond Phase 01's substrate scope. |

## Consequences

### Makes easier
- Gives Phase 01 a genuinely behavioral validation gate (it caught ERR-001, a `localhost`/IPv6 healthcheck defect, before merge).
- Provides a reusable connectivity/health smoke test for every later phase.
- Demonstrates the healthcheck cadence (ADR-002) and shared-network conventions concretely.

### Makes harder
- One extra service in `docker-compose.yml` until it is profiled out.
- A small image to pull on first run (mitigated by the Terraform digest pin staging it offline).

### Makes impossible
- N/A.

### Impact on other phases
- Later phases may run the canary as a smoke test before adding their own services.
- The `profiles: ["smoke"]` refinement is a noted future change once the first real services land. No upstream dependency — Phase 01 is the root.
