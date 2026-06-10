# 01 — The Phase Model

## What

The platform is built as 14 sequential phases (01 Infrastructure → 12 Observability, with 10a/10b/10c
for the AI layers). Each phase is a **self-contained conviction**: it has its own `CLAUDE.md` (full
context), `README.md`, `decisions/` (local ADRs), `errors/`, and `tests/` (`unit/`, `integration/`,
`contracts/`). No phase requires reading another phase's files to be understood or implemented.

Each phase moves through a fixed lifecycle:

```
/new-phase ──▶ fill CLAUDE.md ──▶ /start-phase ──▶ implement ──▶ /review-phase ──▶ /run-chaos ──▶ /close-phase
 scaffold       define the spec    ENTRY GATE       build         CODE GATE         resilience      EXIT GATE
   ⬜                                  🚧                                                                ✅
```

The phase index in root `CLAUDE.md` tracks state: `⬜ Not started` → `🚧 In progress` (set by
`/start-phase`) → `✅ Complete` (set by `/close-phase`).

## Why

**Why phases at all — why not build the platform as one continuous effort?** Because a 12-layer data
platform has too much surface to hold in one coherent context, and because the goals of *session
independence* and *blast-radius isolation* require hard boundaries. Cutting the work into
self-contained units means:

- Any unit can be picked up cold (the session-independence goal from [00 — Philosophy](../00-philosophy/)).
- A failure or a bad decision is contained to its phase, not smeared across the whole build.
- The interface between phases is explicit (see [02 — Gates](../02-gates-and-enforcement/) on the
  contract ledger), so integration is designed, not discovered.

**Why "conviction"?** Each phase directory is meant to argue for itself — it states what it builds,
why it's built that way, what it produces for downstream, and what breaks if it fails. It is not a
folder of files; it is a defensible position.

**Why the entry gate — why isn't scaffolding enough?** This is the subtle one. The lifecycle used to
have two exit gates (`/review-phase`, `/close-phase`) and *zero* entry gate. That left three rules as
policy without enforcement: "write the spec before code," "prerequisites must be met," and "author
this phase's deferred procedures first." `/start-phase` exists to make the lifecycle **symmetric** —
one gate guarding the entrance, two guarding the exit — so a phase cannot *begin* in an unready state
any more than it can *end* in one. The reasoning is recorded in
[`adr-000`](../../../decisions/adr-000-foundation-airtightness.md).

## So what

- **Spec-first, not first-shot.** The phase `CLAUDE.md` — the objectives, interface contract,
  validation gate, fitness functions — is written and gated *before* any code. Implementation aims at
  a defined target; "done" is when the gates pass, not when it feels done. The generation of code is
  the easy part once the spec and context are right.
- **Phases close before some of their validators exist.** Observability (Phase 12) measures phases
  04–11, so those phases ship before their SLO alerting is built. This is handled honestly: SLO-based
  criteria in pre-12 phases are marked `[validated at Phase 12]` and exercised retroactively when 12
  closes. The phase model makes this dependency explicit rather than pretending every check can run
  at every phase's own close.
- **Sequential build shapes the contract check.** Because phases are built in order, when a phase
  closes its *downstream* consumer doesn't exist yet — so the contract gate is **upstream-oriented**
  (does this phase's `Consumes` match the `Produces` of already-closed phases?). The phase model is
  why that orientation is correct; see [02 — Gates](../02-gates-and-enforcement/).

## Where this lives in the repo

- The lifecycle commands: [`.claude/commands/`](../../../.claude/commands/) — `new-phase`,
  `start-phase`, `review-phase`, `run-chaos`, `close-phase`.
- The phase-document contract: [`procedures/phase-claude-md.md`](../../../procedures/phase-claude-md.md).
- The phase index and status legend: root [`CLAUDE.md`](../../../CLAUDE.md).
