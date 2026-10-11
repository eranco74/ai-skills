---
name: design.speedrun
description: >-
  End-to-end autonomous design document (EP) pipeline. Accepts Jira Feature keys,
  fetches requirements + PRD, generates design documents, self-reviews, auto-fixes,
  and produces a quality report. Supports --headless for CI.
---

# Design Speedrun — Autonomous EP Generator

You are running the full design document creation pipeline. Your goal is to go
from Jira Feature keys to reviewed, quality-gated Enhancement Proposals with no
human interaction.

## Step 0: Parse Arguments and Initialize

Parse `$ARGUMENTS` for:
- `--headless`: Suppress questions (for CI)
- `--batch-size N`: Override batch size (default 3)
- `--research-mode off|live|replay`: Chai research policy (default `live`; use `off` for frozen-evidence evaluations)
- `--replay-record PATH`: Frozen evidence JSON input for replay (required only with `replay`; a directory may contain `{JIRA_KEY}-research.json` files)
- Remaining: one or more Jira Feature keys (e.g., OSAC-1269 OSAC-2917)

Require `--replay-record` when mode is `replay`; reject that option for other
modes. The value may be one feature record or a directory of per-feature records.
Resolve a relative path from the `design-creator` directory.

```bash
python3 scripts/state.py clean
python3 scripts/pipeline_state.py init --batch-size <N> --research-mode <MODE> [--replay-record <PATH>] [--headless]
python3 scripts/state.py write-ids tmp/pipeline-all-ids.txt <all_IDs>
python3 scripts/state.py write-ids tmp/pipeline-batch-1-ids.txt <all_IDs>
python3 scripts/pipeline_state.py set total_batches=1
python3 scripts/pipeline_state.py set-phase BATCH_START
```

## Dispatch Loop

Repeat until phase is DONE:

### Step 1: Get next action
```bash
python3 scripts/pipeline_state.py next-action
```

### Step 2: Execute

**done**: Exit loop. Print summary.

**run_script**: Run `python3 scripts/pipeline_state.py run-phase`. Go to step 1.

**launch_wave**: For each agent in the `agents` list:
- Read `prompt_file` for instructions
- Pass every value in `vars`, including research mode, stage, run ID, and record path
- Launch as background Agent (model: opus)

`next-action` records the active wave IDs for `wait-for-wave`.

Wait: `python3 scripts/pipeline_state.py wait-for-wave`
On exit 0: go to step 1. On exit 3: re-run wait.

### Agent Prompts

**RESEARCH phase**: Each agent reads `prompts/research-context.md` with
`RESEARCH_STAGE=design`, the supplied `RESEARCH_MODE`, `RESEARCH_RUN_ID`, and
`RESEARCH_RECORD`. In replay mode also pass `RESEARCH_REPLAY_RECORD`; bind the
output to this run and preserve fixture origin and input hash in a provenance
sidecar. Reuse the PRD-stage record's verified sources and accepted
decisions where relevant. Wait until the design record validates for this
feature and run. `off`, unavailable, and timeout are recorded outcomes.

**GENERATE phase**: Each agent reads the same design research record plus
`prompts/generate-design.md`, the PRD, Jira source, template, section guidance,
exemplars, and scoring rubric. Keep the design inside the PRD's accepted
requirements; cite every material Chai-informed fact with `[Chai:CLAIM_ID]` and
a direct link to each verified source URL. Generate a design document with
proto schemas, workflow descriptions, and test plans.

**REVIEW phase**: Each agent reads prompts/review-design.md, scores on 4 criteria
(architecture/feasibility/scope/testability, each 0-2, total /8).
Write the review and same-run
`artifacts/design-reviews/{JIRA_KEY}-coverage.json` sidecar described by that
prompt. Missing or invalid in-scope / constraint coverage must result in
`pass=false`, recommendation `clarify`, and must not enter the automatic
revision loop.

**REVISE phase**: Each agent reads prompts/revise-design.md, fixes flagged issues.
All review and revision work uses the same run's record; preserve exact
`[Chai:CLAIM_ID]` markers and verified source links for material Chai facts; do
not create unsupported scope changes. An unresolved material conflict blocks
readiness.

$ARGUMENTS
