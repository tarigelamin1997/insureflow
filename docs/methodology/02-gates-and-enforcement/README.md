# 02 — Gates & Enforcement

This is the spine of the methodology. If you read only one topic, read this one.

## What

A **gate** is a command that refuses to let work proceed unless specific conditions are met. The phase
lifecycle has three:

- **`/start-phase`** — the entry gate. Verifies prerequisites are closed, the phase `CLAUDE.md` is
  complete, every required procedure exists (authoring any that were deferred to this phase), fitness
  stubs exist, and every validation criterion is strong (see [04 — Validation](../04-validation/)).
  Only then does the phase go `🚧 In progress`.
- **`/review-phase`** — the code gate. Static analysis, secret scan, unit tests, fitness functions
  (no `xfail` stubs survive), and each criterion's negative case actually run.
- **`/close-phase`** — the exit gate. Documentation complete, ADRs present, validation gate run
  (positive *and* negative cases), no open errors, contract verified against upstream, chaos
  scenarios passed, phase index updated to `✅`.

Three **ledgers** hold the cross-phase state that the gates check:

- [`procedures/README.md`](../../../procedures/README.md) — the procedure registry: which standards
  are written, which are deferred to a future phase.
- [`CONTRACTS.md`](../../../CONTRACTS.md) — the interface ledger: every phase's `Produces` → who consumes it.
- The six-angle coverage matrix in [`chaos/CLAUDE.md`](../../../chaos/CLAUDE.md) — which chaos angle is
  covered by which scenario.

## Why

**The core principle: a standard not wired into a command is a suggestion.**

The original foundation had a revealing asymmetry. *Documentation* was rigorously gated — every ADR,
every error, every `CLAUDE.md` section had an exit check. But *behavior* was gated only by convention:
the procedures said "run the chaos scenarios at the close gate" and "validate contracts," but no
command actually verified either. A rule that no command enforces is a rule the system can sail
straight past while still reporting green.

That asymmetry is the thing this topic exists to kill. Three failure modes follow from it, and each
has a fix:

| Failure mode | Why it happens | The fix |
|---|---|---|
| A gate is described but never enforced | The rule lives in prose, not a command | Wire it into a command — chaos → `/close-phase` Check 9; contracts → Check 8 |
| Cross-phase state drifts | Procedure status / contracts / coverage live as scattered prose | One **ledger** per concern, as the single source of truth |
| Rules that must hold *before* code are unenforced | No entry gate existed | Add `/start-phase` for entry/exit symmetry |

**Why ledgers instead of prose?** Because the root `CLAUDE.md` is navigation-only by design — putting
maintained, cross-phase state in it guarantees drift. A dedicated ledger keeps the state where it is
read and updated, and gives the gate one authoritative thing to check. When the procedures tree in
`CLAUDE.md` once listed files that didn't exist and omitted three that did, that was prose drift; the
registry is the cure.

**Why an upstream contract check?** In a sequential build, when a phase closes its downstream consumer
doesn't exist yet — so a *downstream*-looking contract check is inert. The only contract you can verify
at close time is this phase's dependency on its already-closed producers. So Check 8 verifies
`Consumes` against the upstream `Produces` recorded in `CONTRACTS.md`, then appends this phase's own
`Produces` row. See [01 — Phase Model](../01-phase-model/) for why the sequencing forces this.

## The four-layer enforcement pattern

When a standard must hold across the *whole* project, wiring it into one command isn't enough — it has
to be impossible to bypass at any stage. The pattern, proven on the Gate Robustness Standard
([adr-001](../../../decisions/adr-001-validation-robustness-standard.md)):

```
DEFINE ONCE ──▶ INHERIT VIA TEMPLATE ──▶ ENFORCE AT EVERY GATE ──▶ AUDIT CONTINUOUSLY
 one canonical    every phase CLAUDE.md     entry / code / exit       a standing invariant
 standard file    inherits it for free      gates each check it       re-checks it forever
```

Each layer closes a different bypass: definition prevents ambiguity, the template makes adoption
automatic, the gates prevent skipping, and the audit prevents rot.

**Auditing the foundation itself.** The foundation can drift like anything else, so it audits itself.
[`/audit-foundation`](../../../.claude/commands/audit-foundation.md) runs a read-only sweep —
registry vs. disk, ledger vs. phase contracts, chaos matrix vs. scenarios, every gate-rule mapped to
the command that enforces it. It turns a one-time consistency check into a standing gate, run before
every close and after any foundation edit.

## So what

- **You cannot reach "done" by being plausible.** "Done" is a machine-checkable state, not a feeling.
  A phase can't close with unrun chaos, unverified contracts, open errors, or weak validation criteria.
- **The boundary the gates can't cross is named, not hidden.** Gates force the right checks to *exist
  and run*; they can't judge whether a check is *strong*. That residual — the quality of the criteria
  themselves — is closed separately by the Gate Robustness Standard in [04 — Validation](../04-validation/).
- **Every new "rule" must answer one question:** which command enforces it? If the answer is "none,"
  it isn't a rule yet — it's a suggestion, and the methodology says to either wire it or drop it.

## Where this lives in the repo

- The foundation decision: [`decisions/adr-000-foundation-airtightness.md`](../../../decisions/adr-000-foundation-airtightness.md).
- The gates: [`.claude/commands/`](../../../.claude/commands/) — `start-phase`, `review-phase`, `close-phase`.
- The ledgers: `procedures/README.md`, `CONTRACTS.md`, `chaos/CLAUDE.md`.
- The self-audit: [`procedures/foundation-audit.md`](../../../procedures/foundation-audit.md).
