# ADR-002 — Standard healthcheck cadence via a shared anchor

## Status
Accepted

## Context
The root Global Build Standard requires every service in `docker-compose.yml` to declare a healthcheck.
Without a shared cadence, each phase would choose its own `interval` / `timeout` / `retries` /
`start_period`, producing inconsistent detection windows and flaky boots across the stack, and making
`depends_on: { condition: service_healthy }` ordering unreliable. The cadence must be defined once,
inherited platform-wide, and tunable per service.

## Decision
Define a top-level YAML anchor `x-healthcheck-defaults` in `docker-compose.yml` and merge it into every
service via `<<: *healthcheck-defaults`. Values: `interval: 10s`, `timeout: 5s`, `retries: 5`,
`start_period: 30s`. Rationale: `retries × interval = 5 × 10s = 50s` steady-state detection window —
long enough to absorb a one-off blip, short enough to detect a real stall well inside any SLO; `30s`
boot grace covers typical cold starts. Services override only what genuinely differs (a slow JVM
service bumps `start_period`). Every healthcheck `test` must be behavioral and fail-on-error, per
`procedures/docker-healthcheck.md`.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| Per-service ad-hoc healthcheck blocks (no shared anchor) | Guarantees drift and inconsistent detection windows across phases; nothing to audit against; the same cadence gets re-derived (differently) each time. |
| Rely on Docker's default cadence (omit the fields) | Docker defaults (`interval 30s`, `retries 3`, `start_period 0s`) give zero boot grace → false `unhealthy` flapping at boot, and hide the detection window. `procedures/validation-standard.md` forbids opaque, unreviewable gate behavior. |

## Consequences

### Makes easier
- Consistent, auditable health semantics across the whole stack; one place to tune the cadence.
- `depends_on: service_healthy` startup ordering is trustworthy because the cadence is known and uniform.

### Makes harder
- A service with genuinely different timing must remember to override the relevant field (documented in the procedure).

### Makes impossible
- N/A — overrides keep the anchor from constraining any real service.

### Impact on other phases
- Every later service merges this anchor and only overrides deltas.
- Phase 12 (Observability) SLO alerting builds on health signals that are uniform and meaningful because of this cadence.
