# OSAC Design Creator

Autonomous design document (Enhancement Proposal) generation from Jira Feature
issues and their PRDs. Modeled on the [strat-creator](https://github.com/opendatahub-io/strat-creator)
and [rfe-creator](https://github.com/opendatahub-io/rfe-creator) architectures.

Design documents describe HOW — architecture, APIs, proto schemas, controller
logic, provisioning workflows. The PRD (WHAT/WHY) is the primary input.

## Pipeline

```
BATCH_START → FETCH → FETCH_PRD → GENERATE → ASSESS → REVIEW → REVISE → FIXUP
  → REASSESS_CHECK → [REASSESS loop max 2] → REPORT → DONE
```

## Skills

| Skill | Description |
|-------|-------------|
| `design.create` | Generate design from Jira feature + PRD |
| `design.review` | Score design against 4-criterion rubric |
| `design.respond` | Handle GitHub PR reviewer feedback |
| `design.speedrun` | End-to-end pipeline (headless) |

## Scoring Rubric (/8 total, pass at 5+)

| Criterion | What it checks |
|-----------|---------------|
| Architecture (0-2) | Tenant isolation, standard object shape, controller patterns, cross-repo changes |
| Feasibility (0-2) | Proto schemas, all CRUD ops, error codes, failure modes, risks with mitigations |
| Scope (0-2) | PRD referenced, design goals (not product goals), real alternatives, dimensions |
| Testability (0-2) | Specific unit/integration/e2e scenarios, measurable graduation criteria |

## What makes 8/8 vs 1/8

**8/8 designs:** Proto schemas for all resources, all CRUD lifecycle ops, concrete
failure modes with recovery, at least one real alternative, specific test scenarios,
tenant isolation on new resources, infrastructure reuse over new code.

**1/8 designs:** Schema/contract mismatches, hand-waving on hard parts, no proto
schemas, generic risks, placeholder test plans, missing tenant isolation, migration
as "destroy and rebuild" without validation.

## Context Files

| File | Purpose |
|------|---------|
| `context/design-template.md` | OSAC EP template (20+ sections) |
| `context/section-guidance.md` | Per-section writing instructions |
| `context/osac-dimensions.md` | Services, personas, cross-cutting dimensions |
| `context/review-patterns.md` | Reviewer expectations and anti-patterns |
| `context/scoring-rubric.md` | 4-criterion rubric with calibration examples |
| `context/exemplars/` | Top-scoring merged designs |

## Scripts

| Script | Purpose |
|--------|---------|
| `score_design.py` | Structure, frontmatter, proto, tenant isolation, placeholder, length checks |
| `frontmatter.py` | YAML frontmatter management (design-task, design-review schemas) |
| `pipeline_state.py` | State machine: phases, transitions, wave dispatch |
| `fetch_feature.py` | Fetch Jira feature via `jira` CLI |
| `state.py` | State persistence |
| `run_eval.py` | Evaluation orchestrator with gold comparison |

## Artifacts

```
artifacts/
  design-tasks/          # Generated designs
    OSAC-1269-design.md   # Design document
    OSAC-1269-source.md   # Jira feature content
    OSAC-1269-prd.md      # PRD content (input)
  design-originals/      # Pre-revision backups
  design-reviews/        # Review files with scores
  pipeline-runs/         # Pipeline run reports
```
