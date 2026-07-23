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
- Remaining: Jira Feature key (e.g., OSAC-1269)

## Step 1: Fetch Feature

```bash
python3 scripts/fetch_feature.py {JIRA_KEY} --output artifacts/prd-tasks/{JIRA_KEY}-source.md
```

## Step 2: Read Context

Read these files in order:
1. `artifacts/prd-tasks/{JIRA_KEY}-source.md`
2. `context/prd-template.md`
3. `context/osac-dimensions.md`
4. `context/review-patterns.md`
5. `context/scoring-rubric.md`
6. One exemplar from `context/exemplars/` matching the service area
7. `prompts/generate-prd.md`

## Step 3: Generate PRD

Follow the instructions in `prompts/generate-prd.md` to write the PRD to
`artifacts/prd-tasks/{JIRA_KEY}.md`.

## Step 4: Set Frontmatter

```bash
python3 scripts/frontmatter.py set artifacts/prd-tasks/{JIRA_KEY}.md \
    prd_id={JIRA_KEY} title="{title}" jira_key={JIRA_KEY} status=Draft
```

## Step 5: Run Checks

```bash
python3 scripts/score_prd.py check-structure artifacts/prd-tasks/{JIRA_KEY}.md
python3 scripts/score_prd.py check-personas artifacts/prd-tasks/{JIRA_KEY}.md
python3 scripts/score_prd.py check-leakage artifacts/prd-tasks/{JIRA_KEY}.md
```

If any check fails, fix the PRD before returning.

$ARGUMENTS
