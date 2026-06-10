# 06 — Error Discipline

## What

Every failure encountered during implementation is logged as a permanent `ERR-NNN` file — opened when
the error is first observed, updated with every attempt, and **never deleted**. It lives in the owning
phase's `errors/` (or root `errors/` if cross-phase). Each error carries `Layer`, `Type`, and `Source`
tags, a verbatim error message (never paraphrased), and — once resolved — a Resolution section with
root cause, why each previous attempt failed, prevention, and **detection**.

The standing rule, enforced across every phase: **before attempting any fix, read the relevant
`errors/` directories.**

## Why

**Why log every failure, even the ones you fix in five minutes?** Because the same failure costs time
twice if the second person doesn't know the first one solved it. An error log turns debugging from a
private, disposable act into a shared, compounding asset. A solution that reintroduces a known-failed
approach is a *documentation* failure, not an engineering one — the information existed and wasn't read.

**Why "why it failed" is mandatory for every attempt.** The list of what *didn't* work is often more
valuable than what did. "Restarting the container doesn't recreate the replication slot — the slot
persists in Postgres and must be dropped first" is the sentence that saves the next session an hour. An
attempt section without a cause ("unknown — needs investigation" is acceptable; blank is not) throws
that value away.

**Why error messages are pasted verbatim, never summarized.** A paraphrased error is unsearchable and
loses the exact tokens — the slot name, the error code, the stack frame — that let a future session
match "I've seen this before." The diagnostic value is in the specifics.

**Why the Detection field is mandatory on every resolution.** Fixing the error is only half the lesson;
the other half is *what would have caught it earlier* — a healthcheck, a Soda check, a fitness function,
a Prometheus rule. The default assumption is that a detection gap exists and should be closed; writing
"nothing would have caught this" requires a justification. This is what turns a one-off fix into a
permanent improvement to the validation surface — and it's the same instinct as the negative-case rule
in [04 — Validation](../04-validation/): don't just fix it, prove you'll see it next time.

**Why the `Source: chaos-discovered` tag.** It marks pre-incidents — failures a chaos scenario surfaced
that would otherwise have reached production undetected. Distinguishing these from implementation errors
tells you something real: how much of your reliability you owe to having broken things on purpose.

## So what

- **A phase cannot close with open errors.** `/close-phase` scans the phase's `errors/` and root
  `errors/` and blocks on any `Status: Open`. Unresolved failures can't be left behind as someone
  else's problem.
- **The error log feeds back into the gates.** Every Detection field is a candidate new check; over
  time the validation surface grows from the failures the system actually hit, not just the ones
  imagined up front.
- **Errors live with the fix, not in a silo.** Chaos-discovered errors go to the owning phase, not a
  separate chaos directory — so the phase that must fix the behavior is the phase whose close gate
  blocks on it. State lives where it's actioned.

## Where this lives in the repo

- The standard, template, and workflow: [`procedures/error-logging.md`](../../../procedures/error-logging.md).
- The commands: [`/new-error`](../../../.claude/commands/new-error.md), [`/resolve-error`](../../../.claude/commands/resolve-error.md).
- The close-gate check: `/close-phase` Check 6.
