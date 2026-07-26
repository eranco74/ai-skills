# OSAC AI Skills

AI-assisted development skills for the OSAC (Open Sovereign AI Cloud) project.
Autonomous document generation, calibrated review, and SDLC automation.

Layers on top of [flightctl/ai-workflows](https://github.com/flightctl/ai-workflows)
with OSAC-specific autonomous skills.

## Skills

| Skill | Description |
|-------|-------------|
| `prd-creator` | Autonomous PRD generation from Jira Features |
| `design-creator` | Autonomous design document (EP) generation from PRDs |
| `prd-review` | PRD scoring rubric (5 criteria, /10) |
| `design-review` | Design scoring rubric (4 criteria, /8, UI-aware) |

## Forge Overrides

| Override | Replaces |
|----------|----------|
| `forge-skills/osac/generate-prd` | Forge default `generate-prd` |
| `forge-skills/osac/generate-spec` | Forge default `generate-spec` |

## Installation

```bash
# Into osac-workspace
git clone https://github.com/eranco74/ai-skills.git osac-ai-skills

# Into Forge
forge skills install --project osac ./osac-ai-skills/forge-skills
```

## Running Evals

```bash
cd skills/prd-creator && python3 scripts/run_eval.py --all
cd skills/design-creator && python3 scripts/run_eval.py --all
```
