# OSAC AI Skills

AI-assisted development skills for the [OSAC](https://github.com/osac-project)
(Open Sovereign AI Cloud) project. Autonomous document generation, calibrated
review, and SDLC automation.

Layers on top of [flightctl/ai-workflows](https://github.com/flightctl/ai-workflows)
(generic attended workflows) with OSAC-specific autonomous skills.

## Overview

```
Jira Feature
  → prd-creator: fetch → generate → self-review → auto-fix → publish PR
  → reviewers comment → autonomous revision → iterate until merged
  → design-creator: fetch PRD → generate design → self-review → auto-fix → publish PR
  → reviewers comment → autonomous revision → iterate until merged
```

## Skills

### Document Creators (autonomous, unattended)

| Skill | Description | Eval |
|-------|-------------|------|
| [`prd-creator`](skills/prd-creator/) | Generate PRDs from Jira Features. Self-reviews against 5-criterion rubric, auto-fixes, publishes to GitHub, responds to reviewer feedback. | 10 cases, 4.5/5 independent review |
| [`design-creator`](skills/design-creator/) | Generate design documents (EPs) from PRDs. Proto schemas, controller patterns, test plans. UI-aware type detection. | 6 cases, 100% gold section overlap |

### Reviewers (invoked on demand)

| Skill | Description |
|-------|-------------|
| [`prd-review`](skills/prd-review/) | Score a PRD against calibrated rubric: WHAT, WHY, User-Facing Focus, Right-Sized, Testability (/10, pass at 7+) |
| [`design-review`](skills/design-review/) | Score a design: Architecture, Feasibility, Scope, Testability (/8, pass at 5+). UI-aware — detects UI designs and adjusts proto/tenant checks. |

### Forge Overrides

Condensed versions of the OSAC domain knowledge for use with
[Forge](https://github.com/forge-sdlc/forge) as the automation backbone.
See [`forge-skills/README.md`](forge-skills/README.md) for installation.

## Usage

### Prerequisites

- `jira` CLI configured (for fetching Jira features)
- `gh` CLI authenticated (for publishing PRs)
- Python 3.9+ (for scripts — standard library only, no pip dependencies)

### Generate a PRD

```bash
cd skills/prd-creator

# 1. Fetch the Jira feature
python3 scripts/fetch_feature.py OSAC-1270 \
  --output artifacts/prd-tasks/OSAC-1270-source.md

# 2. Generate the PRD (in Claude Code, Cursor, or any AI tool)
#    Tell the agent:
#      "Read prompts/generate-prd.md and all context/ files,
#       then generate a PRD for OSAC-1270 from
#       artifacts/prd-tasks/OSAC-1270-source.md.
#       Write to artifacts/prd-tasks/OSAC-1270.md."

# 3. Run quality checks
python3 scripts/score_prd.py check-structure artifacts/prd-tasks/OSAC-1270.md
python3 scripts/score_prd.py check-personas  artifacts/prd-tasks/OSAC-1270.md
python3 scripts/score_prd.py check-leakage   artifacts/prd-tasks/OSAC-1270.md
python3 scripts/score_prd.py check-duplicates artifacts/prd-tasks/OSAC-1270.md
python3 scripts/score_prd.py check-length    artifacts/prd-tasks/OSAC-1270.md

# 4. Publish to enhancement-proposals as a draft PR
python3 scripts/publish_prd.py OSAC-1270

# 5. After reviewers comment, respond autonomously
python3 scripts/respond_prd.py OSAC-1270
```

### Generate a Design

```bash
cd skills/design-creator

# 1. Fetch feature + copy the merged PRD
python3 scripts/fetch_feature.py OSAC-1270 \
  --output artifacts/design-tasks/OSAC-1270-source.md
cp /path/to/enhancement-proposals/enhancements/OSAC-1270-*/prd.md \
  artifacts/design-tasks/OSAC-1270-prd.md

# 2. Generate the design (in Claude Code)
#    Tell the agent:
#      "Read prompts/generate-design.md and all context/ files,
#       then generate a design for OSAC-1270.
#       Write to artifacts/design-tasks/OSAC-1270-design.md."

# 3. Run quality checks
python3 scripts/score_design.py artifacts/design-tasks/OSAC-1270-design.md check-structure
python3 scripts/score_design.py artifacts/design-tasks/OSAC-1270-design.md check-proto
python3 scripts/score_design.py artifacts/design-tasks/OSAC-1270-design.md check-tenant-isolation
python3 scripts/score_design.py artifacts/design-tasks/OSAC-1270-design.md check-length

# 4. Publish and respond (same as PRD)
python3 scripts/publish_design.py OSAC-1270
python3 scripts/respond_design.py OSAC-1270
```

### Review an Existing PRD or Design

```bash
# In Claude Code from osac-workspace, with the skills installed:
/prd-review enhancement-proposals/enhancements/OSAC-1270-*/prd.md
/design-review enhancement-proposals/enhancements/OSAC-1270-*/design.md
```

## Evaluation

Each creator includes an eval dataset with gold-standard documents from
merged [enhancement-proposals](https://github.com/osac-project/enhancement-proposals) PRs.

```bash
# Run all PRD eval cases (10 cases)
cd skills/prd-creator && python3 scripts/run_eval.py --all

# Run all design eval cases (6 cases)
cd skills/design-creator && python3 scripts/run_eval.py --all

# Run a single case
python3 scripts/run_eval.py --cases OSAC-1270
```

### Latest Results

**prd-creator:**
- 10/10 cases pass all deterministic checks (structure, personas, leakage)
- 85% average gold section overlap
- 4.5/5 on independent pairwise review (one case rated "slightly better" than gold)

**design-creator:**
- 6/6 cases: 100% structure, 83% proto, 100% tenant isolation
- 100% gold section overlap, 199% proto coverage vs gold
- 7.5/8 average self-review score (calibrated)

## Installation

### Into osac-workspace

```bash
git clone https://github.com/eranco74/ai-skills.git osac-ai-skills
# Then link skills into .claude/skills/ via tools/link-agent-skills.sh
```

### Into Forge

```bash
forge skills install --project osac ./osac-ai-skills/forge-skills
```

Or set the `forge.skills` Jira project property to point to this repo.

### Standalone

The skills work independently — clone this repo and follow the usage
instructions above. Requires `jira` and `gh` CLIs but no osac-workspace
bootstrap.

## Relationship to flightctl/ai-workflows

| Repo | Provides | Mode |
|------|----------|------|
| [flightctl/ai-workflows](https://github.com/flightctl/ai-workflows) | Generic workflows: `/prd:ingest`, `/prd:clarify`, `/prd:draft`, `/design:draft` | Attended (human-in-the-loop) |
| This repo | OSAC-specific: `prd-creator`, `design-creator`, `prd-review`, `design-review` | Autonomous + on-demand review |

Both install into osac-workspace. Developers choose attended or autonomous.
The autonomous creators produce output compatible with ai-workflows downstream
phases (`/design:publish`, `/design:respond`).

## Architecture

### Pipeline (same pattern for both creators)

```
BATCH_START → FETCH → GENERATE → ASSESS → REVIEW → REVISE → FIXUP
  → REASSESS (max 2 cycles) → PUBLISH → RESPOND → DONE
```

- **Script phases** (Python): Jira fetch, deterministic scoring, provenance, publish
- **Agent phases** (LLM): generation, review, revision
- **State machine**: `scripts/pipeline_state.py` manages transitions and wave dispatch

### Scoring

**PRD rubric** (5 criteria, 0-2 each, /10):
WHAT, WHY, User-Facing Focus, Right-Sized, Testability

**Design rubric** (4 criteria, 0-2 each, /8):
Architecture, Feasibility, Scope, Testability

### Provenance

Uses [ai-workflows provenance system](https://github.com/flightctl/ai-workflows)
to track authoring metadata. Published documents include a `## Provenance` footer
and machine-readable `<!-- ai-workflow-provenance:{...} -->` comment.

## File Structure

```
osac-ai-skills/
├── AGENTS.md                         # This file
├── skills/
│   ├── prd-creator/                  # Autonomous PRD generation
│   │   ├── AGENTS.md                 # PRD creator conventions
│   │   ├── prompts/                  # Generation, review, revision instructions
│   │   ├── scripts/                  # Pipeline, scoring, publish, respond
│   │   ├── context/                  # Template, dimensions, rubric, exemplars
│   │   ├── eval/                     # 10 test cases with gold PRDs
│   │   └── skills/                   # Sub-skills (create, review, respond, speedrun)
│   ├── design-creator/               # Autonomous design generation
│   │   ├── AGENTS.md
│   │   ├── prompts/
│   │   ├── scripts/
│   │   ├── context/                  # Template, section guidance, exemplars
│   │   ├── eval/                     # 6 test cases with gold designs
│   │   └── skills/
│   ├── prd-review/                   # PRD scoring rubric
│   ├── design-review/                # Design scoring rubric (UI-aware)
│   └── _shared/                      # Shared scripts
│       └── scripts/
├── forge-skills/                     # Forge-compatible overrides
│   └── osac/
│       ├── generate-prd/
│       └── generate-spec/
└── .github/workflows/                # CI (skillsaw lint, eval runs)
```
