List and verify the required fitness functions for the current phase.

Arguments: phase identifier, e.g. `04-bronze-layer`. If no argument is provided, ask which phase to check.

## Steps

1. Read `NN-phase-name/CLAUDE.md` — specifically the `## Fitness Functions` and `## What This Builds` sections.

2. Read `procedures/fitness-function.md` for the standard patterns applicable to this phase's type.

3. List every fitness function that SHOULD exist for this phase based on:
   - What the phase builds (layer type, services involved, data it handles)
   - The architectural properties that must hold (from root `CLAUDE.md` validation architecture section)
   - Any phase-specific properties declared in the phase CLAUDE.md

4. For each required fitness function:
   - Check if it is listed in the phase `## Fitness Functions` section
   - Check if the corresponding file exists in `tests/contracts/`
   - If the file exists, report its current implementation (read it)

5. Report as a table:

| Fitness Function | In CLAUDE.md | File Exists | Implemented |
|---|---|---|---|
| [property description] | YES/NO | YES/NO | YES/NO/PARTIAL |

6. For any fitness function that is missing or not implemented, write a stub test file at the correct path with:
   - A clear docstring describing what property it validates
   - A `pytest.mark.xfail` marker with reason `"not yet implemented"`
   - The test function signature and the assertion it should eventually make
   - Do NOT write a passing test that does not actually validate the property

7. After writing any stub files, add the missing entries to the phase CLAUDE.md `## Fitness Functions` section.

## Standard Fitness Functions by Phase Type

These apply regardless of what the phase CLAUDE.md says — they are minimum required for each layer type:

**Any ingestion phase (CDC, streaming):**
- Source records reach destination within SLA freshness window
- No data loss — record count at destination >= record count at source

**Any storage layer (Bronze, Silver, Gold):**
- Layer isolation — this layer never reads from a downstream layer
- PII handling — sensitive fields masked/hashed/absent as required for this layer

**Bronze specifically:**
- Raw source fidelity — Bronze schema contains all source fields
- No transformation logic — Bronze applies no business rules, only PII masking

**Silver specifically:**
- Soda quality gate enforced — pipeline cannot advance past Silver with failing checks
- Deduplication — no duplicate primary keys in Silver output

**Gold specifically:**
- Referential integrity — all foreign keys in fact tables resolve to dimension records
- SCD Type 2 correctness — only one current=true record per business key

**Any serving layer (FastAPI, Feature Store):**
- Latency SLA — P99 within declared SLA
- Schema contract — response shape matches declared interface

**AI layer:**
- Confidence score always present — no inference response missing confidence_band
- No future leakage — feature values use only data available at the as-of timestamp
