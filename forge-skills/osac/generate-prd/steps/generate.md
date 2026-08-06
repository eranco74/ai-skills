# Phase 2: Generate PRD

## Step 1: Analyze the Feature

Before writing, determine:

- **Which OSAC services** are affected (BMaaS, CaaS, VMaaS, MaaS, Enclave)?
- **Which personas** are affected? If two have identical capabilities, combine
  them (e.g., `### Tenant Admin / Tenant User`).
- **What is the user pain?** State it from the user's perspective.
- **What is the scope boundary?** What's in, what's explicitly out?
- **What are the dependencies?** Other features that must land first.
- **Dependency direction:** Does this feature enable something downstream, or
  depend on something upstream? A feature that exposes data does NOT depend
  on the downstream consumer — the consumer depends on it.

## Step 2: Write the PRD

Follow the template structure. Use the section guidance from
`context/section-guidance.md` for detailed per-section instructions.

### Problem Statement
- Lead with user pain, not the system gap.
- 2-4 sentences. If the problem is clear in 2, stop there.
- State the cost of inaction.

### In Scope
- Bullet list of user-observable capabilities.
- Do NOT restate user stories. In Scope adds boundary information that stories
  alone wouldn't convey ("works for both new and existing clusters" is a
  boundary; "tenants can create volumes" duplicates a story).
- If there is nothing beyond what user stories convey, keep to 2-4 bullets.
- Describe at a high level — not detailed requirements.

### Out of Scope
- **Optional.** Only include what a reader would plausibly assume is included.
- Each item must pass the **boundary proximity test**: would a reviewer ask
  "is this included?" If not, the item is too distant.

### User Stories
- One story per distinct user goal. If a story has "and", split it.
- Ground in concrete artifacts and scenarios — name what users interact with.
- Do NOT write stories about platform behavior. "I want tenant isolation to
  be enforced" is not a user story — it's a platform invariant. "I want to
  view only my tenant's instances" is a user story.

### Assumptions
- Optional. Omit if no unverified assumptions exist.
- Do NOT put API contracts, interface specs, or design details here.

### Dependencies
- Optional. Omit if no external dependencies exist.
- Get the direction right. Name specific capabilities, not just Jira keys.

## Design Leakage — Apply These Tests to Every Statement

Reviewers reject PRDs that contain implementation details. Apply these smell
tests:

- **PM test:** Could a Product Manager verify this by using the product?
  If no → design leakage.
- **Swap test:** Would this statement change if the implementation changed?
  If yes → it's design.
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

### Platform Vocabulary (Acceptable — NOT Design Leakage)

- OpenShift, Hosted Control Planes
- ClusterOrder, ComputeInstance, BareMetalInstance, Tenant
- VirtualNetwork, Subnet, SecurityGroup, PublicIP, StorageClass
- Keycloak, OPA, kubectl, Helm
- BMaaS, CaaS, VMaaS, MaaS, Enclave

## OSAC Personas

| Persona | Role |
|---------|------|
| **Cloud Provider Admin** | Tenant onboarding, quotas, global catalogs, super-user |
| **Cloud Infrastructure Admin** | Core infrastructure, network/storage integrations |
| **Tenant Admin** | Org config, users, IDP, org-scoped catalogs |
| **Tenant User** | Self-service provisioning, lifecycle management |

Each affected persona gets a `### {Persona}` heading with at least one user
story. Unaffected personas get "Not affected by this feature." in one line.

## Size Calibration

Match output depth to feature complexity. When in doubt, write less.

- **Simple feature** (1-2 capabilities): 15-40 lines
- **Medium feature** (3-5 capabilities): 40-70 lines
- **Complex feature** (5+ capabilities): 70-100 lines

One reviewer said of a 120-line PRD for a simple feature: "This doesn't need
to be 120 lines. Maybe 12? Shorter is better."

Consolidation rules:
- One user story per distinct user goal. Consolidate identical persona stories.
- Skip dimensions that don't apply — no "N/A" lines.
- Do not repeat information across sections.

## Patterns from Top-Scoring PRDs

**What 10/10 PRDs do:**
- Problem statement leads with user pain AND strategic motivation (security,
  compliance, adoption blocker — not just operational convenience)
- In Scope covers EVERY capability from the Jira Definition of Done — no omissions
- In Scope includes failure behavior (what happens when things go wrong)
- In Scope mentions tenant isolation for new resources
- Out of Scope contains items at the feature boundary — closely related but
  deferred. NOT distant, unrelated capabilities nobody would expect.
- When two personas have identical capabilities, they are combined under one
  heading (e.g., "### Tenant Admin / Tenant User") with a note explaining they
  share the same scope. **Combined persona test:** "Does the Tenant Admin have
  any capability in this feature that the Tenant User does not?" If no, combine.
- Out of Scope items pass the **boundary proximity test**: "Would a reviewer
  plausibly ask 'is this included?'" If not, the item is too distant.
- User stories cover 3-4 personas with concrete scenarios
- Dependencies name specific capabilities needed, not just Jira keys
- Assumptions are specific and verifiable
- Language is precise — no "appropriate", "efficient", "standard" without specifics

**What 5/10 PRDs get wrong:**
- Claim "all resources" but omit some
- Mix implementation details with requirements
- User stories are generic ("manage X") instead of specific ("create X with Y")
- Contradictory scope statements
- List completed work as in-scope

## What NOT to Do

- Do NOT ask clarifying questions — generate the best PRD from available info
- Do NOT add FR-N/NFR-N requirement IDs — OSAC uses user stories, not numbered FRs
- Do NOT add Risks, Acceptance Criteria, or Open Questions sections
- Do NOT prescribe implementation — "the controller uses AAP" is design leakage
- Do NOT use vague language — "handle edge cases appropriately" → name the edge cases
- Do NOT repeat the same information in Problem Statement and In Scope

## Source Traceability

Add `[Jira: {KEY}]` markers only when a requirement comes from a non-obvious
source (linked issue, comment). Add `[Assumption]` for requirements not directly
stated in the Jira source. Most statements trace to the primary feature — don't
tag every one.
