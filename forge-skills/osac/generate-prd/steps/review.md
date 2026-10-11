# Phase 4: Self-Review

**IMPORTANT: Do NOT output any review text, scores, or reasoning. Perform
this review silently — evaluate each criterion internally, note what needs
fixing, then proceed directly to Phase 5 (Revise) or Phase 6 (Output).
Your text output must contain ONLY the final PRD, never review commentary.**

Score your PRD draft against the 5-criterion rubric below. Be strict — first
drafts rarely merit 10/10. The average merged PRD scores 8-9/10 after human
review rounds.

## Scoring Process

For each criterion, evaluate internally and decide the score. Do NOT write
the scores or reasoning as text output.

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
   Statement, In Scope, Out of Scope, User Stories, Assumptions,
   Dependencies. Keep all six headings, allowing empty optional bodies.
   No other `## ` headings allowed (no Risks,
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

5. **Persona ownership check:** For each persona marked "Not affected," verify
   the feature does not automate or replace a process they currently perform.
   If it does, they need user stories — mark this as a review failure.

6. **Persona-story alignment check:** For each user story, verify the
   capability matches the persona's role definition. Infrastructure operations
   under Cloud Provider Admin, or tenant management under Cloud Infrastructure
   Admin, is a misattribution.

7. **Problem Statement solution check:** The Problem Statement must not contain
   sentences describing what the feature introduces or how it works. Search for
   "introduces", "eliminates", "provides", "enables" used to describe the
   feature itself (not the user pain). Any match is a failure.

8. **Async status check:** Scan the draft for async triggers such as
   provisioning, deployment, ComputeInstance, ClusterOrder, BareMetalInstance,
   storage volumes, CSI driver, GPU passthrough, "automatically available",
   "on-demand", or "when ready". For each trigger, check the Jira extraction
   and durable record. If Jira or an applicable explicit owner decision
   authorizes user-visible status/progress/failure details, verify that In
   Scope and User Stories represent that requirement. If no approved source
   authorizes it, do not fail for omission; instead verify the draft does not
   imply that status capability. When the need is material and unresolved,
   require a neutral Assumptions question rather than inferred scope.

9. **Approved-source completeness check:** Re-read the Jira input and the
   durable scoped evidence record. Verify every explicit Jira requirement and
   every relevant, verified requirement from an applicable explicit owner
   decision is represented in the PRD where applicable. If Jira or an owner decision
   marks something out of scope or deferred, verify it is not accidentally
   presented as In Scope. List missing or misclassified items. Proposed,
   superseded, unknown, and unverified claims do not create requirements. A
   claim state alone is not scope authority; implemented claims describe current
   behavior, not a new requirement.

10. **Scope authority check:** Every In Scope bullet must trace to Jira or an
    applicable explicit owner decision in the durable record with verified
    source references. Every Out of Scope bullet must trace to an explicit Jira
    exclusion or a verified owner decision excluding it. A claim's state alone
    does not authorize scope; implemented claims describe current behavior.
    Remove unsupported scope. Keep unresolved conflicts in the record and,
    when they affect the boundary, state them neutrally under Assumptions; do
    not choose a side without an accepted decision.

11. **Persona separation check:** Verify that Tenant Admin and Tenant User
    have SEPARATE headings in User Stories unless they have genuinely
    identical capabilities in this feature. Same for Cloud Provider Admin
    and Cloud Infrastructure Admin. If any two personas are combined under
    one heading, verify that neither has ANY unique capability — if one
    does, split them into separate headings.

12. **Evidence freshness check:** Reuse the record created for this `prd` run;
    do not repeat broad research during review or revision. Verify cited source
    URLs, dates, and revisions using the organizational-research contract.
    If a source cannot be checked, treat its claim as unverified and do not
    present it as settled. In `live` mode, make at most one targeted follow-up
    only when a material gap or conflict blocks review; update the same run's
    record and cited brief according to the contract. In `off` or `replay`, do
    not make live calls. If material questions remain because evidence was
    unavailable or unverified, keep them visible under Assumptions and mark the
    draft incomplete for downstream design; an absent decision is not a
    confirmed absence of a decision.

13. **Research citation traceability:** Compare every material factual or
    rationale statement derived from organizational research with the `claims`
    in this run's record. Put `[Chai:CLAIM_ID]` inline beside each such
    statement and include a nearby link to the verified original source.
    Verify the claim ID exists, its wording and decision state
    support the statement, and every referenced source is `verified` with its
    URL, date, and revision present in the record and cited brief.
    If a source is missing, unverified, or does not support the statement,
    remove the factual assertion or mark the unresolved point neutrally under
    Assumptions. A Chai citation does not authorize scope. Missing markers or
    original-source links fail review.

14. **Requirement-ID coverage:** Compare every explicit requirement ID in the
    durable record and Jira extraction against the cited-brief coverage table.
    Each ID must be marked `covered`, `unresolved`, or `omitted`, with its PRD
    section and user-facing statement or open question. Translate technical
    criteria into user-facing outcomes where possible and preserve remaining
    tests, resource-audit, default-resolution, or other verification duties in
    the sidecar/handoff. Never drop an explicit requirement to meet length or
    style. Any material omission fails readiness; an unresolved owner decision
    remains a question and must not become an affirmative story.

15. **Diagnostic authorization:** For every story exposing diagnostic
    payloads, verify the audience is authorized by an explicit approved
    requirement or independently checked existing access control. Tenant
    visibility or persona naming alone does not authorize payload access. If
    authorization is unresolved, keep it as a question and do not describe the
    audience as entitled to the data.

16. **Persist coverage and final document:** Write `{KEY}-coverage.json` beside
    the research record using the organizational contract's machine-readable
    schema. Include every requirement ID, its covered/unresolved/omitted status,
    and the actual draft passage or question. Re-read it after revision. Save
    the final document to `document_output_path`; a filesystem-only runner uses
    `/home/user/prd.md` when the caller supplies no path. Sidecars and final
    document are distinct artifacts.

## Verdict

If all checks pass → proceed to Phase 6 (Output).
If any check fails → proceed to Phase 5 (Revise). Note which criteria scored
low and which deterministic checks failed.
An unresolved material conflict means the PRD is incomplete for downstream
design even if the other checks pass; keep it unresolved in the record and
visible under Assumptions.
