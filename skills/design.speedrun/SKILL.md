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
- Remaining: one or more Jira Feature keys (e.g., OSAC-1269 OSAC-2917)

```bash
python3 scripts/state.py clean
python3 scripts/pipeline_state.py init --batch-size <N> [--headless]
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
- Substitute `{JIRA_KEY}` and `{DESIGN_ID}` from `vars`
- Launch as background Agent (model: opus)

Wait: `python3 scripts/pipeline_state.py wait-for-wave`
On exit 0: go to step 1. On exit 3: re-run wait.

### Agent Prompts

**GENERATE phase**: Each agent reads prompts/generate-design.md, the PRD, Jira
source, template, section guidance, exemplars, and scoring rubric. Generates a
300-500 line design document with proto schemas, workflow descriptions, test plans.

**REVIEW phase**: Each agent reads prompts/review-design.md, scores on 4 criteria
(architecture/feasibility/scope/testability, each 0-2, total /8).

**REVISE phase**: Each agent reads prompts/revise-design.md, fixes flagged issues.

$ARGUMENTS
