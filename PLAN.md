# PRD Creator — Autonomous PRD Generation for OSAC

## Overview

Build an autonomous, unattended workflow that generates OSAC Product Requirements
Documents (PRDs) from Jira Feature issues, self-reviews them against a calibrated
rubric, auto-fixes issues, and supports reviewer feedback loops. Modeled after
the [rfe-creator](https://github.com/opendatahub-io/rfe-creator) architecture
but adapted for OSAC's larger, more structured PRD format.

## Architecture

### Key Design Decisions

1. **Artifact-based state** — All intermediate state lives in `artifacts/` with
   YAML frontmatter, surviving context compression and enabling headless execution.
2. **Skill-based pipeline** — Each phase is a self-contained skill that can run
   independently or as part of the speedrun pipeline.
3. **Rubric-driven quality** — Uses the existing OSAC PRD review rubric (5 criteria,
   0-2 each, pass at 7+/no zeros) as the scoring backbone.
4. **Few-shot context injection** — Top-scoring merged PRDs are included as
   exemplars to guide generation quality.
5. **Domain context injection** — OSAC dimensions, personas, review patterns,
   and codebase architecture are injected during generation.
6. **Headless mode** — Full pipeline runs unattended (for GitHub Actions/CI).

### Differences from rfe-creator

| Aspect | rfe-creator (RFEs) | prd-creator (PRDs) |
|--------|-------------------|-------------------|
| Output size | 1-2 paragraphs | 100-200 lines structured doc |
| Template | Simple (Summary/Problem/Customers/AC) | Complex (Problem/Scope/UserStories by persona/Assumptions/Dependencies) |
| Context needed | Minimal (business need only) | Deep (OSAC personas, dimensions, architecture, review patterns) |
| Scoring rubric | 5 criteria (what/why/open_to_how/not_a_task/right_sized) | 5 criteria (WHAT/WHY/user-facing-focus/right-sized/testability) |
| Output target | Jira ticket | GitHub PR in enhancement-proposals |
| Review flow | Self-contained auto-fix | Auto-fix + GitHub PR reviewer feedback |

### Pipeline Flow

```
Jira Feature → Ingest → Generate → Self-Review → Auto-Fix → [Optional: Publish PR]
                  ↑                                              ↓
                  └──────── Reviewer Feedback Loop ←─────────────┘
```

## Implementation Plan

### Phase 1: Project Scaffolding

1. Create directory structure
2. Create Python utility scripts (frontmatter.py, state.py, fetch_feature.py)
3. Create AGENTS.md/CLAUDE.md with conventions

### Phase 2: Core Skills

1. **prd.create** — Generate PRD from Jira feature
   - Fetches feature from Jira (jira CLI)
   - Injects OSAC context (dimensions, personas, review patterns)
   - Injects few-shot examples (top 3-5 merged PRDs)
   - Generates PRD following template
   - Writes artifact with frontmatter

2. **prd.review** — Score PRD against rubric
   - Reads PRD artifact
   - Scores on 5 criteria (WHAT, WHY, User-Facing Focus, Right-Sized, Testability)
   - Writes review artifact with frontmatter (score, pass/fail, recommendation)
   - Provides actionable feedback per criterion

3. **prd.auto-fix** — Auto-revise PRDs
   - Reads review feedback
   - Revises PRD to address flagged issues
   - Preserves content fidelity (reframe, don't remove)
   - Triggers re-review after revision

4. **prd.speedrun** — End-to-end pipeline
   - Orchestrates: create → review → auto-fix → re-review
   - Supports `--headless`, `--dry-run`
   - Batch mode for multiple features

5. **prd.respond** — Handle reviewer feedback (future/optional)
   - Fetches GitHub PR comments
   - Proposes PRD changes
   - Updates artifact and pushes to PR branch

### Phase 3: Context & Exemplars

1. Copy OSAC dimensions, review patterns, and persona definitions into `context/`
2. Extract top-scoring merged PRDs as few-shot examples
3. Create PRD template reference
4. Build the generation prompt with calibrated examples

### Phase 4: Evaluation

1. Create eval dataset from Jira features with known-good merged PRDs
2. Define eval.yaml with deterministic checks and LLM judges
3. Run evaluation, analyze results
4. Iterate (3 rounds minimum)

### Phase 5: Iteration

For each iteration:
1. Analyze eval failures and low scores
2. Identify prompt improvements
3. Update generation/review prompts
4. Re-run eval and compare

## Eval Dataset

Test cases from merged PRDs with known scores:

| Case | Jira | PRD PR | Score | Gold PRD Path |
|------|------|--------|-------|---------------|
| 1 | OSAC-1269 | #74 | 10/10 | OSAC-1269-cluster-version-api/prd.md |
| 2 | OSAC-1270 | #135 | 10/10 | OSAC-1270-base-os-management-bmaas/prd.md |
| 3 | OSAC-1415 | #124 | 10/10 | (open PR, use diff) |
| 4 | OSAC-2917 | #132 | 9/10 | OSAC-2917-gpu-instance-types/prd.md |
| 5 | OSAC-2872 | #134 | 9/10 | storage-control-plane-osac-2872/prd.md |
| 6 | OSAC-1330 | #113 | 9/10 | type-safe-resource-references/prd.md |
| 7 | OSAC-917 | #66 | 9/10 | OSAC-1110-storage-tier/prd.md |
| 8 | OSAC-2540 | #120 | 9/10 | OSAC-2540-disk-image/prd.md |
| 9 | OSAC-1028 | #70 | 8/10 | (open PR, use diff) |
| 10 | OSAC-1061 | #150 | 5/10 | (merged but low-scoring, for calibration) |

## File Structure

```
prd-creator/
├── AGENTS.md                    # Project conventions
├── PLAN.md                      # This plan
├── scripts/
│   ├── frontmatter.py           # YAML frontmatter management
│   ├── state.py                 # State persistence for pipelines
│   ├── fetch_feature.py         # Fetch Jira feature content
│   └── score_prd.py             # Rubric scoring utilities
├── context/
│   ├── osac-dimensions.md       # Copied from .design/context/
│   ├── review-patterns.md       # Copied from .design/context/
│   ├── prd-template.md          # OSAC PRD template
│   └── exemplars/               # Top-scoring merged PRDs
│       ├── OSAC-1269-prd.md
│       ├── OSAC-2917-prd.md
│       └── OSAC-2872-prd.md
├── prompts/
│   ├── generate-prd.md          # Main PRD generation prompt
│   ├── review-prd.md            # PRD review/scoring prompt
│   ├── revise-prd.md            # PRD revision prompt
│   └── respond-feedback.md      # Reviewer feedback response prompt
├── eval/
│   ├── eval.yaml                # Evaluation config
│   └── dataset/
│       └── cases/               # Per-feature test cases
│           ├── OSAC-1269/
│           │   ├── input.yaml
│           │   ├── annotations.yaml
│           │   └── gold-prd.md
│           └── ...
└── artifacts/                   # Runtime output (gitignored)
    ├── prd-tasks/               # Generated PRDs
    ├── prd-reviews/             # Review results
    └── prd-originals/           # Pre-revision backups
```

## Success Criteria

1. Generated PRDs score 7+/10 on the rubric (pass) for well-defined features
2. Auto-fix improves scores by at least 1 point on average
3. Generated PRDs are structurally valid (all required sections present)
4. Generated PRDs use correct OSAC terminology and persona names
5. No design leakage (internal component names, controller logic)
6. Content traces back to Jira feature (no fabricated requirements)
