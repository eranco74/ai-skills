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

## Optional Chai Evidence Research

Both OSAC generators can record feature-specific organizational evidence before
drafting. This is an optional runtime capability; these files do not install an
MCP server or contain its endpoint or credentials. To enable live research,
configure the organization-provided `chai_osac_public` MCP server in the MCP
client that runs Forge and expose its read-only `ask_persona(question)` tool.
The server URL and authentication come from that runtime's existing secure
configuration; do not infer or copy credentials into this repository.

### Forge runtime configuration

The audited Forge revision `9985378` reads a JSON mapping of server names to
LangChain MCP connections from `AGENT_MCP_CONFIG_PATH` (or its normal
`mcp-servers.json`). The [example connection](chai-mcp.example.json) uses the
[read-only bridge](../skills/_shared/scripts/chai_research_server.py), which
exposes exactly `ask_persona` and gives its upstream call 900 seconds. Install
`uv` in the runtime, make the full ai-skills checkout available there, and set:

```bash
export AI_SKILLS_CHECKOUT=/absolute/path/to/ai-skills
export AGENT_ENABLE_MCP=true
export AGENT_MCP_READ_ONLY=true
export AGENT_MCP_CONFIG_PATH="$AI_SKILLS_CHECKOUT/forge-skills/chai-mcp.example.json"
```

Provide `CHAI_OSAC_PUBLIC_MCP_URL` and `CHAI_OSAC_PUBLIC_MCP_TOKEN` through the
runtime's existing secret/environment configuration. The JSON contains variable
references, never their values. Merge this server entry into your existing MCP
mapping if you need its other servers. `AGENT_MCP_SERVERS` must include
`chai_osac_public` (its default `*` does).

The bridge is deliberate: that Forge revision's read-only filter uses names
such as create/update/delete and does not exclude `submit_feedback` or
`submit_lesson`. Exposing only `ask_persona` enforces this workflow's tool scope.
The bridge requires Python 3.10+; Forge itself requires 3.11+. Its TLS validation
uses system certificate trust, including your organization's installed CA.
The example is a runtime connection, separate from Forge's skill installation.
The local `devtools/test-skill/run.py` runner has no live MCP tools; its benchmark
must use an audited replay fixture and a separate connector check.

When the runner supplies additional per-run context, use these values:

- `research_mode`: `live`, `replay`, or `off`. If absent, default to `live`.
- `run_id`: use it when supplied; otherwise generate a fresh UUID for the run.
- `replay_record_path`: the validated evidence record to use in `replay` mode.
- `research_record_path`: the exact current-run output JSON path, when supplied.
- `document_output_path`: the final document file path. Filesystem-only runners
  default to `/home/user/prd.md` or `/home/user/design.md` so their collector can
  preserve the document independently of the agent's response text.
- research artifact workspace: use it when supplied; otherwise use the fallback
  path below.

These are values carried in the caller's context, not a documented Forge CLI
or project-property interface. Do not assume that Forge exposes a specific
input mechanism. In `live` mode, retrieve evidence only when a material
question remains; each run is bounded to one focused request and at most one
targeted follow-up. If `ask_persona` is not exposed, record `unavailable` and
continue from approved inputs. `replay` makes no live call; a missing or invalid
record is a setup error that stops drafting rather than completing research.
A valid fixture can contain an unavailable retrieval outcome. `off` skips
retrieval while still recording explicit Jira/PRD requirements.

If no tool is exposed or a call times out, the skill records an `unavailable` or
`timeout` status and continues from its approved inputs with the evidence gap
visible. Configure the MCP client with a practical long call timeout of about
900 seconds. Codex TOML server settings support `tool_timeout_sec = 900`; Forge
deployments should use the timeout setting supported by their runtime rather
than an assumed Forge-specific variable.

Research artifacts live beside the run artifacts. Forge's fallback directory
is `.artifacts/research/{run_id}/{KEY}/{stage}/`, containing
`{KEY}-research.json`, `{KEY}-research-brief.md`, and
`{KEY}-research-raw.md`. The raw sidecar retains live questions, complete raw
results, duration, and status; on unavailable calls or timeouts it retains the
attempted question and status. Replay preserves the supplied record's origin
without changing that input. Reviews reuse the same run record and check its
source references. Automatic generation uses only `ask_persona`; it does not
submit feedback or lessons.

The review also saves `{KEY}-coverage.json` beside the research record, binding
every explicit requirement ID to a covered passage, unresolved question, or
omission. Keep its identity aligned with the record after revision. Wire the
[external artifact check](../README.md) into your Python-capable caller before
promoting an artifact. A skill instruction is not an enforcement hook in Forge;
the check is a separate integration step and does not replace semantic or source
review. The shared helper lives in the full checkout, not a Forge-only skill copy.

For acceptance, the caller must use
[`review_gate.py`](../skills/_shared/scripts/review_gate.py), as described in the
[root README](../README.md#enforced-independent-review). It enforces the artifact
check and launches a separate semantic reviewer with original scope and primary
captures. A passing generator self-review cannot substitute for that step.
Use the existing Forge generation/revision runner, then the gate; retain failed
drafts and its `decision.json`. The local test runner needs an explicit MCP
adapter hook for live generation, since its audited default has no MCP tools.
Hosted Forge integration belongs between artifact collection and publication.
The supplied files and helper do not install that hosted integration.

## Files Per Skill

```
osac/
  generate-prd/
    SKILL.md              # Instructions with OSAC personas, dimensions, rules
    prd-template.md       # OSAC PRD template (user stories by persona)
    osac-context.md       # Architecture, resource hierarchy, review patterns
    steps/generate.md     # Jira scope extraction and evidence-record workflow
    context/organizational-research.md # Record schema and research rules
  generate-spec/
    SKILL.md              # Instructions with proto conventions, tenant isolation
    spec-template.md      # OSAC EP template (20+ sections, YAML frontmatter)
    osac-arch-context.md  # Architecture context for designs
    context/organizational-research.md # Record schema and research rules
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
