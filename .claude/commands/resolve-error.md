Mark an error as resolved and document the fix permanently.

Arguments: error ID, e.g. `ERR-003` or `ERR-003-debezium-connector-not-starting`. If no argument is provided, list all open error files across the current phase and root `errors/` and ask which one to resolve.

## Steps

1. Read `procedures/error-logging.md` in full before proceeding.

2. Locate the error file:
   - Search `NN-phase/errors/` and `errors/` (root) for the matching ERR-NNN file (chaos-discovered errors live in the owning phase's `errors/`, not a separate directory)
   - Read the file in full — every attempt, every result

3. Confirm the fix is verified before marking resolved:
   - Ask: "Has the fix been confirmed working? What command or check confirmed it?"
   - Do not mark resolved based on an assumption — only mark resolved when the fix is verified

4. Fill the `## Resolution` section:

   **What worked:**
   - Exact fix — command, config change, code change, version pin
   - Specific enough that someone can reproduce it without asking questions

   **Root cause:**
   - The actual underlying cause, not the symptom
   - Example: "Debezium could not connect because the PostgreSQL replication slot was created with a different plugin (pgoutput vs wal2json) than the connector config expected" — not "connector config was wrong"

   **Why previous attempts failed:**
   - One entry per previous attempt
   - This is the most critical field — explains what NOT to try next time
   - Be specific: "Attempt 1 failed because restarting the container does not recreate the replication slot — the slot persists in PostgreSQL and must be dropped manually first"

   **Prevention:**
   - What change prevents this from recurring: an ADR update, a healthcheck addition, a Soda check, a config comment, a procedure update
   - If an ADR should be updated or created, flag it — run `/write-adr` after this command

   **Detection:**
   - What alert, healthcheck, Soda check, fitness function, or Prometheus rule would have surfaced this error earlier
   - Always results in a concrete action: "add X to Y"
   - If nothing would have caught it earlier, state why and whether that gap should be accepted or closed
   - "Nothing would have caught this" requires justification — the default assumption is a detection gap exists

5. Change `## Status` from `Open` to `Resolved`.

6. If the fix requires an ADR, procedure update, or config change to prevent recurrence — create a follow-up task and state it explicitly in the report.

7. Report back:
   - Confirm the file path and status change
   - State the root cause in one sentence
   - State the prevention action and whether it requires a follow-up (`/write-adr`, procedure edit, etc.)

## Rules
- Never mark resolved without a verified fix — "probably fixed" is not resolved
- The "Why previous attempts failed" field cannot be left empty if there were failed attempts
- If the root cause reveals a design flaw that affects other phases, flag it — it may require an ADR or a blast radius review in the relevant phase CLAUDE.md
- A resolved error file is permanent — never delete it
