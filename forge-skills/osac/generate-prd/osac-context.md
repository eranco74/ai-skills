# OSAC Context for PRD Generation

## What is OSAC?

OSAC (Open Sovereign AI Cloud) is a fulfillment system for provisioning
Kubernetes clusters and compute instances with networking capabilities.

## Architecture

```
fulfillment-service    gRPC/REST API server, PostgreSQL
osac-operator          Kubernetes operator, provisions via AAP + HCP
osac-aap               Ansible playbooks for VM and network provisioning
osac-installer         Kustomize overlays, deploys all components
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

## PRD vs Design: What Belongs Where

| PRD (this document) | Design (separate document) |
|---------------------|---------------------------|
| User stories per persona | CRD fields, conditions, finalizers |
| Observable outcomes | Controller reconcile logic |
| Non-goals, assumptions, risks | Playbook names, API schemas |
| High-level affected surfaces | Helm/installer implementation |

**Litmus test:** could a persona observe or experience this directly?
If yes → PRD. If no → design.

## Common Reviewer Feedback

| Anti-Pattern | Better Approach |
|-------------|-----------------|
| Vague non-goals ("advanced features") | Specific: "Auto-scaling deferred to OSAC-XXXX" |
| Implementation user stories ("I want the CRD to have a CIDR field") | "I want to define an isolated network with my own IP space" |
| Generic risks ("might have bugs") | "IPv6 dual-stack adds testing complexity — mitigate with IPv4-only mode" |
| AC that repeats requirements | End-to-end scenarios a PM can verify by using the product |
