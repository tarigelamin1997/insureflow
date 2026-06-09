Scaffold a new phase directory for InsureFlow.

Arguments: phase identifier and name, e.g. `03-cdc-ingestion` or `10a-feature-store`. If no argument is provided, ask for it before proceeding.

## Steps

1. Read `procedures/phase-claude-md.md` in full before creating any file.

2. Create the following directory structure (use the phase identifier as the directory name):

```
NN-phase-name/
├── CLAUDE.md
├── README.md
├── decisions/
│   └── .gitkeep
├── errors/
│   └── .gitkeep
└── tests/
    ├── unit/
    │   └── .gitkeep
    ├── integration/
    │   └── .gitkeep
    └── contracts/
        └── .gitkeep
```

3. Write `NN-phase-name/CLAUDE.md` using the full template from `procedures/phase-claude-md.md`. Pre-fill:
   - The phase number and title in the heading
   - Any prerequisites that are obvious from the phase's position in the pipeline (reference the service dependency map in root `CLAUDE.md`)
   - The `## Procedures` section — include only the rows from the full table that are relevant to what this phase builds. Remove irrelevant rows. If unclear, keep all rows and mark them `[REVIEW — remove if not needed]`
   - Leave all other sections as clearly marked `[TO BE FILLED]` placeholders — do NOT invent content

4. Write `NN-phase-name/README.md` with this skeleton only:
```markdown
# Phase NN — Title

## What This Phase Builds
[One paragraph — copied from CLAUDE.md "What This Builds" once that section is filled]

## How to Run
[To be documented during implementation]

## Validation
[To be documented during implementation]
```

5. After creating all files, update the Phase Index table in root `CLAUDE.md`:
   - Find the row for this phase
   - Status remains `⬜ Not started` — do not change it

6. Report back: list every file created with its path. Flag any prerequisites or Interface Contract fields that could be pre-filled based on known architecture (from root `CLAUDE.md`).

7. State the next step explicitly: "Fill the phase CLAUDE.md, then run `/start-phase NN-name` — the entry gate — before writing any implementation code." `/new-phase` only scaffolds; `/start-phase` verifies prerequisites, CLAUDE.md completeness, required procedures, and fitness stubs, and marks the phase 🚧 In progress.

## Rules
- Do not write any implementation files (no .py, .sql, .yml config files)
- Do not fill in Decisions or Gotchas — those are written during implementation
- The CLAUDE.md must pass the "Minimum Viable" check defined in `procedures/phase-claude-md.md` before this command is considered complete — flag any missing required sections
