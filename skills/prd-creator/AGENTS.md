# OSAC PRD Creator

Autonomous PRD generation from Jira Feature issues. Modeled on the
[rfe-creator](https://github.com/opendatahub-io/rfe-creator) thin dispatcher
architecture: a pipeline state machine manages phases, scripts handle
deterministic operations, and LLM agents handle generation and review.

## Pipeline Architecture

```
BATCH_START → FETCH → GENERATE → ASSESS → REVIEW → REVISE → FIXUP
  → REASSESS_CHECK → [REASSESS loop max 2] → REPORT → DONE
```

### Phase Types

| Type | Description | Examples |
|------|-------------|----------|
| **noop** | Decision point, no dispatch | BATCH_START, REASSESS_CHECK |
| **script** | Deterministic Python execution | FETCH, ASSESS, FIXUP, REPORT |
| **agent** | LLM agent with background dispatch | GENERATE, REVIEW, REVISE |

### State Machine

The pipeline state machine (`scripts/pipeline_state.py`) manages:
- Phase tracking and transitions
- Wave-based agent dispatch
- Barrier synchronization (wait-for-wave)
- Reassess cycle limiting (max 2)
- ID filtering (which PRDs need revision)

### Dispatch Loop

The orchestrator (`skills/prd.speedrun/SKILL.md`) is a thin dispatcher (~80 lines)
that repeatedly calls `next-action` and executes the result:

```bash
python3 scripts/pipeline_state.py next-action    # Returns: run_script | launch_wave | done
python3 scripts/pipeline_state.py run-phase       # Execute script phases
python3 scripts/pipeline_state.py wait-for-wave   # Poll agent completion (exit 0=done, 3=pending)
```

## Skills

| Skill | Description | Mode |
|-------|-------------|------|
| `prd.create` | Generate PRD from Jira feature | Single |
| `prd.review` | Score PRD against rubric | Single/Batch |
| `prd.respond` | Handle GitHub PR reviewer feedback | Single |
| `prd.speedrun` | End-to-end pipeline | Batch/Headless |

## Artifact Conventions

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
  pipeline-runs/             # Pipeline run reports
    20260723-210404.yaml      # Timestamped YAML report
  prds.md                    # Generated index
```

### Frontmatter

```bash
python3 scripts/frontmatter.py schema prd-task    # PRD file schema
python3 scripts/frontmatter.py schema prd-review  # Review file schema
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

## Scripts

| Script | Purpose |
|--------|---------|
| `pipeline_state.py` | State machine: phases, transitions, wave dispatch |
| `fetch_feature.py` | Fetch Jira feature via `jira` CLI |
| `score_prd.py` | Deterministic checks: structure, personas, leakage |
| `frontmatter.py` | YAML frontmatter management |
| `state.py` | State persistence (survives context compression) |
| `collect_recommendations.py` | Route PRDs by review recommendation |
| `check_review_progress.py` | Poll agent progress via artifact files |
| `run_eval.py` | Evaluation orchestrator with gold comparison |

## Scoring Rubric

5 criteria, 0-2 each, /10 total. Pass: 7+/10 AND no zeros.

| Criterion | What it checks |
|-----------|---------------|
| WHAT | Clear user-facing need with personas and services |
| WHY | Concrete business justification with impact |
| User-Facing Focus | No design leakage (controllers, playbooks, etc.) |
| Right-Sized | One coherent feature, not bundled independents |
| Testability | Every requirement PM-verifiable |

## Context Files

| File | Purpose |
|------|---------|
| `context/prd-template.md` | OSAC PRD template (user stories by persona) |
| `context/osac-dimensions.md` | Services, personas, cross-cutting dimensions |
| `context/review-patterns.md` | Reviewer feedback patterns and anti-patterns |
| `context/scoring-rubric.md` | Calibrated rubric with scoring examples |
| `context/exemplars/*.md` | Top-scoring merged PRDs as few-shot examples |

## Evaluation

```bash
python3 scripts/run_eval.py --all --iteration N
```

Eval dataset in `eval/dataset/cases/` — 10 Jira features with gold-standard
merged PRDs for comparison. Deterministic checks + gold section/persona overlap.

### Evaluation Results (3 iterations)

| Metric | Iter 1 | Iter 2 |
|--------|--------|--------|
| Structure pass rate | 100% | 100% |
| Persona pass rate | 100% | 100% |
| No-leakage pass rate | 100% | 100% |
| Avg gold section overlap | 91% | 93% |
| Avg self-review score | 10.0/10 | 9.8/10 |
| Independent review (3 cases) | 3.3/5 | TBD |

**Key improvements from iteration 1 → 2:**
- Added acceptance criteria section guidance
- Fixed strategic framing (security vs convenience)
- Added failure scenario coverage
- Added tenant isolation call-outs
- Combined personas with identical capabilities
- Reduced Out of Scope filler
- Calibrated self-review (no longer all 10/10)

## File Structure

```
prd-creator/
├── AGENTS.md                    # This file
├── PLAN.md                      # Design plan
├── scripts/
│   ├── pipeline_state.py        # State machine core
│   ├── fetch_feature.py         # Jira feature fetch
│   ├── score_prd.py             # Deterministic scoring
│   ├── frontmatter.py           # YAML frontmatter
│   ├── state.py                 # State persistence
│   ├── collect_recommendations.py  # Review routing
│   ├── check_review_progress.py # Agent progress polling
│   └── run_eval.py              # Evaluation orchestrator
├── skills/
│   ├── prd.speedrun/SKILL.md    # End-to-end pipeline
│   ├── prd.create/SKILL.md      # Single PRD generation
│   ├── prd.review/SKILL.md      # PRD review/scoring
│   └── prd.respond/SKILL.md     # PR feedback response
├── prompts/
│   ├── generate-prd.md          # PRD generation instructions
│   ├── review-prd.md            # PRD scoring instructions
│   ├── revise-prd.md            # PRD revision instructions
│   └── respond-feedback.md      # Feedback response instructions
├── context/
│   ├── prd-template.md          # OSAC PRD template
│   ├── osac-dimensions.md       # Services, personas, dimensions
│   ├── review-patterns.md       # Reviewer expectations
│   ├── scoring-rubric.md        # Calibrated scoring rubric
│   └── exemplars/               # Top-scoring merged PRDs
├── eval/
│   ├── eval.yaml                # Evaluation configuration
│   ├── dataset/cases/           # Test cases with gold PRDs
│   └── results/                 # Evaluation reports
└── artifacts/                   # Runtime output (gitignored)
```
