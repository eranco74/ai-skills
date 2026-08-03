# OSAC Context for PRD Generation

## What is OSAC?

OSAC (Open Sovereign AI Cloud) is a fulfillment system for provisioning
OpenShift clusters and compute instances with networking capabilities.

## Architecture

```
fulfillment-service    gRPC/REST API server, PostgreSQL
osac-operator          Kubernetes operator, provisions via AAP + HCP
osac-aap               Ansible playbooks for VM and network provisioning
osac-installer         Helm charts, deploys all components to OpenShift
osac-test-infra        E2E test playbooks against Fulfillment API
osac-ui                Web console (React, PatternFly 6)
```

## Resource Hierarchy

```
Tenant → namespace and network isolation
ClusterOrder → OpenShift clusters via Hosted Control Planes
VirtualNetwork → L2 network with CIDR
  ├── Subnet → CIDR range within VirtualNetwork
  └── SecurityGroup → firewall rules
ComputeInstance → KubeVirt VM
BareMetalInstance → physical machine
PublicIPPool → IP address ranges
  └── PublicIP → allocated from pool
```

## Domain Knowledge (Common Mistakes to Avoid)

These domain facts have caused PRD rejections when gotten wrong:

- **OpenShift, not Kubernetes.** OSAC provisions OpenShift clusters. Use
  "OpenShift" unless referring to general Kubernetes concepts.
- **IP addresses are NOT inventory.** IP addresses are a function of what
  network a host is attached to — they change based on network configuration.
  MAC addresses are hardware identifiers. Do not treat IPs as a property of
  the physical host inventory.
- **There is no "primary" interface.** Bare metal hosts have multiple NICs.
  OSAC does not define which is "primary" — that concept does not exist in
  the platform. If the feature involves NICs, consider surfacing all
  interfaces rather than assuming one is special.
- **Tenancy ≠ Kubernetes namespaces.** OSAC tenant isolation is enforced via
  BMaaS/fulfillment-service authorization boundaries, not Kubernetes
  namespaces. Do not conflate the two.
- **Dependency direction matters.** A feature that exposes data (e.g., MAC
  addresses in status) does NOT depend on the downstream consumer (e.g.,
  CaaS). The consumer depends on the feature. Get this right in the
  Dependencies section.
- **Milestones are not PRD content.** Do not include milestone targets,
  version numbers, or release timelines in the PRD.

## PRD vs Design: What Belongs Where

| PRD (this document) | Design (separate document) |
|---------------------|---------------------------|
| User stories per persona | CRD fields, conditions, finalizers |
| Observable outcomes | Controller reconcile logic |
| What users can do and see | Playbook names, API schemas |
| Scope boundaries | Helm/installer implementation |
| Unverified assumptions | SLA numbers, timing guarantees |
| External dependencies | Retry strategies, backoff logic |
| | Cleanup mechanics (disk wipe, etc.) |
| | Internal status conditions |
| | Synchronization intervals |

**Litmus test:** could a persona observe or experience this directly?
If yes → PRD. If no → design.

**Swap test:** would this statement change if the implementation changed?
If yes → design. If no → PRD.

## Common Reviewer Feedback (From Actual PRD Reviews)

| Anti-Pattern | Reviewer Reaction | Better Approach |
|-------------|-------------------|-----------------|
| 120 lines for a simple feature | "Maybe 12 lines? Shorter is better." | Match length to complexity |
| In Scope restates user stories | "Don't re-state user stories. Describe at a higher level." | Add boundary info only |
| SLA numbers not from Jira (60s, 10m) | "I don't think this is realistic" | Omit unless Jira specifies |
| Extra sections (Risks, AC, Milestones) | "Do we track milestones in PRDs? — No." | Follow template exactly |
| "Primary IP address" | "What is a 'primary' IP address?" | Use precise platform terms |
| Internal conditions in Assumptions | "These are design-level interface contracts" | Move to design document |
| Cleanup mechanics in scope | "The details of cleanup are handled by BMaaS and should not be detailed here" | State outcome: "hosts are cleaned up" |
| User story about platform invariant | "This isn't exposed to users and therefore isn't a user story" | Only write stories about user actions |
| Reversed dependency direction | "I would reverse this. This proposal should not depend on CaaS." | Feature enables consumers, not depends on them |
| Design details in In Scope | "Design details don't belong in the PRD" | State user-observable capability only |
