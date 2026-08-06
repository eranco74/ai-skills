# Phase 3: Self-Review

Score your PRD draft against the 5-criterion rubric below. Be strict — first
drafts rarely merit 10/10. The average merged PRD scores 8-9/10 after human
review rounds.

## Scoring Process

For each criterion, state your reasoning FIRST, then assign the score.

### 1. WHAT — Clear user-facing need? (0-2)

Check:
- Does the PRD describe a new product capability (not just content/docs)?
- Are OSAC services identified (BMaaS, CaaS, VMaaS, MaaS, Enclave)?
- Are affected personas identified with per-persona user stories?
- Each affected persona must have at least one `As a <persona>...` story.
  Mentioning a persona in prose without a story does not count.

Score:
- **0** = Vague, system internals, no personas, or no per-persona user stories
- **1** = Partially clear but mixed with implementation or missing personas
- **2** = Clear, specific, user-observable. Each affected persona has stories.

Calibration:
- W=0: "Implement CSI driver installation via AAP playbook" — system action, no user need
- W=1: "Tenants can manage secrets" — right direction but generic, no use cases
- W=2: "Tenant users can retrieve cluster kubeconfig and admin password via
  the secrets API. Tenant admins can store OIDC client secrets for IDP
  integration." — names concrete artifacts

### 2. WHY — Business justification? (0-2)

Check:
- Is there a clear problem statement with user pain?
- Is the cost of inaction described?
- Is there concrete evidence (not just "users need this")?

Score:
- **0** = No justification or circular reasoning
- **1** = Generic justification, plausible but no evidence
- **2** = Concrete justification with pain, impact, or strategic tie

Calibration:
- Y=1: "Tenants cannot run stateful workloads without manual storage
  configuration." — gap described but no impact
- Y=2: "Tenants cannot run stateful workloads until someone manually
  configures storage, and there is no visibility into whether storage is
  available. This blocks CaaS adoption." — pain + consequence + tie

### 3. User-Facing Focus — Free from design leakage? (0-2)

Check:
- Does the PRD name controllers, reconcilers, finalizers, playbooks?
- Does it describe internal conditions or reconciliation logic?
- Does it specify CRD field names, SLA numbers not from Jira, or cleanup
  mechanics?
- Platform vocabulary (ClusterOrder, ComputeInstance, etc.) is acceptable.

Smell tests:
- Could a PM verify this by using the product?
- Would this change if the implementation changed?
- Does this name something only visible in code?

Score:
- **0** = Reads like a design document
- **1** = Mostly user-focused but some design leakage
- **2** = Only user-observable outcomes

Calibration:
- UF=0: "The storage controller places a finalizer on each ClusterOrder.
  On deletion, it triggers osac-delete-tenant-cluster-storage." — finalizers,
  controller names, playbook names
- UF=1: "Storage is automatically provisioned on CaaS clusters. The
  controller uses AAP to install the CSI driver." — good outcome, but
  "controller uses AAP" is implementation
- UF=2: "When a CaaS cluster is provisioned and ready, persistent storage
  is automatically available without manual configuration." — pure outcome

### 4. Right-Sized — Focused scope? (0-2)

Check:
- How many independent capabilities are described?
- Could each ship on its own and provide value?
- Capabilities that require each other are one feature.

Score:
- **0** = Bundles 3+ independent capabilities
- **1** = Bundles 1-2 separable capabilities
- **2** = Focused — capabilities require each other

### 5. Testability — Verifiable requirements? (0-2)

Check:
- Can each user story be verified by a PM using the product?
- Are there vague terms ("appropriate", "efficient") without specifics?
- Are there requirements describing system internals?

Score:
- **0** = Requirements describe activities or internals
- **1** = Some testable, some vague or internal
- **2** = Every requirement PM-verifiable

## Pass/Fail

- **PASS**: Total >= 7/10 AND no zeros on any criterion
- **FAIL**: Total < 7 OR any zero (automatic fail regardless of total)

## Inline Deterministic Checks

Also verify these concrete checks against your draft:

1. **Section check:** Count `## ` headings. Must have exactly: Problem
   Statement, In Scope, Out of Scope, User Stories, Assumptions (optional),
   Dependencies (optional). No other `## ` headings allowed (no Risks,
   Acceptance Criteria, Terminology, Milestone Scoping).

2. **Persona check:** All four names must appear in the User Stories section:
   Cloud Provider Admin, Cloud Infrastructure Admin, Tenant Admin, Tenant User
   (each with a story or "Not affected" note).

3. **Leakage check:** Search for these terms (case-insensitive). Any match
   is a failure:
   - reconciler, reconciliation, finalizer, playbook, env var, AAP job,
     CRD field, osac-operator, osac-aap, ansible role
   - "controller" (unless in "Hosted Control Planes")

4. **Length check:** Count non-blank lines. Must be 15-120. Target is 40-80.

## Verdict

If all checks pass → proceed to Phase 5 (Output).
If any check fails → proceed to Phase 4 (Revise). Note which criteria scored
low and which deterministic checks failed.
