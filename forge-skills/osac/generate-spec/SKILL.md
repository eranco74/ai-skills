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

1. **Every design decision traces to the PRD.** Mark unverified decisions `[Assumption]`.
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
