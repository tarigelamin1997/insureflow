# Procedure: Docker Healthcheck

## Guiding Principle

A healthcheck is a **behavioral** assertion, not a liveness probe. It must exercise the service
through its real interface and **exit non-zero the moment the service cannot do its job** — even while
the container process is still running and its port is still open. A healthcheck that returns `0` on a
broken service is worse than no healthcheck: it reports green on a dead service and every
`depends_on: { condition: service_healthy }` downstream trusts the lie.

This is the `procedures/validation-standard.md` Rule 1 (behavioral, not presence/liveness) applied to
Docker. The most common way it is violated is subtle and worth stating up front:

> `curl http://localhost/` exits **0** on an HTTP 500 or 404 — it succeeded in *talking* to the
> server. `curl -f http://localhost/` exits **22** on any response ≥ 400. **The `-f` is the gate.**
> Without fail-on-error, the healthcheck is a port probe wearing an HTTP costume.

Every healthcheck in `docker-compose.yml` follows the patterns below. The root Global Build Standard
requires one on **every** service; the Phase 01 fitness function
`test_every_service_has_healthcheck.py` enforces it.

---

## The Contract Every Healthcheck Must Meet

1. **Fail-on-error.** The `test` command exits non-zero whenever the service cannot serve a real
   request. Exit `0` only when it genuinely served one. (HTTP: `curl -f` / fail-on-non-2xx wget.
   DB: a real query, not just "accepts connections". Broker: a real API call.)
2. **Behavioral, not a port probe.** Never use `nc -z host port` / a bare TCP connect as a service's
   healthcheck when a protocol-level check exists — an open port says nothing about whether the app
   behind it works. A TCP probe is acceptable **only** when the service speaks a protocol with no
   in-container client available, and then it carries `Negative case: N/A — <reason>` in the gate.
3. **Bounded and explicit.** `interval`, `timeout`, `retries`, and `start_period` are set
   explicitly — never left to Docker defaults. The detection window is `interval × retries`; the
   boot grace is `start_period`.
4. **Self-contained / offline.** The check runs entirely inside the container against `localhost`
   (or a unix socket). It never reaches an external network — that would both break the offline
   guarantee and make health depend on something outside the stack.
5. **Exec-form `test`, LF line endings.** Prefer the `CMD`/`CMD-SHELL` array form. Any shell helper
   script is committed with `eol=lf` (`.gitattributes`) so CRLF authored on Windows does not break
   `/bin/sh` inside a Linux container.

---

## The Standard Cadence — `x-healthcheck-defaults`

Declared once as a top-level YAML anchor in `docker-compose.yml` and merged into each service, so the
whole platform shares one cadence and a service only overrides what is genuinely different.

```yaml
x-healthcheck-defaults: &healthcheck-defaults
  interval: 10s        # how often the check runs once healthy
  timeout: 5s          # a single check must answer within this
  retries: 5           # consecutive failures before the container is marked unhealthy
  start_period: 30s    # boot grace — failures here do NOT count toward retries
```

| Field | Value | Why |
|---|---|---|
| `interval` | `10s` | Fast enough to detect a stall promptly without hammering the service |
| `timeout` | `5s` | A check slower than this is itself a symptom — treat as a failure |
| `retries` | `5` | `5 × 10s = 50s` steady-state detection window — absorbs one-off blips, still well under any SLO |
| `start_period` | `30s` | Grace for slow starters (Kafka, Postgres, OpenMetadata). **Tune per service** — a JVM service may need `60s`+ |

`start_period` is the field people forget: during it, a failing check reports `starting`, **not**
`unhealthy`, and does not consume a retry. Too short → false `unhealthy` flapping at boot; too long →
slow detection of a genuinely failed start. Size it to just past the service's real cold-start time.

A service inherits and tunes:

```yaml
services:
  some-service:
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      start_period: 60s        # override: this one is a slow JVM starter
```

---

## Patterns by Service Type

Every pattern below is **fail-on-error**. Pick by what the service actually speaks.

### HTTP services — the default

Covers the Phase 01 `canary` (nginx) and later `fastapi`, `superset`, `openmetadata`, `grafana`,
`schema-registry`, MinIO, Marquez.

```yaml
# Preferred — curl with --fail (-f): exits 22 on any HTTP >= 400.
test: ["CMD-SHELL", "curl -f http://127.0.0.1:8080/health || exit 1"]
```

When the image has no `curl`, use a fail-on-error wget (`wget` is present on Alpine images). It
returns non-zero on a connection failure **and** on an HTTP error status, so it satisfies
fail-on-non-200:

```yaml
# Fallback — wget, fail-on-error. Used by the Phase 01 canary.
test: ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1/ || exit 1"]
```

> **Use `127.0.0.1`, not `localhost`, for in-container loopback.** In many images `localhost`
> resolves to IPv6 `::1` only, while the server listens on IPv4 `0.0.0.0` — so a `localhost`
> healthcheck is *refused* while the service is perfectly healthy (it reads `unhealthy` on a working
> stack). This bit the Phase 01 canary; see `01-infrastructure/errors/ERR-001`. Always target the
> explicit IPv4 loopback in a healthcheck.

> **Phase 01 canary, concretely.** nginx serves `index.html` from a named volume. Removing the file
> (the VG2 negative case) makes nginx answer `403`/`404` — both ≥ 400 — so `wget -q -O /dev/null …`
> exits non-zero and the container goes `unhealthy` within `interval × retries`. If the check used
> plain `wget` or `curl` without `-f`, the 403/404 would still exit `0` and the negative case would
> **never fire**. That difference is the whole point of this procedure.

Endpoint choice: hit a real application path or a purpose-built `/health` route — not a static asset
that a misconfigured server might still return from cache.

### PostgreSQL (Phase 02 — `postgres-pms` / `postgres-cms` / `postgres-pfs`)

`pg_isready` only proves the server *accepts connections* — it does not prove it can execute SQL.
Run a real query so a server that is up but rejecting queries (bad auth, read-only, exhausted) is
caught:

```yaml
# Behavioral — runs a real query. Exits non-zero if the DB can't execute it.
test: ["CMD-SHELL", "psql -U \"$$POSTGRES_USER\" -d \"$$POSTGRES_DB\" -tAc 'SELECT 1' || exit 1"]
```

(`$$` escapes the `$` so Compose passes it to the container instead of interpolating it.)

### Kafka KRaft (Phase 03 — `kafka`)

A real broker API call — not a port probe. The broker can hold the port open while still forming the
KRaft quorum:

```yaml
test: ["CMD-SHELL", "kafka-broker-api-versions --bootstrap-server 127.0.0.1:9092 || exit 1"]
start_period: 60s   # KRaft quorum formation is slow
```

### Schema Registry (Phase 03 — `schema-registry`)

```yaml
test: ["CMD-SHELL", "curl -f http://127.0.0.1:8081/subjects || exit 1"]
```

### MinIO (Phase 04 — `minio`)

MinIO exposes its own health endpoints; use the liveness/readiness route, fail-on-error:

```yaml
test: ["CMD-SHELL", "curl -f http://127.0.0.1:9000/minio/health/live || exit 1"]
```

### TCP-only services with no in-container client (last resort)

Only when nothing richer is available in the image. Document the weakness in the gate with an
explicit `Negative case: N/A — <reason>`:

```yaml
# Weakest acceptable form — presence-ish. Justify in the Validation Gate.
test: ["CMD-SHELL", "nc -z localhost 5432 || exit 1"]
```

Prefer adding a small client to the image over shipping a port probe.

---

## Gating Startup Order on Health

`depends_on` with `condition: service_healthy` is only as trustworthy as the upstream healthcheck. A
liveness-only upstream check makes the dependent start before the upstream can actually serve — the
exact failure this procedure exists to prevent.

```yaml
services:
  debezium:
    depends_on:
      postgres-pms:
        condition: service_healthy   # trustworthy ONLY because postgres' check runs SELECT 1
```

---

## The Negative Case — proving the healthcheck fires

Per `procedures/validation-standard.md` Rule 2, the "service health" criterion's negative case is a
real injection, not a claim. Reuse what exists:

| Service | Inject the failure | Expected response |
|---|---|---|
| Canary (nginx) | `docker compose exec canary rm /usr/share/nginx/html/index.html` | `403`/`404` → check exits non-zero → `unhealthy` within `interval × retries` |
| Postgres | revoke query ability / stop the server | `SELECT 1` fails → `unhealthy` |
| Any service | stop a dependency it needs | check fails → `unhealthy`, and dependents' `service_healthy` gate blocks |

Always wait past `start_period` before asserting `unhealthy` — during the grace window a failing
check reports `starting`, which looks like a pass.

---

## What Is Never Acceptable

- **A healthcheck without fail-on-error** — `curl` without `-f`, or any command that exits `0` on a
  500/404. It reports green on a broken service. This is the single most common violation.
- **A port probe (`nc -z`, bare TCP connect) where a protocol-level check exists** — an open port is
  presence, not behavior.
- **Relying on Docker default `interval` / `timeout` / `retries` / `start_period`** — they must be
  explicit, so the detection window and boot grace are visible and reviewable.
- **A missing `start_period` on a slow starter** — guarantees false `unhealthy` flapping at boot and
  trains operators to ignore the status.
- **A healthcheck that reaches an external network** — breaks the offline guarantee and ties health
  to something outside the stack.
- **A service in `docker-compose.yml` with no `healthcheck` at all** — fails the root Global Build
  Standard and the Phase 01 `test_every_service_has_healthcheck.py` fitness function.
