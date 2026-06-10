# InsureFlow Methodology — The Rationale Handbook

This is the **why** behind how InsureFlow is built. The rest of the repo tells you *what* to do
(`procedures/`), *what was decided* (`decisions/`), and *where things live* (`CLAUDE.md`). This
handbook explains *why the way of working exists at all* — what problem each guardrail solves, what
it would cost to skip it, and what it forecloses.

It exists for two readers:
- **The contributor** (a future engineer, or a fresh Claude session) who needs to understand the
  reasoning before changing the system, so they don't quietly dismantle a guardrail that's load-bearing.
- **The reviewer** (e.g. an architect evaluating this as a portfolio) who wants to see not just a
  working platform, but the engineering judgment behind how it was built.

## The through-line

One sentence holds the whole methodology together:

> **A standard not wired into a command is a suggestion.**

Everything here is an application of that idea. We don't trust that the right thing will happen
because it's written down — we make the system *unable* to proceed when the right thing hasn't
happened. Documentation captures the reasoning; gates enforce the behavior; ledgers keep the shared
state honest; audits prove the whole thing still holds.

A second principle sits underneath it:

> **Documentation as infrastructure** — the state of every decision, and the reasoning behind it,
> lives in the files. Not in memory, not in a tool, not implied by the code.

Together they produce a system that is *reproducible from the documentation alone* and *self-enforcing*.

## How to read this

Each topic is a numbered folder. Read them in order for the full picture, or jump to the one you
need. Every topic doc follows the repo's own standard — **What** (the practice), **Why** (the
reasoning and what it replaces), **So what** (what it enables or forecloses) — and links down to the
concrete procedures, commands, and ADRs that implement it.

| # | Topic | The question it answers |
|---|---|---|
| [00](00-philosophy/) | Philosophy | Why is documentation treated as infrastructure, and what standard must every document meet? |
| [01](01-phase-model/) | The Phase Model | Why is the work cut into self-contained phases, and what is the lifecycle of one? |
| [02](02-gates-and-enforcement/) | Gates & Enforcement | Why do stated rules get wired into commands, and how do the three gates + ledgers work? |
| [03](03-decisions/) | Decisions | Why is every non-trivial choice recorded as an ADR, and how is decision history preserved? |
| [04](04-validation/) | Validation & Quality | Why is the validation loop the highest-leverage thing we do, and what makes a gate *strong*? |
| [05](05-resilience/) | Resilience & Chaos | Why do we deliberately break the platform before trusting it? |
| [06](06-error-discipline/) | Error Discipline | Why is every failure logged, never deleted, and read before the next fix? |

## What this is not

- It is **not** a how-to. The procedures in `procedures/` are the how-to; this is the why-to.
- It is **not** the decision record. ADRs in `decisions/` are terse and authoritative; this is the
  narrative that connects them.
- It does **not** restate the architecture. The Medallion lakehouse design lives in `README.md`,
  `CLAUDE.md`, and the phase ADRs.

When in doubt, this handbook should make you understand the system well enough to *defend* a guardrail
to someone who wants to remove it — or to remove it deliberately, knowing exactly what you give up.
