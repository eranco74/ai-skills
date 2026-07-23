---
name: prd.review
description: >-
  Review and score a PRD against the OSAC rubric. Produces structured review
  with actionable feedback. Accepts one or more PRD IDs.
---

# PRD Review

You are an autonomous PRD reviewer. Score PRDs against the OSAC rubric.

## Step 0: Parse Arguments

Parse `$ARGUMENTS` for:
- `--headless`: Suppress summaries
- Remaining: one or more PRD IDs (Jira keys, e.g., OSAC-1269 OSAC-2917)

## Step 1: For Each PRD

Read the PRD at `artifacts/prd-tasks/{PRD_ID}.md`.

Read context:
1. `context/scoring-rubric.md`
2. `context/osac-dimensions.md`
3. `context/review-patterns.md`
4. `prompts/review-prd.md`

## Step 2: Run Deterministic Checks

```bash
python3 scripts/score_prd.py check-structure artifacts/prd-tasks/{PRD_ID}.md
python3 scripts/score_prd.py check-personas artifacts/prd-tasks/{PRD_ID}.md
python3 scripts/score_prd.py check-leakage artifacts/prd-tasks/{PRD_ID}.md
```

## Step 3: Score and Write Review

Follow `prompts/review-prd.md` to score the PRD and write the review to
`artifacts/prd-reviews/{PRD_ID}-review.md`.

Set frontmatter with scores.

## Step 4: Filter for Revision

After reviewing all PRDs, output which ones need revision:

```bash
# IDs with score < 7 or any zero → need revision
# IDs with score >= 7 and no zeros → ready for submission
```

$ARGUMENTS
