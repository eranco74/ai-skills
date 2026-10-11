# Phase 3: Generate PRD

## Step 1: Analyze the Feature

Before writing, determine:

- **Which OSAC services** are affected (BMaaS, CaaS, VMaaS, MaaS, Enclave)?
- **Which personas** are affected? Default to giving EACH persona its own
  heading. Only combine two personas under one heading (e.g.,
  `### Tenant Admin / Tenant User`) when they have genuinely identical
  capabilities AND neither has any unique story. When in doubt, keep them
  separate — the gold standard almost always separates them.
- **Persona ownership test:** Before marking any persona "Not affected," ask:
  does this persona currently perform the manual process this feature automates
  or replaces? If yes, they are a primary affected persona — write stories
  about what changes for them. Example: if a feature replaces a static pool
  maintained by Cloud Infrastructure Admins, CIA is a primary persona even if
  the feature is "CaaS" scoped.
- **Diagnostic audience authorization:** Do not infer diagnostic payload
  access from a persona's ability to view or manage tenants. Qualify each
  diagnostic story using an explicit approved requirement or independently
  verified existing access control. If authorization is unknown, leave it as
  an actionable question in Assumptions and the evidence record; do not imply
  access is allowed.
- **What is the user pain?** State it from the user's perspective.
- **What is the scope boundary?** What's in, what's explicitly out?
- **Lifecycle decomposition:** For any resource, pool, or capacity being
  introduced, enumerate all lifecycle operations a user can perform: create,
  list/view, update/configure, scale up, scale down, delete. Each operation
  explicitly required by Jira or an applicable explicit owner decision needs
  an In Scope bullet. Treat lifecycle operations as candidates to check, not
  implicit requirements; on-demand creation does not by itself add scale or
  status scope.
- **Async status visibility (source-gated check):** For resources created,
  provisioned, deployed, or modified asynchronously, check whether Jira or an
  applicable explicit owner decision requires user-visible status, progress,
  or failure details. Resources worth checking include ComputeInstance,
  ClusterOrder, BareMetalInstance, storage volumes, CSI driver deployment, and
  GPU passthrough setup. Add a status capability and user story only when that
  approved source authorizes it. If the need is material but approved sources
  are silent, record an actionable question and state it neutrally under
  Assumptions; do not infer scope from the async operation alone.
- **What are the dependencies?** Other features that must land first.
- **Dependency direction:** Does this feature enable something downstream, or
  depend on something upstream? A feature that exposes data does NOT depend
  on the downstream consumer — the consumer depends on it.

## Step 1.5: Extract Requirements and Build the Scoped Evidence Record (MANDATORY)

**Complete this step before drafting any PRD content. If you skip it, the PRD
will fail review.** The temporary Jira extraction remains mandatory; the
durable evidence record adds organizational findings without changing the
PRD's six-section template.

### 1.5a Extract Jira scope

Re-read the Jira Feature description line by line. Write `/tmp/scope-contract.md`
with exactly these three sections:

```
## In Scope (from Jira)
- [quote or paraphrase each capability the Jira explicitly requests]

## Out of Scope (from Jira)
- [quote anything the Jira explicitly defers or excludes]

## Not Mentioned
- Jira omissions only. Silence in Jira is not an exclusion, but it does not
  authorize scope.
```

Rules for the extraction:
- Use the Jira's own words. Do not rephrase, expand, or infer.
- Acceptance criteria items → In Scope
- Demo steps → In Scope (the capability they demonstrate)
- "Future work", "separate ticket", "out of scope" in Jira → Out of Scope
- If the Jira does not mention something, it goes in "Not Mentioned"
- Keep Jira omissions in this section even when separately evaluating an
  applicable explicit owner decision; capture that decision in the durable
  record, not as Jira scope.

### 1.5b Research and persist the evidence record

Read `skills/osac/generate-prd/context/organizational-research.md` and follow
its schema and tool instructions. Use caller-provided per-run context values
when present: `research_mode`, `run_id`, `replay_record_path`,
`research_record_path` (the output JSON path), and `artifact_workspace` (an
output directory). These are contextual inputs, not assumed Forge CLI flags or
a Forge-specific configuration interface. If `research_mode` is absent, use
`live`; if that mode is selected and `ask_persona` is not exposed, record
`unavailable` and continue. `replay` reads the supplied, validated record at
`replay_record_path` and makes no live call. A missing or invalid replay input
is a setup error: stop before drafting, report the error, and do not create a
completion record or switch to live. A valid frozen fixture may itself record
an unavailable retrieval outcome; preserve that outcome when replaying it.
`off` skips Chai but still records Jira requirements. In `live`, if a material
question remains, make one bounded feature-specific request and at most one
targeted follow-up for a material missing source, status, or conflict. Do not
perform broad team-history searches or use Chai's lesson/feedback tools.

Create a distinct record for this issue, run, and `prd` stage. Use the supplied
`run_id` when present; otherwise use a fresh UUID for this run (do not reuse a
previous run's identifier). Save the current-run JSON to the supplied
`research_record_path` when present; otherwise use the supplied
`artifact_workspace` and name the file `{KEY}-research.json`; otherwise use
`.artifacts/research/{run_id}/{KEY}/prd/{KEY}-research.json`. Save
`{KEY}-research-brief.md` and `{KEY}-research-raw.md` beside that JSON. A
supplied `research-input.json` or `replay_record_path` is input only, never the
current run's completion artifact. Never overwrite a replay input or a record
belonging to another run. If the requested output path equals the replay input,
use a distinct artifact-workspace or fallback path.
For replay, read from `replay_record_path`, validate the supplied record against
the current issue and stage, preserve its origin in the raw/provenance sidecar,
and do not modify the supplied input. Save the current run's record at the
current run path, keeping the replay source path and originating run in the
sidecar. Record the Jira requirements from
`/tmp/scope-contract.md`, cited claims with their source URLs, dates and
revisions, the decision state (`accepted`, `proposed`, `implemented`,
`superseded`, or `unknown`), and unresolved conflicts. Render the cited brief
beside the JSON record as described by the contract. In the raw sidecar, retain
the exact question sent, complete raw `ask_persona` result, call duration, and
status for each live call; for an unavailable tool or timeout, retain the
attempted question and status even when there is no result. In replay or off
mode, record the input path or skipped status without inventing a live response.
Keep explicit Jira requirements separate from applicable explicit owner
decisions, research claims, and assumptions. For a requirement authorized by
an owner decision, name the owner and decision, link its verified source, and
explain applicability in the provenance sidecar.

**Completion gate — required before Step 2 drafting:** Use `write_file` to save
the current-run JSON and cited brief in the selected output location in every
mode, including `replay`, `off`, `unavailable`, and `timeout`. Do not treat a
readable input record as proof these outputs were saved. Reread both saved files
with `read_file` and verify required fields and types, `schema_version: 1`, all
allowed enums, unique IDs, and that every referenced source ID exists. Verify
the record identity exactly matches this run's Jira key, `stage: prd`, `run_id`,
and `research_mode`; verify its status reflects the actual result. Check that
the brief agrees with the record, includes source URLs, dates, and revisions,
and presents factual claims only when every supporting source is verified. If
any artifact is missing or fails validation, stop without drafting and report
only the failed artifact path and validation issue.

If Chai is not configured or the call fails, mark the record `unavailable` or
`timeout` as applicable, preserve the Jira requirements, and continue without
claiming that research succeeded. In `off`, mark it `skipped`. State material
remaining questions neutrally under Assumptions. Retrieval failure does not
mean the organization has no decision. Do not make up source URLs, dates,
revisions, accepted decisions, or requirements. A proposed, superseded, unknown,
or unverified claim is not an approved requirement.

Compare Jira scope with organizational evidence. Do not silently resolve a
contradiction by choosing the newest or most frequent statement. Keep each
material unresolved contradiction in the record as an unresolved conflict. If
it affects the PRD boundary, state it neutrally under the existing Assumptions
section as `[Open conflict: ...]`; do not add a new section or present either
side as settled. If material questions remain because evidence could not be
retrieved or checked, state them under Assumptions and make clear that the draft
is incomplete for downstream design until resolved.

After adding extracted Jira requirements, questions, and conflicts, update the
current-run JSON and brief, then reread and recheck their identity and
references. Do not draft until this final completion check passes.

### Scope authority for Step 2

Every PRD In Scope item must trace to either the Jira `In Scope (from Jira)`
list or an applicable explicit owner decision captured as a requirement in the
durable record with verified source references. Every Out of Scope item must
trace to the Jira `Out of Scope (from Jira)` list or an explicit, verified
owner decision excluding it. A claim's `accepted`/`implemented` state alone
does not grant scope authority; an implemented claim describes existing
  behavior, not a new requirement. Jira silence, Chai suggestions, and
  unrelated architecture context cannot add scope. An item absent from Jira
  may be included only when a separate applicable explicit owner decision is
  recorded as a requirement with verified source references; identify the
  decision and its applicability in the provenance sidecar. Do not treat an
  accepted claim state alone as an owner decision. Use `[Chai:CLAIM_ID]` beside
  each material research-backed statement, with a nearby link to its verified
  original source; the durable record and cited brief also carry the URL, date,
  and revision. Chai may
  support user-facing problem context, but PRD prose must not expose
  implementation details or turn architecture rationale into a product
  requirement.

### Requirement coverage sidecar

After the first draft and after every revision, update the cited brief with a
coverage table containing one row for every explicit requirement ID in the
durable record. Mark each row `covered`, `unresolved`, or `omitted`, and give
the exact PRD section and user-facing statement or the open question. Translate
technical Jira criteria (including tests, resource audits, and default
resolution behavior) into user-facing outcomes where possible; preserve any
remaining verification obligation in the sidecar and handoff. Do not omit a
requirement to satisfy length, style, or design-leakage rules. A material
omission blocks readiness; an unresolved owner decision remains a question,
not an affirmative story. Reread the updated brief and verify every requirement
ID is represented before the final review gate.

## Step 2: Write the PRD

Follow the template structure. Use the section guidance from
`context/section-guidance.md` for detailed per-section instructions.

### Problem Statement
- Lead with user pain, not the system gap.
- 2-4 sentences. If the problem is clear in 2, stop there.
- State the cost of inaction.
- **Pain only — no solutions.** The Problem Statement describes what's broken
  and why it matters. Do NOT describe what the feature introduces, how it
  works, or what the solution model is — that belongs in In Scope. A sentence
  starting with "This feature introduces..." or "The X eliminates..." is a
  solution description, not a problem statement.

### In Scope
- Bullet list of user-observable capabilities.
- **Controlled scope.** Every In Scope item must trace to explicit Jira scope
  or an applicable explicit owner decision allowed by the evidence record. A
  claim status alone does not authorize scope. Do NOT add capabilities merely
  because they seem logical or appear in proposed, unknown, superseded, or
  unrelated research. If the
  Jira says "CRUD for X", scope is CRUD for X, not CRUD plus monitoring plus
  migration plus integration with Y.
- Do NOT restate user stories. In Scope adds boundary information that stories
  alone wouldn't convey ("works for both new and existing clusters" is a
  boundary; "tenants can create volumes" duplicates a story).
- If there is nothing beyond what user stories convey, keep to 2-4 bullets.
- Describe at a high level — not detailed requirements.
- **Status visibility:** For every resource or operation that is created or
  modified asynchronously, check whether Jira or an applicable explicit owner
  decision requires status tracking. If so, ensure the authorized requirement
  and corresponding user story make current state and any required failure
  reasons visible. Async behavior alone does not imply status scope. If this is
  a material unresolved need, record a question under Assumptions without
  asserting a capability.
- **Billing, metering, and cost management:** Check approved sources for
  explicit requirements or exclusions. Do not infer that billing is Out of
  Scope because it is a platform-wide concern or because another topic is the
  feature's primary purpose. If sources are silent and the boundary is
  material, record an actionable question under Assumptions instead of
  asserting inclusion or exclusion.

### Out of Scope
- **Optional.** Only include what a reader would plausibly assume is included.
- Each item must pass the **boundary proximity test**: would a reviewer ask
  "is this included?" If not, the item is too distant.
- **Match approved sources.** If Jira or an applicable explicit owner decision
  excludes or defers something, include it here when it is near
  the feature boundary. If Jira mentions a related capability handled by a
  different ticket, that is an Out of Scope item with the responsible ticket
  noted.
- **Do NOT invert scope or silently resolve a conflict.** Preserve explicit Jira
  requirements and exclusions. Apply a separately recorded owner decision only
  when its authority and applicability are verified. If Jira and an owner
  decision conflict and the decision does not explicitly resolve that conflict,
  record it as unresolved and state the material question under Assumptions.
- For features involving shared physical infrastructure (bare metal hosts,
  GPUs, storage backends), check approved sources for requirements or
  exclusions about data and configuration between assignments. Do not infer a
  sanitation, disk-wipe, or credential-rotation exclusion or assign it to a
  responsible service without an approved source. If the boundary is material
  and sources do not settle it, record an actionable question under
  Assumptions; architecture context can inform the question but does not
  authorize product scope.

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

### Persona-Story Alignment Check

After writing all user stories, verify each story's capability matches the
persona's role:

| Capability type | Correct persona |
|----------------|-----------------|
| Tenant onboarding, quotas, global catalogs, cross-tenant visibility | Cloud Provider Admin |
| Infrastructure operations, hardware lifecycle, sanitization, network/storage backends | Cloud Infrastructure Admin |
| Org config, org-scoped catalogs, IDP, org users | Tenant Admin |
| Self-service provisioning, resource lifecycle, click-ops | Tenant User |

A sanitization or hardware lifecycle story under Cloud Provider Admin is a
misattribution — move it to Cloud Infrastructure Admin.

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
source (linked issue, comment). Add `[Assumption]` for unverified statements
that are not supported by Jira or an applicable explicit owner decision. Add
`[Chai:CLAIM_ID]` and a nearby link to its verified original source next to
each material research-backed statement; the durable evidence record/cited
brief retains each source URL, date, and revision. Most statements trace to the
Jira feature — don't tag every one. Never cite proposed,
superseded, unknown, or unverified claims as settled facts.
