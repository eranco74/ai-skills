# OSAC PRD Creator

Autonomous PRD generation from Jira Feature issues. Generates, self-reviews,
auto-fixes, and supports reviewer feedback loops — all without human interaction.

## Artifact Conventions

All artifacts live in `artifacts/` with YAML frontmatter managed by
`scripts/frontmatter.py`.

```
artifacts/
  prd-tasks/                 # Generated PRDs with YAML frontmatter
    OSAC-1269.md              # PRD keyed by Jira key
    OSAC-1269-source.md       # Raw Jira feature content
  prd-originals/             # Pre-revision backups
    OSAC-1269.md              # Baseline for diffing
  prd-reviews/               # Review files with YAML frontmatter
    OSAC-1269-review.md       # Rubric scores and feedback
    OSAC-1269-responses.md    # PR reviewer feedback responses
  prds.md                    # Generated index
```

### Frontmatter

```bash
python3 scripts/frontmatter.py schema prd-task
python3 scripts/frontmatter.py schema prd-review
python3 scripts/frontmatter.py set <path> field=value ...
python3 scripts/frontmatter.py read <path>
python3 scripts/frontmatter.py rebuild-index
```

### State Persistence

```bash
python3 scripts/state.py init <file> key=value ...
python3 scripts/state.py set <file> key=value ...
python3 scripts/state.py read <file>
python3 scripts/state.py write-ids <file> ID ...
python3 scripts/state.py read-ids <file>
python3 scripts/state.py clean
```

## Pipeline

```
Jira Feature → Fetch → Generate → Self-Review → Auto-Fix → Re-Review
```

### Usage

**Single feature:**
```bash
# In prd-creator directory:
# Step 1: Fetch Jira feature
python3 scripts/fetch_feature.py OSAC-1269 --output artifacts/prd-tasks/OSAC-1269-source.md

# Step 2: Generate PRD (invoke generate-prd.md agent prompt)
# Step 3: Review PRD (invoke review-prd.md agent prompt)
# Step 4: Auto-fix if needed (invoke revise-prd.md agent prompt)
# Step 5: Re-review
```

**Batch mode (headless):**
```bash
# Provide a YAML batch file:
# - jira_key: OSAC-1269
#   title: Managed Cluster Versions
# - jira_key: OSAC-2917
#   title: GPU-Enabled InstanceTypes
```

## Scoring Rubric

5 criteria, 0-2 each, /10 total:

| Criterion | What it checks |
|-----------|---------------|
| WHAT | Clear user-facing need with personas and services |
| WHY | Concrete business justification |
| User-Facing Focus | No design leakage (controllers, playbooks, etc.) |
| Right-Sized | One coherent feature, not bundled independents |
| Testability | Every requirement PM-verifiable |

**PASS**: Total >= 7/10 AND no zeros on any criterion.

## Context Files

| File | Purpose |
|------|---------|
| `context/prd-template.md` | OSAC PRD template (user stories by persona) |
| `context/osac-dimensions.md` | Services, personas, cross-cutting dimensions |
| `context/review-patterns.md` | Reviewer feedback patterns and anti-patterns |
| `context/scoring-rubric.md` | Calibrated rubric with examples |
| `context/exemplars/*.md` | Top-scoring merged PRDs as few-shot examples |

## Evaluation

```bash
# Run evaluation against known-good PRDs
# Uses eval/eval.yaml configuration
# Test cases in eval/dataset/cases/
```

See `eval/eval.yaml` for judges, thresholds, and dataset schema.
