# Procedure: Error Logging

## Guiding Principle

Every error encountered during implementation is a permanent, documented record. An error file is a living document — it is opened when the error is first observed and updated with every attempt until it is resolved. It is never deleted.

The standing rule across all phases: **before attempting any fix, read the `errors/` directory of the relevant phase and the root `errors/` directory.** A solution that reintroduces a known failed approach is worse than no solution — it consumes time and context that has already been paid for once.

If it happened, it is logged. If it is logged, it is read before the next attempt.

---

## Error File Locations

| Error type | Location |
|---|---|
| Contained within one phase | `NN-phase/errors/ERR-NNN-description.md` |
| Affects multiple phases or infrastructure-wide | `errors/ERR-NNN-description.md` (repo root) |
| Surfaced by a chaos scenario | the **owning phase's** `NN-phase/errors/` (or root `errors/` if cross-phase), with `Source: chaos-discovered` and a back-reference to the `ST-NNN` document |

Chaos-discovered errors live with the phase that owns the fix — not in a separate `chaos/` location.
A chaos scenario finds a defect in some phase's behaviour; the error belongs to that phase so
`/close-phase` (which scans the phase's `errors/` and root `errors/`) blocks on it. The link back
to the scenario is the `ST-NNN` reference plus `Source: chaos-discovered`.

When in doubt, place it in the phase where it was first observed. Cross-phase errors can be moved to root `errors/` once the scope is confirmed.

---

## Naming Convention

`ERR-NNN-short-description.md`

- `NNN` = three-digit sequence, scoped per directory, starting at 001
- Short description = kebab-case, 3–5 words, describes the error not the fix
- Examples: `ERR-001-debezium-connector-not-starting.md`, `ERR-002-iceberg-write-permission-denied.md`

---

## Error File Template

```markdown
# ERR-NNN — Short Description

## Status
Open

## Phase / Component
[Phase name and specific component: service name, script, config file, dbt model, etc.]

## Layer
[Bronze / Silver / Gold / CDC / Infrastructure / Governance / AI / Serving / Observability / Cross-cutting]

## Type
[data-corruption / connectivity / config / dependency / performance / schema / auth / unknown]

## Source
[implementation / chaos-discovered]

## First Observed
[Context: what was being implemented when this error first appeared.
 Include: what command was run, what was expected, what happened instead.]

## Error Description
[Exact error message, stack trace, or behaviour description.
 Paste verbatim — do not paraphrase error messages.]

## Environment State
[What was running at the time: docker compose ps output, relevant config values,
 Python/tool versions, any recent changes made before the error appeared.]

---

## Attempts

### Attempt 1
**What was tried:**
[Exact change made — command, config diff, code change.]

**Result:**
[What happened after the attempt. Exact error if still failing.]

**Why it failed:**
[Root cause of this specific attempt's failure, if known.]

---

## Resolution
<!-- Fill this section only when Status changes to Resolved -->

**What worked:**
[Exact fix — command, config change, code change.]

**Root cause:**
[The actual underlying cause of the original error.]

**Why previous attempts failed:**
[Specifically what was wrong with each failed attempt. This is the section
 future Claude sessions must read before proposing a solution.]

**Prevention:**
[What guard, check, ADR update, or config change prevents this from recurring.]

**Detection:**
[What alert, healthcheck, Soda check, fitness function, or Prometheus rule would have
 surfaced this error earlier — before it became a blocker. Always results in a concrete
 action: add X to Y. If nothing would have caught it earlier, explain why and whether
 that gap should be accepted or closed.]
```

---

## Workflow

### When an error occurs
1. Run `/new-error` — creates the file from template with pre-filled metadata
2. Paste the exact error message into `## Error Description`
3. Document the environment state

### During active debugging
- Edit the error file directly — add a new `### Attempt N` section for each attempt
- Do not wait until an attempt is complete to document it — log what was tried as you go
- Each attempt section must have all three fields: what was tried, result, why it failed

### When resolved
- Run `/resolve-error ERR-NNN` — fills the Resolution section and changes Status to Resolved
- The file is never deleted — it becomes a permanent reference

### Before attempting any fix
1. Read every file in `NN-phase/errors/` for the current phase
2. Read every file in root `errors/`
3. Check if the current error has already been seen (same stack trace, same component)
4. If yes — read the previous attempts before proposing anything new

---

## Rules

- **Status must always be current.** An error that is resolved but still marked Open is misleading. Run `/resolve-error` as soon as the fix is confirmed working.
- **Never summarise error messages.** Paste verbatim. Paraphrased errors are unsearchable and lose diagnostic information.
- **Every attempt gets its own section.** A single section with "we tried several things" is not acceptable.
- **"Why it failed" is mandatory for closed attempts.** If you don't know why it failed, write "unknown — needs investigation" rather than leaving it blank.
- **A phase cannot close with open errors.** `/close-phase` checks `errors/` and blocks if any file has `Status: Open`.
- **Detection is mandatory in every resolved error.** Writing "nothing would have caught this earlier" requires a justification. The default assumption is that a detection gap exists and should be closed — a new alert, check, or fitness function is the expected output.
- **Layer, Type, and Source are required.** Every new error file must have these three fields filled before the first attempt is logged. `Source: chaos-discovered` marks errors found during chaos testing — pre-incidents that would have reached production undetected.
