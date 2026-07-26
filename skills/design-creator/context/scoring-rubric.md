# OSAC Design Document Scoring Rubric

## Overview

This rubric evaluates OSAC design documents using a calibrated 0-2 scoring system across 4 dimensions. A design document describes HOW a feature will be implemented — architecture, API design, controller logic, provisioning workflows. It builds on a PRD (WHAT/WHY) and provides enough detail for engineering to estimate, plan, and implement.

## Template Completeness Prerequisites

Before scoring, verify structural completeness. Missing required sections count against the relevant dimension scores:

- **YAML frontmatter**: title, authors, creation-date, last-updated, tracking-link (full URL), prd (relative path to PRD)
- **Required sections**: Summary, Motivation (Goals, Non-Goals), Proposal (Workflow Description, API Extensions, Implementation Details, Security Considerations, Failure Handling and Recovery, RBAC/Tenancy, Observability and Monitoring, Risks and Mitigations, Drawbacks), Alternatives, Test Plan
- **Conditionally required**: UX Alignment (required only when a matching `@temp-api` file exists in `osac-ux/libs/ui-components/src/api/v1/`)
- **PRD reference**: the `prd:` frontmatter field or an explicit link to `prd.md` must be present — user stories and persona coverage belong in the PRD, not the design
- **Placeholder-only sections**: `TBD` with no other content, or a lone `TODO:` line with no other content count against the relevant dimension score
- **N/A sections**: Sections that are genuinely N/A must explain why — silence is a gap

## Scoring Criteria (0-2 each, /8 total)

Score each criterion independently. For each, first state your reasoning, then assign the score. Missing or placeholder-only sections that are relevant to a criterion pull that criterion's score toward 0.

### 1. Architecture (0-2)

**Question**: Are the technical decisions sound and consistent with OSAC patterns?

#### Checklist

- [ ] Owner reference (`osac.openshift.io/owner-reference`) and tenant isolation (`osac.openshift.io/tenant`) annotations present on all new resources
- [ ] API conventions per `fulfillment-service/docs/API.md`: standard object shape (`id`, `Metadata`, `<Type>Spec`, `<Type>Status`), spec/status ownership, declarative intent-based design (no imperative methods), naming conventions
- [ ] Spec contains only desired state (user-controlled); status contains only observed state (system-controlled)
- [ ] Controller patterns: finalizer → status update → provisioning lifecycle
- [ ] Conditions used for lifecycle state (preferred over phase enums for new resources)
- [ ] Maps avoided in CRDs (prefer lists of named subobjects); pluggable architectures preferred over hardcoded implementations
- [ ] Dependencies between components identified with ordering, and cross-repo impacts enumerated
- [ ] Integration with existing services described
- [ ] Breaking changes called out with migration strategies
- [ ] Terminology defined upfront and used consistently throughout

#### Scoring Scale

- **0** = Fundamental architectural misalignment — missing tenant isolation, wrong patterns, no dependency analysis
- **1** = Core patterns followed but gaps — some conventions missed, integration partially described, inconsistent terminology
- **2** = All OSAC patterns followed, dependencies clear, integration well-described, terminology consistent

#### Calibration Examples

**A=0**: Design introduces new CRDs without tenant annotation, uses direct DB access instead of gRPC, proto schemas don't follow standard object shape, doesn't mention which repos need changes.

**A=1**: Design follows controller patterns and has tenant isolation, proto schemas use standard object shape but mix spec/status ownership (e.g., user-modifiable fields in status), doesn't describe interaction with osac-aap for provisioning.

**A=2**: Design follows all conventions, describes the full resource hierarchy with owner references, enumerates cross-repo changes (fulfillment-service proto + osac-operator controller + osac-aap role), and defines terminology upfront.

---

### 2. Feasibility (0-2)

**Question**: Is the implementation realistic, specific, and proportional to the scope?

#### Checklist

- [ ] Implementation details are specific — names data structures, specifies error codes, defines validation rules
- [ ] Proto schemas included for new resources (at least key fields, types, constraints)
- [ ] No hand-waving on hard parts (avoid vague phrases like `handle edge cases appropriately` or `implement as needed`)
- [ ] Effort is proportional to scope
- [ ] Workflow covers all lifecycle operations (create, get, list, update, delete)
- [ ] Error handling and failure modes described
- [ ] Risks are specific technical risks with concrete mitigations
- [ ] Drawbacks section steel-mans the argument against the proposal

#### Scoring Scale

- **0** = Vague implementation — no proto schemas, hand-waving on hard parts, generic risks ("things might break")
- **1** = Reasonable detail but gaps — some lifecycle operations missing, risks somewhat generic, thin error handling
- **2** = Deep technical detail, proto schemas present, all lifecycle ops covered, risks with concrete mitigations

#### Calibration Examples

**F=0**: Example of vague implementation: `The controller will handle provisioning appropriately` with no detail on what provisioning means, no proto schema, and risks like "implementation might be complex."

**F=1**: Design includes proto schemas for the main resource and describes create/get/list, but update and delete flows are "TBD." Risks mention "race conditions" without specifying which ones or how to mitigate.

**F=2**: Design includes full proto schemas with field types and validation annotations, describes all CRUD lifecycle operations with error codes, identifies specific risks ("concurrent subnet allocation may cause CIDR overlap") with concrete mitigations ("use optimistic locking with resource version").

---

### 3. Scope (0-2)

**Question**: Is the design right-sized with clear boundaries, covering relevant personas and dimensions?

#### Checklist

- [ ] Summary is 3-5 sentences: what's added, why it's valuable, key capabilities
- [ ] Goals are user-visible outcomes, not implementation tasks
- [ ] Non-goals are specific about what's explicitly out of scope and why
- [ ] No scope creep signals ("and related functionality", "all necessary changes")
- [ ] Alternatives section includes at least one real alternative with rationale for rejection
- [ ] Design references its PRD (`prd:` frontmatter or link to `prd.md`) and addresses relevant personas through architectural decisions
- [ ] Cross-cutting dimension coverage: for each dimension relevant to this design (from `.design/context/osac-dimensions.md`), the design must address it or explicitly defer. Silence on a relevant dimension is a gap.

#### Scoring Scale

- **0** = Scope unbounded, no PRD reference, vague non-goals, no alternatives, relevant dimensions ignored
- **1** = Boundaries mostly clear, PRD referenced but some relevant dimensions not addressed, non-goals could be more specific
- **2** = Clear boundaries, PRD referenced, specific non-goals, real alternatives, relevant dimensions addressed or deferred

#### Calibration Examples

**S=0**: Design has no PRD reference, no non-goals, and says "Alternatives: none considered." Storage dimension is relevant but not mentioned.

**S=1**: Design references a PRD but non-goals say "advanced features are out of scope" without specifying which. Networking dimension acknowledged but not addressed. Cloud Provider Admin perspective not covered in workflow description.

**S=2**: Design references its PRD, non-goals explicitly exclude auto-scaling and multi-region ("deferred to v0.2, see OSAC-XXXX"), alternatives section compares two real approaches with trade-offs, and all relevant dimensions from osac-dimensions.md are addressed or explicitly deferred.

---

### 4. Testability (0-2)

**Question**: Does the design describe a concrete test strategy that would catch regressions?

#### Checklist

- [ ] Test plan describes strategy per level: unit, integration, e2e
- [ ] Unit tests specify what's tested (validation logic, state transitions, error paths)
- [ ] Integration tests describe test infrastructure (kind cluster, mocked backends, etc.)
- [ ] E2E tests describe user-observable scenarios
- [ ] Graduation criteria are concrete conditions, not vague milestones

#### Scoring Scale

- **0** = No test plan, or placeholder ("tests will be added"). Graduation criteria absent or vague.
- **1** = Test plan mentions unit/integration/e2e but lacks specifics — doesn't say what's tested or how. Graduation criteria present but generic.
- **2** = Test plan specifies what's tested at each level with concrete scenarios. Graduation criteria are measurable conditions.

#### Calibration Examples

**T=0**: "Unit and integration tests will be added" — no specifics on what's tested.

**T=1**: "Unit tests for proto validation, integration tests with kind cluster" — right categories but no specific scenarios. Graduation criteria: "feature is stable."

**T=2**: "Unit tests for CIDR validation and overlap detection; integration tests for subnet creation and attachment using kind cluster with mock network backend; e2e test for full tenant workflow: create VirtualNetwork → create Subnet → attach to ComputeInstance → verify connectivity." Graduation criteria: "All CRUD operations pass e2e, error paths tested, no regressions in existing networking tests."

---

## Pass/Fail Thresholds

- **PASS**: Total >= 5/8 AND no zeros on any criterion
- **FAIL**: Total < 5 OR any zero (automatic fail regardless of total)

**Rationale**: A single zero is an automatic fail because it signals a fundamental problem (e.g., no test plan, or architectural misalignment). The author must fix zero-scored criteria before resubmission.

---

## Severity Classification

Use these severity levels when reporting findings:

- **Critical**: Any zero-scored criterion. Also: missing tenant isolation on new resources, fundamental architectural misalignment, breaking changes without migration path, security gaps.
- **Important**: Score of 1 on any criterion. Also: incomplete sections, missing personas, unclear workflow, vague non-goals, generic risks, thin implementation details, relevant dimension neither addressed nor deferred.
- **Suggestion**: Style improvements, deeper alternatives discussion, more specific test plan, documentation polish.

---

## Review Guidelines

- Score based on what's in the design, not what you think should be there
- Use `osac-dimensions.md` to decide relevance per dimension — skip Networking for a storage-only design. When a dimension is relevant, require address-or-defer — silence is a gap
- Reference merged designs in `enhancement-proposals/enhancements/` for calibration on depth and style
- Push for specificity: "handle errors" is not a mitigation; "retry with exponential backoff, circuit-break after 3 failures" is
- The review process requires consensus from all stakeholders — flag sections that would likely trigger stakeholder questions
