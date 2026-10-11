---
name: prd.speedrun
description: >-
  End-to-end autonomous PRD pipeline. Accepts Jira Feature keys, fetches
  requirements, generates PRDs, self-reviews, auto-fixes, and produces a
  quality report. Supports --headless for CI. Non-interactive.
---

# PRD Speedrun — Autonomous PRD Generator

You are running the full PRD creation pipeline in speedrun mode. Your goal is
to go from Jira Feature keys to reviewed, quality-gated PRDs with no human
interaction. You orchestrate by calling scripts and launching agents — never
duplicate their work.

## Step 0: Parse Arguments and Initialize

Parse `$ARGUMENTS` for:
- `--headless`: Suppress questions and confirmations (for CI)
- `--batch-size N`: Override batch size (default 5)
- `--research-mode off|live|replay`: Chai research policy (default `live`; use `off` for frozen-evidence evaluations)
- `--replay-record PATH`: Frozen evidence JSON input for replay (required only with `replay`; a directory may contain `{JIRA_KEY}-research.json` files)
- Remaining arguments: one or more Jira Feature keys (e.g., OSAC-1269 OSAC-2917)

Require `--replay-record` when mode is `replay`; reject that option for other
modes. The value may be one feature record or a directory of per-feature records.
Resolve a relative path from the `prd-creator` directory.

If no arguments provided, stop with usage instructions.

Clean state and initialize:

```bash
python3 scripts/state.py clean
python3 scripts/pipeline_state.py init --batch-size <N> --research-mode <MODE> [--replay-record <PATH>] [--headless]
```

Write all IDs to disk:

```bash
python3 scripts/state.py write-ids tmp/pipeline-all-ids.txt <all_IDs>
python3 scripts/state.py write-ids tmp/pipeline-batch-1-ids.txt <all_IDs>
python3 scripts/pipeline_state.py set total_batches=1
python3 scripts/pipeline_state.py set-phase BATCH_START
```

## Dispatch Loop

**CRITICAL: Run the loop to completion.** Never stop early or skip phases.
Context compression is handled automatically.

Repeat until phase is DONE:

### Step 1: Get next action

```bash
python3 scripts/pipeline_state.py next-action
```

Parse the YAML output for: `action`, `phase`, `message`, `agents`.
For each agent, pass every value in `vars` to the prompt, including research
mode, stage, run ID, and record path. `next-action` records the active wave IDs
for `wait-for-wave`.

### Step 2: Execute

**done**: Exit loop. Print summary.

**run_script**: Run `python3 scripts/pipeline_state.py run-phase`. Go to step 1.

**launch_wave**: For each agent in the `agents` list:
- Read `prompt_file` to get the agent instructions
- Substitute `{JIRA_KEY}` and `{PRD_ID}` from `vars`
- Launch as background Agent (model: opus)

Then wait for completion:

```bash
python3 scripts/pipeline_state.py wait-for-wave
```

On exit 0 (complete): go to step 1.
On exit 3 (still pending): re-run `python3 scripts/pipeline_state.py wait-for-wave`.

### Agent Prompts

**GENERATE phase** — For each ID, launch an agent with this prompt:

```
You are working in {CWD}. Generate a PRD for {JIRA_KEY}.

Read these files in order:
1. artifacts/prd-tasks/{JIRA_KEY}-source.md
2. context/organizational-research.md and artifacts/prd-tasks/{JIRA_KEY}-research.md
3. context/prd-template.md
4. context/osac-dimensions.md
5. context/review-patterns.md
6. context/scoring-rubric.md
7. One file from context/exemplars/ (pick based on similar service area)
8. prompts/generate-prd.md

Generate PRD to artifacts/prd-tasks/{JIRA_KEY}.md.
For every material Chai-informed fact, include `[Chai:CLAIM_ID]` and a direct
link to each verified source URL; follow prompts/generate-prd.md.
Set frontmatter: python3 scripts/frontmatter.py set artifacts/prd-tasks/{JIRA_KEY}.md prd_id={JIRA_KEY} title="..." jira_key={JIRA_KEY} status=Draft
```

**RESEARCH phase** — For each ID, launch `prompts/research-context.md` with
`RESEARCH_STAGE=prd`, the supplied `RESEARCH_MODE`, `RESEARCH_RUN_ID`, and
`RESEARCH_RECORD`. In replay mode also pass `RESEARCH_REPLAY_RECORD`; the
prompt binds the output to this run and retains the fixture origin and input
hash in a provenance sidecar. Wait until the record validates for the current
feature and run. `off`, unavailable, and timeout outcomes are valid recorded
outcomes; they are not evidence of an empty scope.

**REVIEW phase** — For each ID, launch an agent with this prompt:

```
You are working in {CWD}. Review the PRD for {PRD_ID}.

Read these files:
1. artifacts/prd-tasks/{PRD_ID}.md
2. context/organizational-research.md and the same research record
3. context/scoring-rubric.md
4. context/osac-dimensions.md
5. context/review-patterns.md
6. prompts/review-prd.md

Run deterministic checks:
  python3 scripts/score_prd.py check-structure artifacts/prd-tasks/{PRD_ID}.md
  python3 scripts/score_prd.py check-personas artifacts/prd-tasks/{PRD_ID}.md
  python3 scripts/score_prd.py check-leakage artifacts/prd-tasks/{PRD_ID}.md

Write review to artifacts/prd-reviews/{PRD_ID}-review.md with frontmatter scores
and `artifacts/prd-reviews/{PRD_ID}-coverage.json` as described in
prompts/review-prd.md. Use exact requirement IDs. Missing or invalid in-scope /
constraint coverage must result in `pass=false`, recommendation `clarify`, and
must not enter the automatic revision loop.
Apply calibration — first drafts rarely merit 10/10.
```

**REVISE phase** — For each ID that needs revision, launch an agent with:

```
You are working in {CWD}. Revise the PRD for {PRD_ID} based on review feedback.

Read:
1. artifacts/prd-reviews/{PRD_ID}-review.md (review feedback)
2. artifacts/prd-tasks/{PRD_ID}.md (current PRD)
3. context/organizational-research.md and the same research record
4. prompts/revise-prd.md (revision instructions)

Back up: cp artifacts/prd-tasks/{PRD_ID}.md artifacts/prd-originals/{PRD_ID}.md
Fix flagged issues. Set auto_revised=true in review frontmatter.
Keep changes within the record's accepted scope; preserve `[Chai:CLAIM_ID]` and
verified source links for material Chai facts. Leave unsupported reviewer
suggestions out of scope or as open questions.
```

## Teardown

After phase reaches DONE:

```bash
python3 scripts/pipeline_state.py get-phase
```

Print the pipeline report from `artifacts/pipeline-runs/`.

$ARGUMENTS
