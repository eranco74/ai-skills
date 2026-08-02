# PRD Review — Calibration Examples

Worked scoring examples for each criterion in [SKILL.md](../SKILL.md).
Read the section for the criterion currently being scored.

## 1. WHAT — Clear user-facing need?

- W=0: "Ship example YAML files and a README in the repo so admins can load them with `osac create -f`." — the API and CLI already exist; the deliverable is content (example files + docs), not a product capability. This is a Jira task, not an enhancement.
- W=0: "Implement CSI driver installation via AAP playbook on ClusterOrder Ready event" — describes a system action, not a user need. No persona mentioned.
- W=0: A PRD states "Cloud Infrastructure Admin and Cloud Provider Admin personas are affected" in the problem statement and references personas in functional requirements, but has no User Stories section and no `As a <persona>...` stories. Personas are named but the PRD never describes what each persona can do — the reviewer cannot evaluate completeness.
- W=1: "Storage should be available on CaaS clusters" — right direction but vague. Which clusters? What does "available" mean to the user? How would a tenant know? No personas identified.
- W=1: "Tenant users can create and manage secrets" — right direction but generic. What secrets? SSH keypairs? OIDC client secrets? Cluster kubeconfigs? Cloud-init credentials? Without explicit use cases, reviewers can't evaluate whether the scope is right.
- W=2: "When a CaaS cluster is provisioned and ready, tenants can create persistent volumes using StorageClasses without manual configuration. Tenants can see whether storage is ready on their cluster. Cloud Provider Admins can see storage readiness across all tenant clusters." — clear, observable, specific, personas identified.
- W=2: "Tenant users can retrieve cluster kubeconfig and admin password via the secrets API. Tenant admins can store OIDC client secrets for IDP integration. Tenant users can store cloud-init credentials containing passwords for VM provisioning." — names the concrete artifacts and scenarios, not just the generic capability.
- W=2: A single `### Tenant Admin / Tenant User` heading with "As a Tenant Admin or Tenant User, I want persistent storage to be available on my CaaS cluster when it is ready, so that I can run stateful workloads without waiting for manual configuration." — one story, two personas, because the capability is identical for both. Full coverage; do not dock for "missing" separate Tenant Admin and Tenant User headings.
- W=1: A `### Tenant Admin / Tenant User` heading with "As a Tenant Admin or Tenant User, I want to view resource quota usage" — but Tenant Admins actually need org-wide quota visibility across all Tenant Users, while Tenant Users only need their own usage. The heading labels this a consolidation, but the two personas' real needs differ. Treat the Tenant Admin persona as uncovered — the shared heading doesn't describe what a Tenant Admin can actually do.

## 2. WHY — Business justification?

- Y=0: "Add storage support for CaaS clusters" with no explanation of why this matters or what happens without it.
- Y=0: A feature listing 11 Definition of Done bullets and 10 user stories but zero explanation of why this capability matters, who is asking for it, or what happens without it.
- Y=1: "Tenants cannot run stateful workloads on CaaS clusters without manual storage configuration." — describes the gap but no impact.
- Y=2: "CaaS clusters are provisioned without persistent storage. Tenants cannot run stateful workloads until someone manually configures storage, and there is no visibility into whether storage is available. This blocks CaaS adoption for any tenant with stateful workloads." — names the pain, describes the consequence, ties to adoption.
- Y=2: "Multi-tenant GPU clusters require InfiniBand tenant isolation to prevent cross-tenant traffic interference. Without isolation, tenants sharing a fabric can observe each other's RDMA traffic, which is a security and compliance blocker for sovereign AI deployments." — specific pain, concrete consequence, ties to strategic goal.

## 3. User-Facing Focus — Free from design leakage?

- UF=0: "When a ClusterOrder reaches phase=Ready and the owning Tenant has StorageBackendReady=True, the storage controller invokes osac-create-tenant-cluster-storage with provisioning_target=hcp_data_plane." — names controllers, internal conditions, playbook parameters.
- UF=0: "The storage controller places a finalizer on each ClusterOrder where storage was set up. On deletion, it triggers osac-delete-tenant-cluster-storage to remove StorageClasses, VolumeSnapshotClasses, and CSI Secret from the CaaS cluster." — describes finalizer behavior and cleanup implementation.
- UF=1: "Storage is automatically provisioned on CaaS clusters when they become ready. The controller uses AAP to install the CSI driver." — good user outcome, but "the controller uses AAP" is an implementation detail.
- UF=2: "When a CaaS cluster is provisioned and ready, persistent storage is automatically available on the cluster without manual configuration." — pure user outcome.
- UF=2: "Tenants can see storage readiness on their ClusterOrder status." — ClusterOrder is user-facing platform vocabulary, readiness is observable.
- UF=2: "Tenants specify port mappings in the format `8080:80` (host:container) when creating a ComputeInstance." — a single, minimal illustrative example of a value the user types; it conveys the user-facing format without describing how the system implements it. Do not dock a PRD for including one example like this.
- UF=0: "The reconciler records the parsed mapping in the ComputeInstance status as `conditions: [{type: PortMappingApplied, hostPort: 8080, containerPort: 80}]`." — reads like a design doc even though it's framed as "an example": the condition type and internal field names are only visible in code, not to the user. An example is not automatically exempt from design leakage — apply the same smell tests to it as to any other statement.

## 4. Right-Sized — Focused and economical scope?

- R=0: "Add storage support, networking policy enforcement, and cluster monitoring for CaaS." — three independent capabilities for different concerns.
- R=0: "East-west connectivity: Ethernet fabric provisioning, InfiniBand tenant isolation, NVLink partition management, VPC peering, and cross-fabric validation." — five independent capabilities that each serve different fabric types and could ship independently. This should be split into individual features per fabric type.
- R=1: "Add CaaS cluster storage and add tenant storage quota management." — storage provisioning and quota management serve different workflows (day-1 vs day-2) and could ship independently.
- R=0: A PRD for one narrow capability (e.g., exposing one existing inventory field through the API) padded with a `Terminology` section defining platform terms already in `osac-dimensions.md`, a standalone `Acceptance Criteria` section duplicating User Stories content, a `Risks` section, and a `Milestone Scoping` section — none of which exist in `prd_template.md` — such that the actual one-capability scope is buried under four non-template sections a reader must cut through to find it.
- R=1: A PRD covering one coherent capability (e.g., exposing one existing inventory field through the API) but restating the same story two or three times across near-identical Acceptance Criteria bullets, defining terms already covered by `osac-dimensions.md`, and stating numeric SLAs with no traceable source (a pattern that appeared in `enhancement-proposals#169`) — the underlying scope is fine, but the document is padded well past what that scope needs.
- R=2: "CaaS cluster storage: automatic provisioning, readiness visibility, and cleanup on deletion." — provisioning without visibility is incomplete; cleanup without provisioning is meaningless. Tightly coupled.
- R=2: `OSAC-1332-caas-cluster-storage` (47 lines) — one coherent capability, each section states its content once, no restatement across sections.

## 5. Testability — Verifiable requirements?

- T=0: "The controller reconciles within 30 seconds" and "The finalizer is removed after cleanup completes" — not observable by users.
- T=1: "Tenants can create PVCs on CaaS clusters" (testable) mixed with "The AAP job succeeds and StorageClasses are confirmed" (internal).
- T=2: "A tenant can create a PVC using a StorageClass on their CaaS cluster within 5 minutes of the cluster becoming ready." — observable, measurable, testable.
