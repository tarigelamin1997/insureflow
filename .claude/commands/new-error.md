Create a new error file for a failure encountered during implementation.

Arguments: a short description of the error, e.g. `debezium-connector-not-starting` or `iceberg-write-permission-denied`. If no argument is provided, ask for it before proceeding.

## Steps

1. Read `procedures/error-logging.md` in full before creating any file.

2. Determine the correct location:
   - If the error is contained within one phase → `NN-phase/errors/`
   - If the error spans multiple phases or is infrastructure-wide → `errors/` at repo root
   - If the error was surfaced by a chaos scenario → the **owning phase's** `NN-phase/errors/`
     (or root `errors/` if cross-phase). Set `Source: chaos-discovered` and reference the `ST-NNN`
     document. There is no separate `chaos/errors/` directory — chaos errors live with the phase
     that owns the fix so `/close-phase` blocks on them.
   - If the phase is ambiguous, ask before proceeding.

3. Check for duplicates first:
   - List all existing files in the target `errors/` directory
   - Also list all files in root `errors/`
   - Read any file whose description matches the current error
   - If a matching open error already exists: do NOT create a new file — report the existing one and suggest adding a new attempt section to it instead

4. Determine the next error number:
   - List files in the target directory
   - Find the highest existing `ERR-NNN-*.md` number
   - Increment by 1. If no errors exist yet, start at 001.

5. Create `errors/ERR-NNN-short-description.md` using the full template from `procedures/error-logging.md`.

   Pre-fill the following from context:
   - Phase / Component — from the current working phase and the service or file where the error occurred
   - Layer — infer from the phase and component: Bronze/Silver/Gold/CDC/Infrastructure/Governance/AI/Serving/Observability/Cross-cutting
   - Type — infer from the error nature: data-corruption/connectivity/config/dependency/performance/schema/auth/unknown
   - Source — `implementation` by default; `chaos-discovered` if the error was surfaced by a chaos scenario
   - First Observed — what was being implemented, what command was run
   - Error Description — paste the exact error message if available in the conversation
   - Environment State — any service states or versions visible from context

   Leave `## Attempts` empty — the first attempt will be added directly to the file as debugging proceeds.

6. Report back:
   - File path created
   - Error number assigned
   - Remind: "Log each attempt directly in this file as you go. Run `/resolve-error ERR-NNN` when fixed."

## Rules
- Do not create a new file if a matching open error already exists — append to the existing one
- Never paraphrase error messages — paste verbatim or leave the field as [PASTE ERROR MESSAGE HERE]
- Do not pre-fill the Attempts or Resolution sections
