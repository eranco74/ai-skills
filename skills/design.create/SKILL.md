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
- `--research-mode off|live|replay`: Research policy (default: `live`)
- `--replay-record PATH`: Frozen evidence JSON input (required only with `replay`)
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

## Step 2: Capture Chai Evidence

`replay` requires `--replay-record PATH`; reject it in other modes. Read
`context/organizational-research.md` and follow `prompts/research-context.md`
with `RESEARCH_STAGE=design`, the selected `RESEARCH_MODE`,
`RESEARCH_REPLAY_RECORD` (when replaying), and a fresh run ID such as
`single-{JIRA_KEY}-{UTC timestamp}`. Use that exact ID as `RESEARCH_RUN_ID` below.
Resolve a relative fixture path from the `design-creator` directory.
Reuse the PRD research record's verified sources and accepted decisions where
they apply, and persist the design-stage record at
`artifacts/design-tasks/{JIRA_KEY}-research.json`:

```bash
python3 ../_shared/scripts/research_context.py validate artifacts/design-tasks/{JIRA_KEY}-research.json --feature {JIRA_KEY} --stage design --run-id {RESEARCH_RUN_ID}
python3 ../_shared/scripts/research_context.py render artifacts/design-tasks/{JIRA_KEY}-research.json --output artifacts/design-tasks/{JIRA_KEY}-research.md
```

In replay mode, validate the fixture's feature and PRD/code revision
applicability, bind the new record to this run, and keep fixture origin and
input hash in a provenance sidecar.

Continue on unavailable or timed-out research when the PRD gives enough
information for a complete design. A material unresolved scope conflict blocks
readiness.

## Step 3: Read Context and Codebase

Read: PRD, Jira source, design template, section guidance, dimensions, rubric,
the organizational research contract and rendered research record, one exemplar,
and `prompts/generate-design.md`.

Explore affected codebase components (fulfillment-service API.md, existing protos,
osac-operator controllers).

## Step 4: Generate Design

Follow `prompts/generate-design.md`. Keep technical scope within the PRD's
in-scope requirements. Cite every material Chai-informed fact with
`[Chai:CLAIM_ID]` and a direct link to each verified source URL. Write to
`artifacts/design-tasks/{JIRA_KEY}-design.md`.

## Step 5: Run Checks

```bash
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-structure
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-frontmatter
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-proto
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-tenant-isolation
python3 scripts/score_design.py artifacts/design-tasks/{JIRA_KEY}-design.md check-length
```

Fix any failures before returning.

$ARGUMENTS
