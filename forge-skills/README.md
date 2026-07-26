# OSAC Forge Skill Overrides

Custom [Forge](https://github.com/forge-sdlc/forge) skill overrides for the OSAC
project. These replace Forge's stack-agnostic defaults with OSAC-specific knowledge:
personas, services, API conventions, proto patterns, tenant isolation, and
calibrated scoring.

## Skills Provided

| Skill | Overrides | What's Different |
|-------|-----------|-----------------|
| `generate-prd` | `skills/default/generate-prd` | OSAC PRD template (user stories by persona), 4 canonical personas, 5 services, cross-cutting dimensions, size calibration, design leakage rules |
| `generate-spec` | `skills/default/generate-spec` | OSAC EP template (20+ sections), proto schema conventions, tenant isolation requirements, gRPC error codes, controller patterns, resolution timing rules |

## Installation

### Option 1: Forge CLI

```bash
forge skills install --project osac /path/to/osac-workspace/forge-skills
```

### Option 2: Manual Copy

```bash
cp -r forge-skills/osac/ /path/to/forge/skills/osac/
```

### Option 3: Jira Project Property

Set the `forge.skills` property on the OSAC Jira project:

```json
{
  "sources": [
    {
      "url": "https://github.com/osac-project/osac-workspace.git",
      "path": "forge-skills",
      "ref": "main"
    }
  ]
}
```

## How It Works

Forge resolves skills using a three-tier hierarchy:

1. `skills/default/` — Stack-agnostic defaults (always loaded)
2. `skills/{project}/` — Project-specific overrides (loaded if directory exists)

When processing an `OSAC-*` ticket, Forge extracts the project key `osac`,
finds `skills/osac/`, and loads those skills. Overrides completely replace the
default skill with the same name — other default skills remain available.

## Files Per Skill

```
osac/
  generate-prd/
    SKILL.md              # Instructions with OSAC personas, dimensions, rules
    prd-template.md       # OSAC PRD template (user stories by persona)
    osac-context.md       # Architecture, resource hierarchy, review patterns
  generate-spec/
    SKILL.md              # Instructions with proto conventions, tenant isolation
    spec-template.md      # OSAC EP template (20+ sections, YAML frontmatter)
    osac-arch-context.md  # Architecture context for designs
```

## Relationship to prd-creator / design-creator

These Forge skill overrides embed the same domain knowledge as the standalone
`prd-creator/` and `design-creator/` tools but in Forge's skill format. The
standalone tools additionally provide:

- Pipeline state machine for batch processing
- Deterministic scoring scripts (Python)
- Auto-fix loop with reassessment
- Evaluation harness with gold-standard comparison
- Provenance tracking via ai-workflows

When using Forge as the automation backbone, these overrides provide the domain
knowledge while Forge handles the workflow orchestration (Jira events, GitHub PRs,
label management, task decomposition).
