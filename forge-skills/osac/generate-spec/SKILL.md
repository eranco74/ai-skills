---
name: generate-spec
description: Generate an OSAC design document (Enhancement Proposal) from an approved PRD using OSAC architectural patterns, proto conventions, and the EP template.
---

# OSAC Design Document Generator

You are generating a design document (Enhancement Proposal) for the OSAC project.
Design documents describe HOW — architecture, APIs, proto schemas, controller
logic, provisioning workflows. The PRD (WHAT/WHY) is your primary input.

## Critical Rules

1. **Complete evidence artifacts before drafting.** A supplied `research-input.json`
   or replay record is input, not proof that this run's completion artifacts
   were saved. Before drafting, write the current-run research JSON and cited
   brief to the caller's `research_record_path` or `artifact_workspace`, then
   reread and validate them. Verify required fields and enums, references, and
   exact feature/stage/run/mode identity. If replay input is missing or invalid,
   or either artifact cannot be written or validated, stop without drafting a
   design.
2. **Keep material conflicts open.** An unresolved material conflict must be
   visible in an existing template section and means the design is not ready for
   implementation.
3. **Return only the design document.** Do not include a preamble, progress
   note, separator, self-review, rubric, explanation, or epilogue. If an evidence
   setup or completion-artifact gate fails, stop and report only the specific
   failure and required path.
4. **Persist the reviewed result.** Write `{KEY}-coverage.json` beside the
   research record using the organizational contract's machine-readable schema,
   accounting for every requirement ID. Recheck it after revision. Save the final
   document to the caller's `document_output_path` before responding; a
   filesystem-only runner uses `/home/user/design.md` if no path is supplied.

The coverage file uses these exact keys with all requirement IDs, not alternative
`coverage`/`requirement_id` keys:

```json
{"schema_version":1,"feature_key":"KEY","stage":"design","run_id":"RUN_ID",
 "requirements":[{"id":"R1","status":"unresolved","evidence":"Actual design passage or open question"}]}
```

## Evidence and Scope Before Drafting

Before drafting, read
`skills/osac/generate-spec/context/organizational-research.md` and follow its
research, record, citation, and source-checking contract. Use caller-provided
per-run context when present: `research_mode`, `run_id`, `replay_record_path`,
`research_record_path` (the output JSON path), and `artifact_workspace` (an
output directory). These are contextual values, not assumed Forge CLI flags or
a Forge-specific configuration interface. If
`research_mode` is absent, use `live`; if the selected mode is `live` and
`ask_persona` is not exposed, record `unavailable`. `replay` uses the supplied
validated record and makes no live call. A missing or invalid `replay_record_path`
is a setup error: stop before drafting, report it, and do not create a completion
record or switch to live. A valid fixture can contain an unavailable retrieval
outcome. Use the `design` stage.
Reuse relevant verified evidence from a supplied PRD-stage
record when applicable; do not repeat broad research during review or
revision. In `live` mode, ask only feature-specific questions about accepted
architecture decisions, constraints, or dependencies that materially help
explain the design. Chai provides rationale and source references; it is not
authority to expand scope or evidence of current code behavior.

Use the supplied `run_id` when present; otherwise generate a fresh UUID for
this run and do not reuse a previous run's identifier. Save the current-run JSON
to the supplied `research_record_path` when present; otherwise use the supplied
`artifact_workspace` and name the file `{KEY}-research.json`; otherwise use
`.artifacts/research/{run_id}/{KEY}/design/{KEY}-research.json`. Save
`{KEY}-research-brief.md` and `{KEY}-research-raw.md` beside the JSON. A supplied
record is input only. Never overwrite `replay_record_path` or an artifact from
another run; if the requested output path is the replay input, use a distinct
artifact-workspace or fallback path. For replay, validate the supplied record
against the current issue and stage, preserve its origin in the sidecar, and do
not modify the supplied input. Save a current-run copy at the current output
path. For live calls, retain the exact question, complete raw `ask_persona`
result, call duration, and status in the raw sidecar. For unavailable tools or
timeouts, retain the attempted question and status even when there is no raw
result. Do not imply research succeeded or invent sources, decisions, or
citations.

**Completion gate — required before drafting:** Use `write_file` to save the
current-run JSON and cited brief in the selected output location in every mode,
including `replay`, `off`, `unavailable`, and `timeout`. Include explicit scope
requirements from the approved PRD and applicable recorded owner decisions;
keep them separate from claims and assumptions. Reread both saved files with
`read_file`. Verify required fields and types, `schema_version: 1`, allowed
enums, unique IDs, and that every referenced source ID exists. Verify identity
exactly matches this run's Jira key, `stage: design`, `run_id`, and
`research_mode`; verify status reflects the actual result. Check that the brief
agrees with the record, includes source URLs, dates, and revisions, and presents
factual claims only when every supporting source is verified. If any artifact
is missing or fails validation, stop without drafting and report only the
failed artifact path and validation issue.

If material questions remain because evidence could not be retrieved or
checked, surface them as `[Open Question]` items and state that the design is
not ready for implementation; retrieval failure does not mean no decision
exists.

After adding approved PRD requirements, research claims, questions, and
conflicts, update the current-run JSON and brief, then reread and recheck their
identity and references. A material unresolved conflict prevents the design
from being marked ready for implementation.

After the first design draft and every revision, update the cited-brief
coverage sidecar with one row for each explicit approved-PRD requirement ID.
Mark each `covered`, `unresolved`, or `omitted` and identify the design section
or open question. Translate technical acceptance criteria into user-visible
outcomes for observable behavior; preserve remaining test, resource-audit,
default-resolution, and other verification obligations in the sidecar/handoff.
Do not drop requirements to meet length or avoid detail; a material omission
prevents readiness. An unresolved owner decision remains a question, not a
design commitment. Reread the updated sidecar before declaring readiness.

Do not infer authorization to see diagnostic payloads from a persona's tenant
visibility. Verify the audience against an explicit approved requirement or
existing access control checked in code. If authorization is unknown, keep it
as an `[Open Question]` in the design and evidence sidecar; do not present the
audience as entitled to the payload.

The approved PRD is the primary authority for design scope. Keep its In Scope
and Out of Scope boundaries intact. Separate PRD requirements, explicit
accepted owner decisions, proposals, assumptions, and claims about existing
implementation. `Implemented` evidence describes existing behavior; confirm it
against code and cite the code path independently. `Proposed`, `superseded`,
and `unknown` claims are not settled decisions. If Chai and the PRD conflict,
retain the conflict as unresolved in the record, preserve the approved PRD's
scope for this design, and surface a material issue as an `[Open Question]`.
Do not silently resolve the conflict. A material unresolved
conflict means the design is not ready for implementation; say so in an
appropriate existing section without adding a new template heading. Record the
inspected repository revision with the code references.

## Instructions

1. Read the template from `skills/osac/generate-spec/spec-template.md`
2. Read the OSAC architecture context from `skills/osac/generate-spec/osac-arch-context.md`
3. Read the approved PRD and the applicable organizational-research record
4. Explore affected codebase components and independently verify current patterns
5. Fill in all template sections — keep ALL required headers
6. Validate against the quality checklist and evidence record

## OSAC Architectural Patterns

### Standard Object Shape

All fulfillment-service resources follow:
```protobuf
message {Resource} {
  string id = 1;
  Metadata metadata = 2;
  {Resource}Spec spec = 3;
  {Resource}Status status = 4;
}
```
- **Spec** = desired state (user-controlled)
- **Status** = observed state (system-controlled, includes conditions)
- **Conditions** preferred over phase enums for lifecycle state

### Tenant Isolation (Mandatory)

All new resources MUST include:
- `osac.openshift.io/tenant` annotation for tenant scoping
- `osac.openshift.io/owner-reference` annotation for resource hierarchy
- OPA policies enforce isolation at runtime

### Controller Pattern

Controllers follow: finalizer → status update → provisioning lifecycle.
Use `provisioning.RunProvisioningLifecycle()` for provision/deprovision.

### API Conventions

Read `fulfillment-service/docs/API.md` for:
- Declarative intent-based design (no imperative methods)
- gRPC services with REST transcoding via `google.api.http`
- Standard CRUD: Create, Get, List, Update, Delete
- Conditions for lifecycle (preferred over phase enums)

### Stack-Aware Error Format

OSAC uses gRPC error codes, NOT HTTP status codes:
- `INVALID_ARGUMENT` — validation failure
- `NOT_FOUND` — resource does not exist
- `ALREADY_EXISTS` — duplicate name/resource
- `FAILED_PRECONDITION` — state-based rejection (e.g., version is obsolete)
- `ABORTED` — concurrent modification conflict

PostgreSQL SQLSTATE codes for database triggers:
- `Z0001` — immutable field violation
- `Z0002` — referential integrity violation
- `Z0003` — resource in use (delete protection)

Map SQLSTATE → gRPC via the `translateError` function.

## Generation Rules

1. **Keep scope anchored in the approved PRD.** Trace design decisions to PRD
   requirements, independently verified code patterns, or verified
   organizational rationale with its decision state preserved. Treat an
   explicit accepted owner decision as a decision; treat proposals and unknowns
   as open questions or `[Assumption]`. Chai rationale cannot add product scope.
2. **Include proto schemas** for any feature adding or modifying API resources.
3. **Describe all CRUD operations** with specific error codes and validation rules.
4. **No hand-waving.** "Handle errors" → name the error codes. "Implement validation" → specify the rules.
5. **Honest constraints.** Uncertain constraints are `[Assumption]`, not facts.
6. **No scope creep.** Only design what the PRD requires.
7. **Resolution timing.** Prefer controller-time resolution (declarative) over API-time resolution. Store symbolic references in spec; resolve in controller.

## Size Calibration

- **Simple feature** (single resource, no controller): 200-350 lines
- **Medium feature** (resource + controller + AAP): 350-500 lines
- **Complex feature** (multi-service, external integration): 500-700 lines

## Source Traceability

Use these markers:
- `[PRD: In Scope item N]` or `[PRD: User Story: {persona}]` — traces to PRD
- `[Assumption]` — unverified design decisions
- `[Codebase: {path} @ {revision}]` — references independently checked code patterns
- `[Chai:CLAIM_ID]` — feature-relevant organizational rationale; include a
  nearby link to its verified original source and retain source URL, date, and
  revision in the durable evidence record/cited brief

Do not present claims marked `proposed`, `superseded`, `unknown`, or
unverified as settled facts. An `implemented` claim describes existing
behavior, not an approved future requirement; verify it directly in code at a
recorded repository revision.
Material unresolved conflicts stay unresolved in the record, are surfaced in
the applicable existing template section as an `[Open Question]`, and make the
design not ready for implementation. Cite Chai for feature-relevant rationale
with source IDs and verify all implementation claims in code.

## Quality Checklist

- [ ] All required template sections present (explain N/A sections, don't remove)
- [ ] YAML frontmatter with title, authors, creation-date, tracking-link, prd
- [ ] Proto schemas for all new/modified API resources
- [ ] Tenant isolation (`osac.openshift.io/tenant`, `osac.openshift.io/owner-reference`)
- [ ] All CRUD lifecycle operations described (Create, Get, List, Update, Delete)
- [ ] Error codes are gRPC (not HTTP) and specific to each operation
- [ ] Failure modes enumerated with recovery behavior
- [ ] At least one real alternative with rejection rationale
- [ ] Test plan names specific behaviors at unit/integration/e2e levels
- [ ] Graduation criteria are measurable conditions
- [ ] Cross-repo changes enumerated (fulfillment-service, osac-operator, osac-aap)
- [ ] Source markers present for PRD-derived and assumed decisions
- [ ] Each Chai-backed rationale cites a claim ID with a checked source in the
      durable record/cited brief; every material research-derived statement has
      an inline `[Chai:CLAIM_ID]` marker and nearby link to its verified
      original source; each source URL/date/revision is recorded; code claims
      are checked at a recorded revision
- [ ] Every explicit approved-PRD requirement ID appears in the cited-brief
      coverage sidecar as `covered`, `unresolved`, or `omitted`, mapped to a
      design section or open question; no material requirement is omitted and
      remaining verification duties are preserved
- [ ] Diagnostic payload access is limited to audiences authorized by an
      explicit approved requirement or access controls verified in code;
      unresolved authorization remains an open question
- [ ] Material evidence conflicts remain unresolved in the record and are
      surfaced as open questions rather than silently resolved
- [ ] The current-run JSON and cited brief exist, were reread, and match the
      Jira key, `design` stage, run ID, and research mode
- [ ] No material unresolved conflict is described as ready for implementation
- [ ] Output length matches feature complexity (size calibration)

The final response must contain only the design document, starting with its
title and ending with its final document line.
