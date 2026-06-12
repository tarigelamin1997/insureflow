# ERR-001 — Canary healthcheck fails on localhost (IPv6) resolution

## Status
Resolved

## Phase / Component
Phase 01 — Infrastructure. `docker-compose.yml` → `canary` service `healthcheck.test`.

## Layer
Infrastructure

## Type
connectivity

## Source
implementation

## First Observed
While running the VG2 positive criterion (`docker compose up -d` then polling
`docker inspect --format '{{.State.Health.Status}}' insureflow-canary`). Expected the canary to
reach `healthy` within `start_period + interval × retries`. Instead it stayed `starting` for ~70s
then flipped to `unhealthy` — the healthcheck was failing the whole time, even though nginx had
started and was serving.

## Error Description
Healthcheck command run manually inside the container:

```
$ wget -q -O /dev/null http://localhost/
wget: can't connect to remote host: Connection refused
```

nginx was up and listening, but only on IPv4:

```
$ netstat -ltn | grep ':80'
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN
```

`localhost` inside the container resolves to IPv6 only:

```
$ getent hosts localhost
::1               localhost  localhost
```

## Environment State
- Docker 29.5.3 (WSL2 backend), Compose v5.1.4
- Image: `nginx@sha256:8b1e78743a03dbb2c95171cc58639fef29abc8816598e27fb910ed2e621e589a` (nginx 1.31.1)
- `docker compose ps`: `insureflow-canary … Up About a minute (unhealthy)`, ports `0.0.0.0:8080->80/tcp`
- Healthcheck at time of error: `["CMD-SHELL", "wget -q -O /dev/null http://localhost/ || exit 1"]`

---

## Attempts

### Attempt 1
**What was tried:**
Original healthcheck targeted `http://localhost/`:
`test: ["CMD-SHELL", "wget -q -O /dev/null http://localhost/ || exit 1"]`

**Result:**
`wget: can't connect to remote host: Connection refused`; container never left `starting`, then went
`unhealthy`.

**Why it failed:**
The container's `/etc/hosts` maps `localhost` to `::1` (IPv6) only. nginx's default config listens on
IPv4 `0.0.0.0:80` and not on `[::]:80`, so a connection to `[::1]:80` is refused. wget did not fall
back to IPv4. The healthcheck command was therefore correct in *form* (fail-on-error) but pointed at
an address nothing was listening on.

---

## Resolution

**What worked:**
Target the loopback by explicit IPv4 address instead of the `localhost` name:
`test: ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1/ || exit 1"]`

Verified inside the container:
```
$ wget -q -O /dev/null http://127.0.0.1/ ; echo $?
0
$ curl -fsS -o /dev/null http://127.0.0.1/ ; echo $?
0
```

**Root cause:**
`localhost` → `::1` (IPv6) in the container, while nginx listens on IPv4 `0.0.0.0:80` only. The
name-vs-address mismatch, not the healthcheck logic, caused the connection refusal.

**Why previous attempts failed:**
Attempt 1 assumed `localhost` would resolve to `127.0.0.1`. In this image it resolves to `::1`, and
the server has no IPv6 listener. Any loopback healthcheck using the `localhost` *name* against an
IPv4-only listener has the same defect.

**Prevention:**
`procedures/docker-healthcheck.md` now mandates the explicit IPv4 loopback `http://127.0.0.1/` for
in-container HTTP healthchecks (with an IPv6/localhost note), so every later service inherits the
correct form rather than rediscovering this.

**Detection:**
The behavioral VG2 criterion ("canary must reach `healthy`") surfaced this before merge — a
presence-only check ("container is running") would have reported green on this exact broken state.
This is the concrete justification for the Gate Robustness Standard. Action taken: keep VG2 as a
**blocking positive** criterion (canary must actually reach `healthy`), and the prevention note above
is added to `docker-healthcheck.md`. No additional alert needed at Phase 01 — the gate is the detector.
