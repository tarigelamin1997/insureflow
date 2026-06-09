Write an Architecture Decision Record for the current phase.

Arguments: a short description of the decision being made, e.g. `kafka schema format` or `iceberg partitioning strategy`. If no argument is provided, ask what decision needs to be recorded before proceeding.

## Steps

1. Read `procedures/adr-template.md` in full before writing anything.

2. Identify the current phase being worked on. If ambiguous, ask.

3. Determine the next ADR number:
   - List files in `NN-phase-name/decisions/`
   - Find the highest existing `adr-NNN-*.md` number
   - Increment by 1. If no ADRs exist yet, start at 001.

4. Ask the following questions if the answers are not already clear from the conversation context. Ask all at once, not one at a time:
   - What is the specific problem or requirement this decision addresses?
   - What are the real alternatives that were considered?
   - What constraints ruled out the obvious default (offline-only, cloud-agnostic, etc.)?

5. Write the ADR file at `NN-phase-name/decisions/adr-NNN-short-title.md` using the full template from `procedures/adr-template.md`.

6. Add an entry to the `## Decisions` section of the phase's `CLAUDE.md`:
   - Format: `- [Short description of decision] → decisions/adr-NNN-short-title.md`

7. Report back: confirm the file path, the ADR number, and summarise the "Makes impossible" and "Impact on other phases" fields — these are the ones most likely to matter later.

## Rules
- Status must be `Accepted` unless explicitly told otherwise
- Alternatives Considered must have at least two rows
- "Makes impossible" must be filled — write `None identified` only if you have genuinely considered it
- Do not write vague rejection reasons. "Too complex" is not acceptable — state what specifically makes it unsuitable for InsureFlow
- If the decision being recorded is already listed in the root `CLAUDE.md` Locked Global Decisions table, note that and still write the full ADR — the root table is a summary, the ADR is the full justification
