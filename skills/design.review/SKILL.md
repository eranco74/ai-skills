---
name: design.review
description: >-
  Review and score a design document against the OSAC 4-criterion rubric
  (Architecture, Feasibility, Scope, Testability). Produces structured review.
---

# Design Review

You are an autonomous design reviewer. Score designs against the OSAC rubric.

## Step 0: Parse Arguments

Parse `$ARGUMENTS` for one or more design IDs (Jira keys).

## Step 1: For Each Design

Read `artifacts/design-tasks/{DESIGN_ID}-design.md`.

Read context: `context/scoring-rubric.md`, `context/osac-dimensions.md`,
`context/review-patterns.md`, `prompts/review-design.md`.

## Step 2: Run Deterministic Checks

```bash
python3 scripts/score_design.py artifacts/design-tasks/{DESIGN_ID}-design.md check-structure
python3 scripts/score_design.py artifacts/design-tasks/{DESIGN_ID}-design.md check-frontmatter
python3 scripts/score_design.py artifacts/design-tasks/{DESIGN_ID}-design.md check-proto
python3 scripts/score_design.py artifacts/design-tasks/{DESIGN_ID}-design.md check-tenant-isolation
python3 scripts/score_design.py artifacts/design-tasks/{DESIGN_ID}-design.md check-placeholders
python3 scripts/score_design.py artifacts/design-tasks/{DESIGN_ID}-design.md check-length
```

## Step 3: Score and Write Review

Follow `prompts/review-design.md`. Score on 4 criteria (0-2 each, /8 total).
Write review to `artifacts/design-reviews/{DESIGN_ID}-review.md` with frontmatter.

Pass: >= 5/8 AND no zeros.

$ARGUMENTS
