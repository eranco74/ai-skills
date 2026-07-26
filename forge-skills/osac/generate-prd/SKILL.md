---
name: generate-prd
description: Generate an OSAC Product Requirements Document from Jira Feature issues using OSAC-specific personas, dimensions, and scoring rubric.
---

# OSAC PRD Generator

You are generating a Product Requirements Document for the OSAC (Open Sovereign
AI Cloud) project. OSAC is a fulfillment system for provisioning Kubernetes
clusters, virtual machines, and bare metal instances with networking and storage.

## Instructions

1. Read the template from `skills/osac/generate-prd/prd-template.md`
2. Read the OSAC context from `skills/osac/generate-prd/osac-context.md`
3. Analyze the raw requirements from the Jira Feature
4. Fill in all template sections following the rules below
5. Validate against the quality checklist

## OSAC-Specific Rules

### Personas

OSAC has four canonical personas. Cover all affected ones with user stories:

| Persona | Role |
|---------|------|
| **Cloud Provider Admin** | Tenant onboarding, quotas, global catalogs, super-user |
| **Cloud Infrastructure Admin** | Core infrastructure, network/storage integrations |
| **Tenant Admin** | Org config, users, IDP, org-scoped catalogs |
| **Tenant User** | Self-service provisioning, lifecycle management |

Each affected persona gets a `### {Persona}` heading with at least one user story.
Unaffected personas get a one-line "Not affected by this feature." note.
If two personas have identical capabilities, combine them: `### Tenant Admin/User`.

### Services

Identify which OSAC services are affected:
- **BMaaS** — Bare Metal as a Service
- **CaaS** — Cluster as a Service (Hosted Control Planes)
- **VMaaS** — Virtual Machines as a Service (KubeVirt)
- **MaaS** — Model as a Service (AI/ML inference)
- **Enclave** — Day 1/Day 2 operations, installation

### Platform Vocabulary (Not Design Leakage)

These are user-visible and acceptable in PRDs:
- OpenShift, Kubernetes, Hosted Control Planes
- ClusterOrder, ComputeInstance, BareMetalInstance, Tenant
- VirtualNetwork, Subnet, SecurityGroup, PublicIP, StorageClass
- Keycloak, OPA, kubectl, Helm

These are internal and NOT acceptable in PRDs:
- Controller names, reconciler logic, finalizer behavior
- Playbook names, AAP job parameters, env vars
- CRD field names, internal conditions, SQLSTATE codes

### Cross-Cutting Dimensions

For each dimension relevant to the feature, address it in In Scope or Out of Scope:
- Tenant Onboarding, Inventory, Provisioning
- Networking, Storage, Installation
- E2E Testing, Documentation, UI

## Generation Rules

1. **Be Specific** — every requirement must be testable; no vague terms
2. **User-Centric** — describe from user perspective, not system perspective
3. **Measurable** — include metrics where data exists; don't invent them
4. **No Implementation** — no controllers, playbooks, internal components
5. **Honest Constraints** — an uncertain constraint is an assumption
6. **No Scope Creep** — scope matches Jira feature, not broader vision
7. **Right-Sized** — output depth proportional to feature complexity

## Size Calibration

Match output depth to feature complexity:
- **Simple feature** (1-2 capabilities): 30-50 lines, 4-6 Out of Scope items
- **Medium feature** (3-5 capabilities): 50-80 lines, 6-8 Out of Scope items
- **Complex feature** (5+ capabilities): 80-120 lines, 8-12 Out of Scope items

One user story per distinct user goal. Consolidate similar stories.
2-4 specific risks better than 6 generic ones. Each risk must name a failure mode.

## Source Traceability

Add `[Jira: {KEY}]` markers only when a requirement comes from a non-obvious
source (linked issue, comment). Add `[Assumption]` for any requirement not
directly stated in the Jira source. Follow the consolidation rule — don't
tag every statement when most trace to the primary Jira feature.

## Quality Checklist

- [ ] Problem statement clearly articulates user pain and cost of inaction
- [ ] At least 2 affected personas with per-persona user stories
- [ ] All user stories are specific (name artifacts, workflows, scenarios)
- [ ] In Scope lists user-observable capabilities only
- [ ] Out of Scope items pass boundary proximity test (reviewer would ask)
- [ ] No technical implementation details (controllers, playbooks, CRD fields)
- [ ] Risks name concrete failure modes with mitigations
- [ ] Output length matches feature complexity (size calibration)
- [ ] Source markers present for non-obvious requirements
- [ ] Technology constraints from Jira preserved (not abstracted away)
