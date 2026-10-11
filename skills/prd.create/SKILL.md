---
name: prd.create
description: >-
  Generate a PRD from a Jira Feature key. Fetches the feature, reads OSAC
  context, and produces a template-conforming PRD. Non-interactive.
---

# PRD Create

You are an autonomous PRD author. Generate a PRD from a Jira Feature issue.

## Step 0: Parse Arguments

Parse `$ARGUMENTS` for:
- `--headless`: Skip all questions
- `--prd-id ID`: Pre-assigned PRD ID (Jira key)
- `--research-mode off|live|replay`: Research policy (default: `live`)
- `--replay-record PATH`: Frozen evidence JSON input (required only with `replay`)
- Remaining: Jira Feature key (e.g., OSAC-1269)

## Step 1: Fetch Feature

```bash
python3 scripts/fetch_feature.py {JIRA_KEY} --output artifacts/prd-tasks/{JIRA_KEY}-source.md
```

## Step 2: Capture Chai Evidence

`replay` requires `--replay-record PATH`; reject it in other modes. Read
`context/organizational-research.md` and follow `prompts/research-context.md`
for this feature with `RESEARCH_STAGE=prd`, the selected `RESEARCH_MODE`,
`RESEARCH_REPLAY_RECORD` (when replaying), and a fresh run ID such as
`single-{JIRA_KEY}-{UTC timestamp}`. Use that exact ID as `RESEARCH_RUN_ID` below.
Resolve a relative fixture path from the `prd-creator` directory.
Persist the requirement and decision record at
`artifacts/prd-tasks/{JIRA_KEY}-research.json`, then validate and render it:

```bash
python3 ../_shared/scripts/research_context.py validate artifacts/prd-tasks/{JIRA_KEY}-research.json --feature {JIRA_KEY} --stage prd --run-id {RESEARCH_RUN_ID}
python3 ../_shared/scripts/research_context.py render artifacts/prd-tasks/{JIRA_KEY}-research.json --output artifacts/prd-tasks/{JIRA_KEY}-research.md
```

In replay mode, validate the fixture's feature/source applicability, create the
current run's record from it, and keep the fixture origin and input hash in a
provenance sidecar. If Chai is unavailable or times out, record that status
honestly and continue when Jira has enough information for a complete draft. A material unresolved
scope conflict blocks readiness.

## Step 3: Read Context

Read these files in order:
1. `artifacts/prd-tasks/{JIRA_KEY}-source.md`
2. `context/prd-template.md`
3. `context/osac-dimensions.md`
4. `context/review-patterns.md`
5. `context/scoring-rubric.md`
6. `context/organizational-research.md` and the rendered research record
7. One exemplar from `context/exemplars/` matching the service area
8. `prompts/generate-prd.md`

## Step 4: Generate PRD

Follow `prompts/generate-prd.md` to write the PRD to
`artifacts/prd-tasks/{JIRA_KEY}.md`. Use only recorded in-scope requirements.
Cite every material Chai-informed fact with `[Chai:CLAIM_ID]` and a direct link
to each verified source URL. Do not treat unverified or proposed claims as
requirements.

## Step 5: Set Frontmatter

```bash
python3 scripts/frontmatter.py set artifacts/prd-tasks/{JIRA_KEY}.md \
    prd_id={JIRA_KEY} title="{title}" jira_key={JIRA_KEY} status=Draft
```

## Step 6: Run Checks

```bash
python3 scripts/score_prd.py check-structure artifacts/prd-tasks/{JIRA_KEY}.md
python3 scripts/score_prd.py check-personas artifacts/prd-tasks/{JIRA_KEY}.md
python3 scripts/score_prd.py check-leakage artifacts/prd-tasks/{JIRA_KEY}.md
```

If any check fails, fix the PRD before returning.

$ARGUMENTS
