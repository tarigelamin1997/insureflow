# Phase 01 — Infrastructure (Docker Compose + Terraform)

## What This Phase Builds

The infrastructure substrate every later phase plugs into — and nothing from a later phase: a root
`docker-compose.yml` defining the shared `insureflow` bridge network, the named-volume namespace, a
reusable `x-healthcheck-defaults` anchor, and a single `canary` (`nginx:alpine`) service that comes up
healthy on the shared network; a Terraform (Docker provider) configuration that pulls and digest-pins
every service image for offline reproducibility; a `.env.example` documenting every environment
variable; and the Python tooling baseline (ruff / mypy / bandit + pytest fitness functions) wired into
pre-commit and CI.

## How to Run

```bash
cp .env.example .env          # environment contract (digest-pinned canary image + host port)
docker compose up -d          # brings up the canary on the shared `insureflow` network
docker compose ps             # canary should report (healthy)
```

Optional — pre-stage digest-pinned images for fully-offline runs (Terraform image provisioning):

```bash
export TF_VAR_canary_image=$(grep '^CANARY_IMAGE=' .env | cut -d= -f2)
terraform -chdir=01-infrastructure/terraform init
terraform -chdir=01-infrastructure/terraform apply
```

Tear down with `docker compose down` (add `-v` to also drop the canary volume).

## Validation

The four behavioral Validation Gate criteria (each with a negative case) — full definitions in
[CLAUDE.md](CLAUDE.md):

- **VG1 image pin** — `terraform apply` stages the digest-pinned image; a floating tag or nonexistent digest fails `apply`.
- **VG2 healthcheck** — the canary reaches `healthy`; removing the served file flips it to `unhealthy`.
- **VG3 shared-network DNS** — `docker run --network insureflow busybox wget http://canary/` resolves; off-network it fails.
- **VG4 env completeness** — `docker compose config` resolves every `${VAR}`; unsetting a required one fails.

Architectural fitness functions (CI-blocking): `pytest 01-infrastructure/tests/contracts`.
