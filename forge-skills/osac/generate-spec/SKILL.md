---
name: generate-spec
description: Generate an OSAC design document (Enhancement Proposal) from an approved PRD using OSAC architectural patterns, proto conventions, and the EP template.
---

# OSAC Design Document Generator

You are generating a design document (Enhancement Proposal) for the OSAC project.
Design documents describe HOW — architecture, APIs, proto schemas, controller
logic, provisioning workflows. The PRD (WHAT/WHY) is your primary input.

## Instructions

1. Read the template from `skills/osac/generate-spec/spec-template.md`
2. Read the OSAC architecture context from `skills/osac/generate-spec/osac-arch-context.md`
3. Read the approved PRD for this feature
4. Explore the affected codebase components for existing patterns
5. Fill in all template sections — keep ALL required headers
6. Validate against the quality checklist

## OSAC Architectural Patterns

### Tenant Isolation (Mandatory)

All new resources MUST include:
- `osac.openshift.io/tenant` annotation for tenant scoping
- `osac.openshift.io/owner-reference` annotation for resource hierarchy
- OPA policies enforce isolation at runtime

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

1. **Every design decision traces to the PRD.** Mark unverified decisions `[Assumption]`.
2. **Include proto schemas** for any feature adding or modifying API resources. For UI-only features with no API changes, skip proto schemas entirely.
3. **Describe all CRUD operations** with specific error codes and validation rules.
4. **No hand-waving.** "Handle errors" → name the error codes. "Implement validation" → specify the rules.
5. **Honest constraints.** Uncertain constraints are `[Assumption]`, not facts.
6. **No scope creep.** Only design what the PRD requires. See Scope Discipline below.
7. **Resolution timing.** Prefer controller-time resolution (declarative) over API-time resolution. Store symbolic references in spec; resolve in controller.
8. **Use OSAC personas in workflows.** Always name actors as: Cloud Provider Admin, Cloud Infrastructure Admin, Tenant Admin, or Tenant User — never generic "Admin" or "User".
9. **Mark architectural uncertainty.** When the PRD doesn't specify which component to extend, mark the decision as `[Assumption]` and list an `[Open Question]`.

## Scope Discipline

The design must match the PRD's scope exactly. These are the most common scope violations — avoid them:

- **Do NOT invent observability content** (Prometheus metrics, alerts, Grafana dashboards, structured log events) unless the PRD specifically lists monitoring as In Scope. If the template's "Observability and Monitoring" section doesn't apply, write: "No new observability changes. Existing monitoring mechanisms apply."
- **Do NOT add feature flags**, administrative escape hatches, or force-delete mechanisms not in the PRD.
- **Do NOT create new resource types** (CRDs, proto messages, database tables) not mentioned or implied by the PRD.
- **Non-Goals must mirror the PRD's Out of Scope** items — translate them to design terms but do not add new ones or remove existing ones.
- **If a template section doesn't apply**, write "N/A — [brief explanation]" rather than inventing content to fill it.
- **Prefer extending existing components** over creating new ones. Reference the OSAC architecture context for existing patterns.

## Failure Handling Guidance

Always cover these OSAC-specific failure categories (when applicable to the feature):

- **Controller reconciliation failures**: transient API errors with exponential backoff, stale cache reads, behavior when controller restarts mid-reconciliation
- **Database-level failures**: Z0001 (immutable field violation), Z0002 (referential integrity), Z0003 (resource in use / delete protection)
- **AAP integration failures** (if applicable): job launch failure (HTTP timeout), job execution failure (callback with error), partial provisioning (job succeeds partially)
- **Race conditions**: resource deleted between validation and persistence, concurrent updates to the same resource
- **Cross-component failures**: fulfillment-service unavailable during controller reconciliation, Keycloak token exchange failure

For each failure mode, specify: what happens, how the system recovers, and what the user observes (error code, status condition, or UI state).

## Size Calibration

- **Simple feature** (single resource, no controller): 200-350 lines
- **Medium feature** (resource + controller + AAP): 350-500 lines
- **Complex feature** (multi-service, external integration): 500-700 lines

## Source Traceability

Use these markers:
- `[PRD: In Scope item N]` or `[PRD: User Story: {persona}]` — traces to PRD
- `[Assumption]` — unverified design decisions
- `[Codebase: {path}]` — references existing code patterns

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
- [ ] Output length matches feature complexity (size calibration)

## Evaluation

This skill is evaluated against gold-standard merged design documents:

- [`eval/eval.yaml`](eval/eval.yaml) — Forge eval harness config: invokes the skill with a Jira feature plus its approved PRD and scores the generated design against gold-standard merged designs.
- [`eval/eval_forge_design.py`](eval/eval_forge_design.py) — standalone judge that scores any generated design against the OSAC quality criteria above (works on any `design.md`, no Forge required).

Eval cases live under `eval/dataset/`. Re-run the harness to regenerate scores after changing the generation rules.
