# Procedure: ADR (Architecture Decision Record)

## Guiding Principle

An ADR is a permanent record of thought process, not just outcome. The goal is that anyone reading it — months later, with no prior context — understands not just what was decided, but why the alternatives failed, what constraints existed, and what the decision makes possible or impossible going forward. If the reasoning can't be reconstructed from the ADR alone, the ADR is incomplete.

---

Every non-trivial architectural or technical decision gets an ADR. Written at decision time — not after implementation, not after a phase is complete. An ADR is a permanent record of why a choice was made, what was rejected, and what that choice makes easier, harder, or impossible.

ADRs live in the phase directory that owns the decision: `NN-phase-name/decisions/adr-NNN-short-title.md`

---

## When to Write an ADR

Write an ADR when:
- You are choosing between two or more real alternatives
- The decision has consequences for other phases or services
- A future engineer (or Claude instance) reading the code would reasonably ask "why did they do it this way?"
- You are diverging from a common/obvious approach
- The decision involves a version pin, a config value, or a pattern that must stay consistent across the project
- The build diverged from the design — the original approach was planned but discarded mid-implementation. Write the ADR retroactively. Status: `Retroactive`. Context captures what was originally planned and why it was abandoned.

Do NOT write an ADR for:
- Obvious implementation details with no alternatives (e.g., "use a for loop")
- Decisions already locked at project level in root `CLAUDE.md`
- Cosmetic or naming choices that have no architectural consequence

---

## Numbering Convention

Format: `adr-NNN-short-title.md`

- NNN = three-digit sequence, scoped per phase, starting at 001
- Short title = kebab-case, 3–5 words, describes the decision not the outcome
- Examples: `adr-001-postgres-replication-slot-strategy.md`, `adr-002-avro-vs-json-schema.md`

---

## Full Template

```markdown
# ADR-NNN — Title

## Status
Accepted

## Context
[What situation forced this decision. What constraints exist that make this non-trivial.
 Include: the specific requirement or problem being solved, any hard constraints
 (offline-only, no paid APIs, cloud-agnostic), and why the obvious default doesn't work here.
 2–5 sentences. No bullet points — this is a narrative.]

## Decision
[Exactly what was chosen. How it will be implemented in this phase.
 Be precise: tool name + version + configuration approach + integration pattern.
 This section should be specific enough that someone can implement it without asking questions.]

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| [Alternative 1] | [Specific reason it was rejected for this project] |
| [Alternative 2] | [Specific reason it was rejected for this project] |

## Consequences

### Makes easier
- [What becomes simpler, faster, or more reliable because of this decision]

### Makes harder
- [What becomes more complex, slower, or more fragile because of this decision]

### Makes impossible
- [What this decision forecloses — things that cannot be done without reversing this decision]

### Impact on other phases
- [Which downstream phases are affected, and how]
- [Which upstream phases this depends on being stable]
```

---

## Field Rules

**Status** — use exactly one of: `Proposed`, `Accepted`, `Retroactive`, `Deprecated`, `Superseded by ADR-NNN`. Start every ADR as `Accepted` unless you are writing it before the decision is finalized. Use `Retroactive` when the ADR is written mid-build to document a divergence from the original design — the decision has already been implemented, and the ADR reconstructs the reasoning. A Retroactive ADR is permanent and has the same standing as an Accepted one.

**Context** — explain the problem, not the solution. A reader should understand why a decision was necessary before reaching the Decision section. Include the constraint that ruled out the default.

**Decision** — be concrete. "Use Debezium 2.7 with pgoutput plugin, one connector per source database, slot name pattern `debezium_{db}`" is correct. "Use Debezium for CDC" is not.

**Alternatives Considered** — minimum two rows. "We considered nothing else" means the ADR should not exist. Rejection reasons must be specific to InsureFlow's constraints — not generic.

**Consequences / Makes impossible** — this is the most important field for cross-phase safety. If this decision forecloses an option another phase might need, flag it here. Other phases can reference this ADR when they hit that constraint.

**Impact on other phases** — name the phases explicitly. "Affects Phase 05" is acceptable shorthand but include what specifically is affected.

---

## Updating an ADR

Never edit the body of an Accepted ADR to change its decision. Instead:
1. Change its Status to `Superseded by ADR-NNN`
2. Write a new ADR with the revised decision
3. In the new ADR's Context, reference why the original decision is being reversed

This preserves the reasoning history.

---

## Example: Minimal Acceptable ADR

```markdown
# ADR-001 — Kafka Schema Format

## Status
Accepted

## Context
Debezium publishes change events to Kafka. Downstream Spark consumers need to deserialize
these events reliably across schema evolution. The project is 100% offline — no external
schema registry services. Schema evolution will occur as source PostgreSQL tables gain
new columns during Phase 08 (data contracts + drift detection).

## Decision
Use Avro encoding with Confluent Schema Registry (local Docker instance, no auth).
All Debezium connectors configured with `value.converter=io.confluent.kafka.serializers.KafkaAvroSerializer`.
Schema registry runs as service `schema-registry` on port 8081.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| JSON (no schema registry) | No schema enforcement — breaking changes in source schema would silently corrupt Bronze writes |
| Protobuf | Better performance but no native Debezium support without custom converter; added complexity with no offline benefit |

## Consequences

### Makes easier
- Schema evolution is tracked automatically — additive changes (new columns) are handled without code changes
- Spark consumers can use generated Avro classes for type safety

### Makes harder
- Schema registry becomes a dependency for all producers and consumers — if it's down, CDC stops
- Local debugging requires running schema-registry container even for simple tests

### Makes impossible
- Cannot swap to a schema-registry-less approach (plain JSON Kafka) without rewriting all connectors and consumers

### Impact on other phases
- Phase 04 (Bronze): Spark must include `confluent-kafka` and Avro deserializer dependencies
- Phase 05 (Silver): Same dependency requirement
- Phase 08 (Data Contracts): Schema registry becomes part of the contract enforcement surface
```
