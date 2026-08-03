---
name: generate-prd
description: Generate an OSAC Product Requirements Document from Jira Feature issues using OSAC-specific personas, dimensions, and scoring rubric.
---

# OSAC PRD Generator

You are generating a Product Requirements Document for the OSAC (Open Sovereign
AI Cloud) project. OSAC is a fulfillment system for provisioning OpenShift
clusters, virtual machines, and bare metal instances with networking and storage.

## Critical Rules

These rules override all other guidance. Violating any of them is a document
failure regardless of other quality.

1. **Follow the template exactly.** The PRD has exactly 6 sections: Problem
   Statement, In Scope, Out of Scope, User Stories, Assumptions, Dependencies.
   Do NOT add sections the template doesn't have — no Terminology, no Milestone
   Scoping, no Acceptance Criteria, no Risks, no Open Questions. Extra sections
   are the most common review rejection.
2. **User-facing only.** Describe what users can do and observe. Never name
   controllers, reconcilers, finalizers, playbooks, conditions, env vars,
   CRD field names, SQLSTATE codes, or AAP job parameters. Those belong in
   the design document.
3. **Shorter is better.** A simple feature (1-2 capabilities) may need only
   10-20 lines. Do not pad output to look thorough. Every sentence must earn
   its place. Top-scoring PRDs average 60 non-blank lines; most over-generate,
   not under-generate.
4. **No fabrication.** Every requirement must trace to the Jira feature content.
   If information is missing, write "TBD" — do not invent customers, metrics,
   SLA numbers, or requirements.

## Instructions

1. Read the template from `skills/osac/generate-prd/prd-template.md`
2. Read the OSAC context from `skills/osac/generate-prd/osac-context.md`
3. Analyze the raw requirements from the Jira Feature
4. Fill in all template sections following the rules below
5. Validate against the quality checklist

## Design Leakage — The #1 Failure Mode

Reviewers reject PRDs that contain implementation details. Apply these smell
tests to every statement:

- **PM test:** Could a Product Manager verify this by using the product?
  If no → design leakage.
- **Swap test:** Would this statement change if the implementation changed?
  If yes → it's design, not requirements.
- **Code test:** Does this name something only visible in source code?
  If yes → design leakage.

### Examples of Design Leakage (Do NOT Include)

| Design Leakage | User-Facing Alternative |
|----------------|------------------------|
| "Exponential backoff with 5 retries" | "The system retries failed operations" |
| "BareMetalInstanceReady condition" | "The instance status reflects readiness" |
| "InfraEnv per cluster" | omit — internal architecture |
| "Deep disk wipe and network state reset" | "Hosts are securely sanitized before reuse" |
| "MAC normalization to IEEE format" | omit — internal formatting |
| "Metadata propagated within 60 seconds" | omit unless Jira specifies an SLA |
| "Synchronization every 10 minutes" | omit — implementation timing |
| "The controller uses AAP to install" | "Storage is automatically available" |
| "Finalizer prevents deletion until..." | "Resources are cleaned up on deletion" |
| "AwaitingHardwareDiscovery status" | omit — internal condition name |

### Platform Vocabulary (Acceptable in PRDs)

These are user-visible and NOT design leakage:
- OpenShift, Hosted Control Planes
- ClusterOrder, ComputeInstance, BareMetalInstance, Tenant
- VirtualNetwork, Subnet, SecurityGroup, PublicIP, StorageClass
- Keycloak, OPA, kubectl, Helm
- BMaaS, CaaS, VMaaS, MaaS, Enclave

## OSAC Personas

OSAC has four canonical personas. Cover all affected ones with user stories:

| Persona | Role |
|---------|------|
| **Cloud Provider Admin** | Tenant onboarding, quotas, global catalogs, super-user |
| **Cloud Infrastructure Admin** | Core infrastructure, network/storage integrations |
| **Tenant Admin** | Org config, users, IDP, org-scoped catalogs |
| **Tenant User** | Self-service provisioning, lifecycle management |

Each affected persona gets a `### {Persona}` heading with at least one user
story. Unaffected personas get a one-line "Not affected by this feature." note.
If two personas have identical capabilities, combine them: `### Tenant Admin / Tenant User`.

**User story validation:** A user story must describe something the persona
directly does or observes. "Tenant boundaries are enforced" is a platform
behavior, not a user story. "I want to view only my tenant's instances" is
a user story.

## OSAC Services

Identify which services are affected:
- **BMaaS** — Bare Metal as a Service
- **CaaS** — Cluster as a Service (Hosted Control Planes)
- **VMaaS** — Virtual Machines as a Service (KubeVirt)
- **MaaS** — Model as a Service (AI/ML inference)
- **Enclave** — Day 1/Day 2 operations, installation

## Section-by-Section Rules

### Problem Statement
- Lead with user pain, not the system gap.
- 2-4 sentences. If the problem is clear in 2, stop there.
- State the cost of inaction.

### In Scope
- Bullet list of user-observable capabilities this PRD delivers.
- Do NOT restate user stories here. In Scope adds boundary information that
  user stories alone wouldn't convey ("works for both new and existing
  clusters" is a boundary; "tenants can create volumes" duplicates a story).
- If there is nothing beyond what user stories convey, keep it to 2-4 bullets.
- Describe at a high level what types of features, capabilities, or personas
  are in scope — not detailed requirements.

### Out of Scope
- This section is **optional**. Only include what a reader would plausibly
  assume is included but isn't. If there's nothing non-obvious, omit the body.
- Each item should pass the **boundary proximity test**: would a reviewer
  ask "is this included?" If not, the item is too distant to mention.
- Do not pad with obviously unrelated items.

### User Stories
- One story per distinct user goal. If a story has "and", split it.
- Ground each story in concrete artifacts and scenarios — name what users
  interact with. "I want to see MAC addresses of my instance" is actionable;
  "I want to view hardware information" is too vague.
- Do NOT write user stories about internal platform behavior. "I want tenant
  isolation to be enforced" is not a user story — that's a platform
  invariant. "I want to view only my tenant's instances" is a user story.

### Assumptions
- Optional. Omit if no unverified assumptions exist.
- An assumption is something the PRD treats as true but hasn't been confirmed.
- Do NOT put API contracts, interface specs, or design-level details here.
  Those belong in the design document.

### Dependencies
- Optional. Omit if no external dependencies exist.
- Get the dependency direction right: "This feature enables X" is different
  from "This feature depends on X." A feature that exposes data for
  downstream consumers does NOT depend on those consumers — they depend on it.
- Name specific capabilities needed, not just Jira keys.

## Size Calibration

Match output depth to feature complexity. When in doubt, write less.

- **Simple feature** (1-2 capabilities): 15-40 lines
- **Medium feature** (3-5 capabilities): 40-70 lines
- **Complex feature** (5+ capabilities): 70-100 lines

One reviewer said of a 120-line PRD for a simple feature: "This doesn't
need to be 120 lines. Maybe 12? Shorter is better."

**Consolidation rules:**
- One user story per distinct user goal. Consolidate identical persona stories.
- Skip dimensions that don't apply — no "N/A" lines.
- Do not repeat information across sections.

## Source Traceability

Add `[Jira: {KEY}]` markers only when a requirement comes from a non-obvious
source (linked issue, comment). Add `[Assumption]` for any requirement not
directly stated in the Jira source. Most statements trace to the primary
feature — don't tag every one.

## Output Formatting (CI Pre-Commit)

The enhancement-proposals repo runs pre-commit checks in CI. The generated
PRD must pass these checks or the PR will fail:

1. **No trailing whitespace.** No spaces or tabs at the end of any line.
2. **Newline at end of file.** The file must end with exactly one newline.
3. **Directory naming convention.** The PRD must be placed in a directory
   named `{issue-key}-<slug>` where `{issue-key}` is the full Jira issue
   key including project prefix (e.g., `OSAC-2135`, not just `2135`) and
   `<slug>` is a lowercase kebab-case summary derived from the feature title.
   Example: `enhancements/OSAC-2135-caas-baremetal-provisioning/prd.md`.
   Do NOT use just the issue key without a slug — CI will reject it.
4. **Filename must be lowercase** `prd.md` — not `PRD.md` or `Prd.md`.

## Quality Checklist

Before finalizing, verify:

- [ ] **Template compliance** — exactly 6 sections, no extras
- [ ] **Problem statement** clearly articulates user pain and cost of inaction
- [ ] **In Scope** lists user-observable capabilities only, does not restate stories
- [ ] **User stories** are specific and per-persona (name artifacts, scenarios)
- [ ] **User stories** describe user actions, not platform behaviors
- [ ] **Out of Scope** items pass boundary proximity test (omit if nothing non-obvious)
- [ ] **No design leakage** — passes PM test, swap test, and code test
- [ ] **No invented SLAs** — timing numbers only if from Jira source
- [ ] **No extra sections** — no Risks, AC, Milestones, Terminology
- [ ] **Right-sized** — output length matches feature complexity
- [ ] **Dependency direction** is correct (enables vs depends on)
- [ ] **Technology constraints** from Jira preserved (not abstracted away)
- [ ] **No trailing whitespace** on any line
- [ ] **File ends with a single newline**
- [ ] **Directory name** follows `{issue-key}-<slug>` convention (e.g., `OSAC-2135-caas-baremetal-provisioning`)
