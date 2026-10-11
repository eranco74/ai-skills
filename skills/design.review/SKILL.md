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

Read `context/organizational-research.md` and the same design-stage record at
`artifacts/design-tasks/{DESIGN_ID}-research.json` (render it with
`../_shared/scripts/research_context.py render` if helpful). Check that design
scope traces to the PRD's in-scope requirements and accepted evidence
decisions. Do not start a new research run or treat proposed/unverified claims
as requirements. An unresolved material conflict blocks readiness.
When a material conflict is unresolved, set the verdict/frontmatter to failed
and recommend `clarify` regardless of the numeric rubric score; keep it out of
automatic revision until its evidence or decision is resolved.
For every material Chai-informed fact, verify the exact `[Chai:CLAIM_ID]`
marker and direct verified source link.

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
Write review to `artifacts/design-reviews/{DESIGN_ID}-review.md` and the
same-run `artifacts/design-reviews/{DESIGN_ID}-coverage.json` sidecar. Missing
or invalid in-scope/constraint coverage makes readiness `clarify` and must not
enter the automatic revision loop.

Pass: >= 5/8 AND no zeros.

$ARGUMENTS
