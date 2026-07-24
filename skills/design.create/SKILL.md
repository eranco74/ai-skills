---
name: design.create
description: >-
  Generate a design document (EP) from a Jira Feature key and its PRD.
  Fetches the feature, reads the PRD, explores affected codebase, and
  produces a template-conforming design with proto schemas and test plans.
---

# Design Create

You are an autonomous design document author. Generate an EP from a Feature.

## Step 0: Parse Arguments

Parse `$ARGUMENTS` for:
- `--headless`: Skip all questions
- `--design-id ID`: Pre-assigned design ID (Jira key)
- Remaining: Jira Feature key (e.g., OSAC-1269)

## Step 1: Fetch Feature and PRD

```bash
python3 scripts/fetch_feature.py {JIRA_KEY} --output artifacts/design-tasks/{JIRA_KEY}-source.md
```

Locate the PRD — check these locations in order:
1. `artifacts/design-tasks/{JIRA_KEY}-prd.md` (already fetched)
2. `../enhancement-proposals/enhancements/*{JIRA_KEY}*/prd.md` (from EP repo)
3. `../prd-creator/artifacts/prd-tasks/{JIRA_KEY}.md` (from prd-creator)

Copy to `artifacts/design-tasks/{JIRA_KEY}-prd.md`.

## Step 2: Read Context and Codebase

Read: PRD, Jira source, design template, section guidance, dimensions, rubric,
one exemplar, and the generation prompt at `prompts/generate-design.md`.

Explore affected codebase components (fulfillment-service API.md, existing protos,
osac-operator controllers).

## Step 3: Generate Design

Follow `prompts/generate-design.md`. Write to `artifacts/design-tasks/{JIRA_KEY}-design.md`.

## Step 4: Run Checks

```bash
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-structure
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-frontmatter
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-proto
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-tenant-isolation
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-length
```

Fix any failures before returning.

$ARGUMENTS
