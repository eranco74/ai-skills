---
name: design.respond
description: >-
  Respond to GitHub PR reviewer feedback on a design document. Fetches PR
  comments, categorizes them, applies design changes, and drafts replies.
---

# Design Respond — Handle Reviewer Feedback

Fetch reviewer comments from a GitHub PR, categorize, apply changes, draft replies.

## Step 0: Parse Arguments

- `--headless`: Apply changes autonomously
- `--pr NUMBER`: GitHub PR number
- `--repo OWNER/REPO`: Default osac-project/enhancement-proposals
- Remaining: Design ID (Jira key)

## Step 1: Fetch PR Comments

```bash
gh pr view {PR} --repo {REPO} --json comments,reviews
gh api repos/{REPO}/pulls/{PR}/comments --paginate
```

## Step 2: Categorize and Apply

Read `context/organizational-research.md`, the design-stage record at
`artifacts/design-tasks/{DESIGN_ID}-research.json`, the PRD, and Jira source.
Use this existing feature/run record; do not start a new research run.

Categories: architectural concern, API design feedback, missing section,
test plan gap, scope question, factual correction, approval.

For each:
- Apply changes supported by the PRD or accepted decisions in the same research
  record. Keep the design inside PRD in-scope requirements; leave unsupported
  scope requests as open questions and explain the evidence boundary in the reply.
- If the same record has an unresolved material conflict, mark the design not
  ready and set its review frontmatter to `pass=false`, `recommendation=revise`.
- Draft reply comments
- Re-run deterministic checks after changes

## Step 3: Write Response Log

Write to `artifacts/design-reviews/{DESIGN_ID}-responses.md`.

$ARGUMENTS
