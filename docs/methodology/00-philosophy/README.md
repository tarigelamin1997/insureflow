# 00 — Philosophy: Documentation as Infrastructure

## What

Every decision, the reasoning behind it, and the implications of every tradeoff live **in the
files** — not in anyone's memory, not in an external tool, not implied by the code. A document is
not a summary written after the work; it is part of the work, held to the same bar as the code.

Concretely, every document in this repo — phase `CLAUDE.md` files, ADRs, READMEs, procedures —
captures three layers:

- **What** — the concrete output: the implementation, the configuration, the end state.
- **Why** — the reasoning: the constraints that shaped the choice, and what was rejected.
- **So what** — the implications: what this enables downstream, and what it forecloses.

A document that answers *what* without *why* is incomplete. An ADR without consequences is
incomplete. A phase `CLAUDE.md` with a placeholder section is, by definition, not ready for
implementation.

## Why

Two non-negotiable goals force this standard. Neither is achievable if the reasoning lives anywhere
but the files.

**1. Public reproducibility.** This is a public portfolio repository. The test it must pass: a
stranger clones it, reads the docs, and can reproduce the system *and understand why it was built
this way* — without asking a single question. The moment a critical "why" exists only in a
conversation, a Slack thread, or someone's head, that test fails. The reasoning is the product as
much as the platform is.

**2. Session independence.** Any working session — a new engineer, or a fresh Claude instance with
no conversation history — must be able to pick up any phase and operate with full context from that
phase's `CLAUDE.md` alone. No cross-phase context hunting. No reliance on what was said earlier. This
is what makes the work *resumable*: you can throw away a full context window and lose nothing,
because nothing important was ever only in the window. The repository is the memory.

These two goals are why we can run **a fresh session per stage** and keep each session's context
small and dense — the durable state was never in the context to begin with.

## So what

- **Placeholders are blockers, not drafts.** A `[TO BE FILLED]` section means the work isn't ready;
  the entry gate (`/start-phase`) refuses to let implementation begin until it's gone.
- **The reasoning compounds.** Because every "why" is written down, later phases inherit context
  instead of re-deriving it. The cost of writing the reasoning once is paid back every time someone
  would otherwise have had to reconstruct it.
- **It sets the communication standard.** Direct and precise, conclusion first, bullets over
  paragraphs, tables for comparison, and **intellectual honesty over politeness** — if something is
  wrong in a review or an ADR, the standard is to say so plainly. Filler is a defect because it
  dilutes the signal a future reader depends on.

## Where this lives in the repo

- The standard itself: the **Documentation Philosophy** section of root [`CLAUDE.md`](../../../CLAUDE.md).
- The phase-document contract: [`procedures/phase-claude-md.md`](../../../procedures/phase-claude-md.md).
- Everything else in this handbook is an application of this philosophy to a specific part of the system.
