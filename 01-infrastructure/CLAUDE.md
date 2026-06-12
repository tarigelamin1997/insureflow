# CLAUDE.md — Phase 01: Infrastructure (Docker Compose + Terraform)

## What This Builds

After this phase the repository has a working infrastructure **substrate** that every later phase
plugs into — and nothing from a later phase. Concretely: a root `docker-compose.yml` defining a
user-defined bridge network `insureflow`, the platform's named-volume namespace, a reusable
`x-healthcheck-defaults` YAML anchor encoding the standard healthcheck cadence, and a single `canary`
service (`nginx:alpine`) that comes up `healthy` on the shared network and is reachable by service
name. A Terraform configuration under `01-infrastructure/terraform/` pulls and **digest-pins** every
service image through the Docker provider — the offline image-staging layer — starting with the
canary's `nginx:alpine`. A `.env.example` documents every environment variable the stack references.
The Python tooling baseline (ruff / mypy / bandit via pre-commit + CI, and the pytest fitness-function
job) is active. End state, verified: `docker compose up` brings the canary to `healthy` in a single
command; `terraform apply` pre-stages the pinned images; `terraform plan` is clean.

## Prerequisites

Host tooling only — Phase 01 is the root of the dependency graph; no upstream InsureFlow phase is a
prerequisite.

- Docker Engine ≥ 24 with the Docker Compose v2 plugin (`docker compose`, not legacy `docker-compose`), reachable at the local daemon socket
- Terraform ≥ 1.6
- Python 3.11 (runs the pre-commit hooks and the pytest fitness functions)
- Internet access **on first run only** — to pull base images (`nginx:alpine`, `busybox`) and the Terraform Docker provider (`kreuzwerker/docker`). Every subsequent run is fully offline. (optional after first run)

## Owns These Paths

Net-new (created by this phase):

- `docker-compose.yml` — root stack skeleton (network, volumes, healthcheck anchor, canary service)
- `.env.example` — env-var contract
- `pyproject.toml` — ruff + mypy configuration
- `.bandit` — bandit configuration
- `01-infrastructure/CLAUDE.md`, `01-infrastructure/README.md`, `01-infrastructure/decisions/`, `01-infrastructure/errors/`, `01-infrastructure/tests/`
- `01-infrastructure/terraform/` — `*.tf`, plus `.terraform.lock.hcl` (committed intentionally)
- `01-infrastructure/tests/contracts/` — fitness-function tests

Modifies (owned by the foundation / dev-tooling — **flagged** because they are shared files):

- `.pre-commit-config.yaml` — adds the `ruff`, `mypy`, `bandit` hooks (was ggshield + file-hygiene only; the file's own comment assigns this to Phase 01)
- `.github/workflows/quality.yml` — adds the `lint` and `fitness-functions` jobs (was secret-scan only; the file's own comment assigns this to Phase 01)
- `README.md` (root) — fills the Getting Started first-run steps once the stack runs, kept **honest to a canary-only stack** (no service URLs for services that do not exist yet)
- `.gitignore` (root) — already anticipates `01-infrastructure/terraform/` paths; extend only if a new artifact type appears

## Decisions

Phase-local ADRs, numbered from `001` (separate sequence from root `decisions/adr-000`/`adr-001` — no
clash):

- Compose owns the runtime substrate (network + volumes + services); Terraform (Docker provider) owns image provisioning + digest pinning for offline — see `decisions/adr-001-compose-vs-terraform-ownership.md`
- Standard healthcheck cadence and the reusable `x-healthcheck-defaults` anchor — see `decisions/adr-002-healthcheck-cadence.md`
- The `canary` reference fixture (`nginx:alpine`) as the phase's behavioral validation target — see `decisions/adr-003-healthcheck-canary.md`

Inline (no ADR — pre-decided by `procedures/code-quality.md`, no real alternative):

- The Python tooling baseline (ruff / mypy / bandit + pytest fitness functions) is activated in Phase 01 because this phase introduces the repository's first Python (the fitness functions) and the CI `fitness-functions` job cannot run without it. `.pre-commit-config.yaml` and `.github/workflows/quality.yml` both already designate Phase 01 as the owner of this activation.

## Interface Contract

### Produces

- **Docker network:** `insureflow` (driver: `bridge`, compose-managed) — every later service attaches here for service-name DNS resolution
- **Named-volume convention:** `insureflow-<service>-<purpose>` (compose-managed named volumes); Phase 01 instantiates it with `insureflow-canary-html`, the volume nginx serves its page from — making both the convention concrete and the VG2 negative case meaningful — later phases follow this pattern
- **docker-compose.yml:** root skeleton + `x-healthcheck-defaults` anchor + the reserved service-name namespace (exact names from root `CLAUDE.md` → Global Naming Conventions) — later phases append their service blocks
- **.env.example:** the env-var contract — variable names, default host ports, credential placeholders, and host data paths — later phases extend it
- **Healthcheck pattern:** `procedures/docker-healthcheck.md` (patterns per service type: HTTP, TCP, exec/CLI, DB-ping) — the standard every later service's `healthcheck` follows
- **Terraform image-provisioning config:** `01-infrastructure/terraform/` (`docker_image` resources, digest-pinned) — later phases add one pinned image per new service to keep the stack reproducibly offline
- **Python tooling baseline:** `pyproject.toml` (ruff + mypy), `.bandit`, the pre-commit hooks, and the CI `lint` + `fitness-functions` jobs — every later phase's Python inherits these

### Consumes

None. Phase 01 is the foundation; it depends only on host tooling (Docker, Terraform, Python), not on
any upstream InsureFlow phase.

### SLA

- **Freshness:** N/A — no data flows in this phase
- **Completeness:** N/A — no records produced
- **Latency:** N/A — no serving endpoint
- The only timing property: `docker compose up` brings every service to `healthy` within its `start_period + interval × retries` budget.

## Test Strategy

Infrastructure phase (category 01 per `procedures/code-quality.md`). Every entry names its negative
case per `procedures/validation-standard.md` — a quality gate that has never rejected bad input is
unproven.

- **Compose config validity** — Tool: `docker compose config` — Threshold: parses and resolves, exit 0 — Blocking: yes — Negative: a malformed compose (broken anchor / unknown key) → non-zero exit.
- **Terraform validity + image pin** — Tool: `terraform validate` / `terraform apply` — Threshold: `validate` exit 0; `apply` pulls the pinned digest — Blocking: yes — Negative: malformed `.tf` → `validate` non-zero; a nonexistent digest → `apply` fails.
- **Service health (behavioral)** — Tool: Docker healthcheck + `docker inspect` — Threshold: canary reports `healthy` — Blocking: yes — Negative: break the served endpoint → `unhealthy` within `interval × retries`.
- **Shared-network DNS** — Tool: `docker run --network insureflow …` — Threshold: the canary resolves by service name — Blocking: yes — Negative: an off-network run → name does not resolve.
- **Fitness functions** — Tool: `pytest 01-infrastructure/tests/contracts/` — Threshold: all pass — Blocking: yes — Negative: each test's built-in refutation (see Fitness Functions).
- **Lint / type / security** — Tool: ruff, `mypy --strict`, bandit — Threshold: all pass — Blocking: yes — Negative: ruff, mypy, and bandit each fail on an injected violation.
- **No unit tests for config** — Justified: infrastructure is validated by running it (`compose up` + `terraform apply` + the fitness inspections), not by unit-testing YAML/HCL. This is the code-quality.md standard for the infrastructure phase category.

## Procedures

Before writing any of the following file types in this phase, read the linked procedure first:

| Task | Procedure |
|---|---|
| Code quality standards | `procedures/code-quality.md` |
| Error encountered | `procedures/error-logging.md` |
| Docker healthcheck | `procedures/docker-healthcheck.md` |

> `procedures/docker-healthcheck.md` is `Deferred → Phase 01` in `procedures/README.md`. Authoring it
> is the **first task of `/start-phase`**, before any implementation code; the registry is then
> updated to `Written`.

## Validation Gate

Each criterion is **behavioral** (asserts the component does its job through its real interface) and
carries a **negative case** (per `procedures/validation-standard.md`). Runnable after
`docker compose up` and `terraform apply`, with no other setup. None of these depend on
Prometheus/Grafana alerting, so no criterion is deferred `[validated at Phase 12]` — all four are
validated at this phase's own close.

### VG1 — Terraform pulls and pins the canary image (offline image provisioning)

- **Positive:** `terraform -chdir=01-infrastructure/terraform init && terraform -chdir=01-infrastructure/terraform apply -auto-approve` → exit 0; then `docker image inspect <pinned-image>@<digest>` returns the image and its `RepoDigests` contains the pinned digest.
- **Negative:** point the canary image at a nonexistent/garbage digest and re-apply → `terraform apply` fails with a pull error, non-zero exit. Proves the pin is enforced, not cosmetic.

### VG2 — Stack comes up healthy (behavioral healthcheck, not a port probe)

- **Positive:** `docker compose up -d` → within `start_period + interval × retries`, `docker inspect --format '{{.State.Health.Status}}' insureflow-canary` returns `healthy`. The healthcheck issues a real, **fail-on-error** HTTP request *inside* the container (`wget -q -O /dev/null` / `curl -f`, per `procedures/docker-healthcheck.md`) against the page served from the `insureflow-canary-html` volume.
- **Negative:** remove the served file — `docker compose exec canary rm /usr/share/nginx/html/index.html` — so nginx answers `403`/`404`; wait past `start_period` → the fail-on-error check exits non-zero and health transitions to `unhealthy` within `interval × retries`. (A check without `-f`/fail-on-error would exit `0` on the 403/404 and this negative case would never fire — that is the watch-point.)

### VG3 — Shared-network service-name DNS

- **Positive:** `docker run --rm --network insureflow busybox:1.36 wget -qO- http://canary` returns the canary's HTTP body — `canary` resolves by Compose service name over the shared bridge.
- **Negative:** the same command **without** `--network insureflow` (lands on the default bridge) → `canary` does not resolve and `wget` exits non-zero. Proves later phases must share `insureflow` to reach one another.

### VG4 — .env.example completeness

- **Positive:** `cp .env.example .env && docker compose config` → exit 0 with no "variable is not set" warning; every `${VAR}` referenced in `docker-compose.yml` resolves from `.env.example`.
- **Negative:** comment out one required variable in `.env` and re-run `docker compose config` → it emits the unset-variable warning / fails. Proves `.env.example` documents every variable the compose file references.

## Fitness Functions

Static-artifact inspections in `01-infrastructure/tests/contracts/`, each behavioral and **refutable**
(per `procedures/fitness-function.md`): a reviewer must be able to name the change that turns each
test red.

- **Every compose service declares a non-trivial healthcheck** (a `healthcheck` block with a `test`) → `tests/contracts/test_every_service_has_healthcheck.py` — Refute: add a service block with no `healthcheck` → the test fails. (Enforces the root Global Build Standard "every service in `docker-compose.yml` has a healthcheck".)
- **Service names conform to the Global Naming Convention** — lowercase kebab-case, and any service whose role maps to a naming-convention entry uses that exact name; the Phase-01 `canary` fixture is the only allow-listed non-catalog service → `tests/contracts/test_service_naming.py` — Refute: rename a service to `Postgres_PMS` (uppercase + underscore) or misspell a catalog name (`kafka-broker` instead of `kafka`) → the test fails.
- **Every service attaches to the shared `insureflow` network** (none left on the implicit default bridge) → `tests/contracts/test_shared_network.py` — Refute: add a service with no `networks:` key → the test fails.

These run in CI via the `fitness-functions` job in `.github/workflows/quality.yml`.

## Blast Radius

- **If the shared network / volume convention is wrong or renamed** → immediate: nothing inter-service resolves; cascading: every later phase's wiring breaks — Debezium cannot reach `postgres-pms` (03), Spark cannot reach `kafka` / `minio` (04), FastAPI cannot reach the online feature store (10a). All 13 downstream phases are blocked until it is fixed.
- **If the healthcheck pattern is wrong** (false-healthy cadence, or a port probe instead of a behavioral check) → immediate: nothing visibly breaks; cascading: later phases inherit false-positive health, so the service-health SLOs and chaos-recovery gates (Phase 12) report green on broken services. This is the most dangerous failure because it is silent.
- **If Terraform image pinning is wrong** (mutable tags instead of digests) → immediate: online builds still work; cascading: the 100%-offline guarantee breaks — a later offline `docker compose up` pulls a drifted or absent tag and the stack will not start reproducibly.
- **If `.env.example` is incomplete** → immediate: a fresh clone's `docker compose config` fails on unset variables; cascading: no phase can bring the stack up from a clean checkout.

## Chaos Scenarios

None — this phase has no chaos scenarios.

Reason: infrastructure-only. Per `chaos/CLAUDE.md` (Chaos Availability by Phase) the earliest scenario
becomes runnable from Phase 03 (CDC running) — every scenario perturbs data flow or a stateful service
that does not exist yet. Phase 01 has no data flow, and the canary is a stateless fixture. The
health-mechanism failure mode is already proven by the VG2 negative case.

## Gotchas

- **Terraform ↔ Compose boundary.** Compose owns the runtime substrate (network, volumes, services) so `docker compose up` stays single-command; Terraform owns *only* image provisioning + digest pinning. Do **not** make the network `external`, and do **not** let Terraform create `docker_container` resources — that path (Option A) was rejected because it breaks the single-command promise and adds a two-step bootstrap plus an external-network failure mode. See `decisions/adr-001`.
- **Healthcheck `start_period`.** Failures during `start_period` do not count toward `retries`. The VG2 negative case must wait until after `start_period` elapses before asserting `unhealthy`, or it will read `starting` and look like a pass.
- **"Offline" is a runtime property, not a build property.** Base images (`nginx:alpine`, `busybox`) and the Terraform Docker provider still download on the *first* run. Terraform digest-pinning is exactly what makes every *subsequent* run reproducibly offline — the same one-time-pull bargain root `CLAUDE.md` already accepts for the Ollama model. **Close the seam:** `docker-compose.yml` references the **same digest** Terraform stages (`image: nginx@sha256:<digest>`), never a floating tag — otherwise compose pulls a different (or absent) image than the one Terraform pinned, and the offline guarantee is a fiction.
- **CRLF on Windows.** A shell-based healthcheck `test` or any `.sh` helper authored on Windows can carry CRLF line endings that break `/bin/sh` inside a Linux container. Prefer the exec-form array for `test`, and guard shell scripts with `.gitattributes` (`*.sh text eol=lf`).
- **Multi-arch digest pinning.** A platform-specific digest pins one architecture; on a different host arch it will not resolve. Pin the **multi-arch index digest** (the tag's top-level digest), not a per-platform one, so the same config resolves on both amd64 and arm64.
- **Future refinement — NOT this phase.** Once real services exist, move the canary behind compose `profiles: ["smoke"]` so the production stack does not ship a stray nginx. It is left as a normal service in Phase 01 so the Validation Gate has a live behavioral target.
