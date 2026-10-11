---
name: prd.respond
description: >-
  Respond to GitHub PR reviewer feedback on a PRD. Fetches PR comments,
  categorizes them, applies PRD changes, and drafts reply comments.
  Supports autonomous and attended modes.
---

# PRD Respond — Handle Reviewer Feedback

You are a PRD feedback responder. Fetch reviewer comments from a GitHub PR,
categorize them, apply PRD changes where appropriate, and draft reply comments.

## Step 0: Parse Arguments

Parse `$ARGUMENTS` for:
- `--headless`: Apply changes autonomously without confirmation
- `--pr NUMBER`: GitHub PR number
- `--repo OWNER/REPO`: GitHub repo (default: osac-project/enhancement-proposals)
- Remaining: PRD ID (Jira key)

## Step 1: Fetch PR Comments

```bash
gh pr view {PR_NUMBER} --repo {REPO} --json comments,reviews
gh api repos/{REPO}/pulls/{PR_NUMBER}/comments --paginate
```

## Step 2: Read PRD and Context

Read:
1. `artifacts/prd-tasks/{PRD_ID}.md`
2. `context/organizational-research.md` and the same run's
   `artifacts/prd-tasks/{PRD_ID}-research.json`
3. `context/review-patterns.md`
4. `context/scoring-rubric.md`
5. `prompts/respond-feedback.md`

## Step 3: Categorize and Apply

Follow `prompts/respond-feedback.md` to:
1. Categorize each comment (clarification, correction, scope question, etc.)
2. Apply changes supported by Jira or accepted decisions in the same research
   record. Do not accept unsupported scope changes; record them as open
   questions and explain the evidence boundary in the reply.
3. Draft reply comments for clarifications

## Step 4: Re-score

Run deterministic checks after any changes:

```bash
python3 scripts/score_prd.py check-structure artifacts/prd-tasks/{PRD_ID}.md
python3 scripts/score_prd.py check-personas artifacts/prd-tasks/{PRD_ID}.md
python3 scripts/score_prd.py check-leakage artifacts/prd-tasks/{PRD_ID}.md
```

## Step 5: Write Response Log

Write to `artifacts/prd-reviews/{PRD_ID}-responses.md`.

If `--headless`, apply all non-destructive changes autonomously.
If interactive, present proposed responses for user approval.

$ARGUMENTS
