---
name: prd-review
description: |
  Review an OSAC PRD against template requirements, OSAC feature dimensions,
  persona coverage, and testability standards. Use when reviewing a PRD PR,
  preparing a PRD for submission, or self-reviewing before /prd:publish.
  Produces structured findings with rubric scores and actionable suggestions.

  Also trigger when user says "review this PRD", "check this PRD",
  "is this PRD ready", "review the requirements doc", or references a PRD
  file or PR.
---

# OSAC PRD Reviewer

## Overview

This skill reviews a Product Requirements Document against a calibrated rubric
with concrete scoring examples. It uses calibrated 0-2 scoring per criterion with
hard pass/fail thresholds — no weighted averages that mask problems.

## When to Use

- Self-reviewing a PRD before running `/prd:publish`
- Reviewing a PRD PR on `enhancement-proposals`
- Checking if a PRD is ready for the design phase
- After `/prd:revise` to verify improvements

## Input Detection

Detect what's being reviewed:

1. **PR URL or number** → Fetch the PRD content from the PR diff
2. **Local file path** → Read the PRD from disk (e.g., `enhancement-proposals/enhancements/<slug>/prd.md` or `.artifacts/prd/*/03-prd.md` for pre-publish drafts)
3. **No input** → Ask: "Which PRD should I review? Provide a PR number, file path, or Jira issue key."

### Fetching from PR

```bash
gh pr diff <N> --repo osac-project/enhancement-proposals
gh pr view <N> --repo osac-project/enhancement-proposals --json title,body,author
```

### Reading from artifact

```bash
ls .artifacts/prd/*/03-prd.md
```

## Load Context

Before reviewing, read these files if they exist:

1. `.design/context/osac-dimensions.md` — services, personas, cross-cutting dimensions
2. `.design/context/review-patterns.md` — reviewer feedback themes and anti-patterns
3. `.planning/codebase/ARCHITECTURE.md` — system architecture for technical grounding

## Scoring Rubric

### Context

A PRD describes WHAT the product must do and WHY — from the user's perspective.
A design document (enhancement proposal) describes HOW — architecture,
controllers, API fields, playbooks. PRDs should be written from the perspective
of a Product Manager, not an engineer.

### Criteria (0-2 each, /10 total)

Score each criterion independently. For each, first state your reasoning,
then assign the score.

#### 1. WHAT — Clear user-facing need? (0-2)

Does the PRD describe a new or changed product capability — something that
requires building, not just writing content? A PRD whose sole deliverable is
documentation, example files, configuration samples, or other content with no
new platform capability is not an enhancement — it belongs in a Jira task, not
the PRD pipeline. Score 0 if there is no new product capability.

Does the PRD clearly describe what users can do or observe?

##### OSAC Dimensions Checklist

Using `.design/context/osac-dimensions.md`, also check whether the PRD
addresses the OSAC dimensions relevant to this feature:
- **Services**: Which services (BMaaS, CaaS, VMaaS, MaaS, Enclave) are in scope?
- **Personas**: Cloud Provider Admin, Cloud Infrastructure Admin, Tenant Admin, Tenant User — which are affected and how?
- **Cross-cutting dimensions** (tenant onboarding, inventory, provisioning, networking, storage, installation): addressed or explicitly out of scope where relevant?
- **Verification scope**: Milestone declares what must be demonstrably working for users (vs deferred); cross-cutting user journeys identified — detailed test plan belongs in the EP
- **Documentation**: User-observable doc needs identified; milestone scope (in scope vs deferred); impact on existing documented workflows — detailed doc plan belongs in the EP
- **UI**: User-observable console needs identified; persona workflows affected; milestone scope (in scope vs API/CLI-only vs deferred) — detailed UI design belongs in the EP
- **API resources**: For each in-scope service, affected API resources listed

##### Scoring

Not every dimension applies to every feature. Don't penalize for dimensions
that aren't relevant — but a PRD that names no personas or services has an
unclear WHAT.

Each affected persona must have at least one user story grouped under a
persona heading (e.g., `### Tenant User`). Mentioning a persona in prose
("Cloud Infrastructure Admins are affected") without a corresponding
`As a <persona>...` user story does not count — the reviewer cannot
evaluate what that persona can actually do.

Personas may share a single heading and story when the capability is
genuinely identical for both (e.g., `### Tenant Admin / Tenant User`
with "As a Tenant Admin or Tenant User, I want..."). This satisfies
coverage for both named personas — do not require a separate heading per
persona when the PRD deliberately consolidates identical stories.
Verify the merge is genuine: if the combined story's outcome or
constraints only actually hold for one of the named personas, treat the
persona whose real need differs as uncovered.

- 0 = Vague, unclear, or describes system internals rather than user outcomes. No personas or services identified, or no per-persona user stories.
- 1 = Ambiguous — need is partially clear but mixed with implementation, missing specifics, or missing affected personas. Or: user stories exist but some affected personas lack stories.
- 2 = Clear, specific, user-observable capabilities. Affected personas and services identified. Each affected persona has at least one user story.

See [calibration-examples.md § 1](references/calibration-examples.md#1-what--clear-user-facing-need) for W=0/1/2 worked examples, including the combined-persona-heading pattern.

#### 2. WHY — Business justification? (0-2)

Is there a clear reason this work matters — user pain, business need, or strategic goal?

- 0 = No justification, or circular reasoning ("we need X because we don't have X")
- 1 = Generic justification — plausible but no specific evidence (e.g., "users need this")
- 2 = Concrete justification — names the pain, quantifies impact, or ties to a strategic goal with a clear causal chain

Take stated evidence at face value. Search the entire PRD for evidence, not
just a dedicated section.

See [calibration-examples.md § 2](references/calibration-examples.md#2-why--business-justification) for Y=0/1/2 worked examples.

#### 3. User-Facing Focus — Free from design leakage? (0-2)

Does the PRD describe user-observable outcomes without prescribing implementation?
A PRD defines WHAT and WHY. The design document (enhancement proposal) defines HOW.

User-facing surfaces (CLI commands, UI pages, API resource names visible to
users) are WHAT. Internal architecture (controllers, reconcilers, playbooks,
env vars, finalizers, internal conditions) is HOW.

##### OSAC Platform Vocabulary

Referencing these by name is acceptable context, not design leakage:
- Platform: OpenShift, Kubernetes, Hosted Control Planes
- Services: BMaaS, CaaS, VMaaS, MaaS, Enclave
- Resources (user-facing): ClusterOrder, ComputeInstance, Tenant, VirtualNetwork, Subnet, SecurityGroup, PublicIPPool, PublicIP, StorageClass
- Networking: OVN, Multus, NetworkClass
- Storage: VAST, CSI
- Auth: Keycloak, OPA
- Tools: kubectl, grpcurl, Helm

##### Scoring

Naming platform technologies is not automatically prescriptive. But mandating
which internal component solves a problem, or describing controller logic,
finalizer behavior, or playbook parameters IS design leakage.

- 0 = PRD reads like a design document — names controllers, describes reconciliation logic, specifies internal API fields or conditions, references playbook parameters
- 1 = Mostly user-focused but some design details leak through — names an internal component or describes a behavior only observable by reading code
- 2 = Describes only user-observable outcomes; implementation details are absent or limited to platform vocabulary

See [calibration-examples.md § 3](references/calibration-examples.md#3-user-facing-focus--free-from-design-leakage) for UF=0/1/2 worked examples, including the illustrative-example-vs-internal-state pair.

**Smell tests:**
- "Could a PM verify this by using the product?" — if no, it's design leakage
- "Would this statement change if we swapped the implementation?" — if no, it belongs in the PRD; if yes, it's design
- "Does this name something only visible in code?" — if yes, it's design leakage

#### 4. Right-Sized — Focused and economical scope? (0-2)

Is the PRD scoped to a coherent set of capabilities, and does it treat
that scope economically? This criterion has two equally-weighted failure
modes — bundling unrelated work, and padding a single coherent capability
with more content than it needs. Either one caps the score.

**Bundling:** When multiple capabilities are present, test independence:
could each ship on its own and provide value? Capabilities that cannot
function without each other are one feature regardless of how many user
stories they span.

**Verbosity:** A focused PRD can still fail this criterion by restating
the same point across multiple sections, including content the template
doesn't call for, or stating specifics with no traceable source. Long
PRDs don't get read — favor the PRD that says what it needs to say once.

- 0 = Bundles 3+ independent capabilities, OR pads a single capability so heavily that a reader cannot extract the actual scope without cutting through the padding.
- 1 = Bundles 1-2 separable capabilities, OR is scoped to one coherent capability but treats it uneconomically (same requirement restated more than once, non-template content).
- 2 = Focused and economical — capabilities require each other to function, and the document states its scope once, without restatement or padding.

See [calibration-examples.md § 4](references/calibration-examples.md#4-right-sized--focused-and-economical-scope) for R=0/1/2 worked examples, including the bundling and verbosity failure modes.

When a PRD scores 0 for bundling, recommend restructuring as an epic with individual
features that can be prioritized, estimated, and delivered independently.

#### 5. Testability — Verifiable requirements? (0-2)

Can the requirements be verified by a PM or QA engineer using the product?

- 0 = Requirements describe activities or system internals that can't be tested from the outside
- 1 = Some requirements are testable, others are vague or describe internal behavior
- 2 = Every requirement and acceptance criterion can be verified by using the product

See [calibration-examples.md § 5](references/calibration-examples.md#5-testability--verifiable-requirements) for T=0/1/2 worked examples.

### Pass/Fail

- **PASS**: Total >= 7/10 AND no zeros on any criterion
- **FAIL**: Total < 7 OR any zero (automatic fail regardless of total)

A single zero is an automatic fail because it signals a fundamental problem
(e.g., the PRD is a design doc, or requirements are untestable). The author
must fix zero-scored criteria before resubmission. Exception: if WHAT
scores zero because the work is content-only (docs, examples, config
samples), the recommendation is to track it as a Jira task, not resubmit
as a PRD.

## Output Format

Present findings as a structured review:

```markdown
## PRD Review: {title}

### Rubric Scores

| Criterion | Score | Notes |
|-----------|-------|-------|
| WHAT (clear need) | X/2 | {explain what need is described and how clearly; note persona/dimension coverage} |
| WHY (justification) | X/2 | {cite the specific evidence found or note its absence} |
| User-Facing Focus | X/2 | {note any design leakage or lack thereof} |
| Right-Sized | X/2 | {assess scope — independent capabilities?} |
| Testability | X/2 | {which requirements are verifiable by using the product?} |
| **Total** | **X/10** | **PASS / FAIL** |

### Verdict: {PASS / FAIL}

{1-2 sentence assessment. If fail, name the zero-scored criteria first.}

### Findings

#### Critical (must fix — zero-scored criteria)
1. {finding with specific section reference, quote the problematic text, suggest a user-focused rewrite}

#### Important (should fix)
1. {finding with specific section reference and suggestion}

#### Suggestions (nice to have)
1. {finding}

### Criterion Details

{For each criterion, explain the score with specific quotes from the PRD.
Show what's good and what needs improvement. For design leakage, quote the
offending text and show what a user-focused rewrite would look like.}
```

## Severity Classification

- **Critical**: Any zero-scored criterion. Also: missing required sections, no personas identified, PRD reads like a design document.
- **Important**: Score of 1 on any criterion. Also: vague non-goals, weak acceptance criteria, scope creep signals, requirements stated as generic capabilities without explicit use cases.
- **Suggestion**: Style improvements, additional non-goals, deeper risk analysis, more specific metrics.

## Notes

- Score based on what's in the PRD, not what you think should be there — if information is genuinely unavailable, "TBD" markers are acceptable
- The WHAT criterion uses `osac-dimensions.md` to check persona and dimension coverage — but features that don't touch networking shouldn't be penalized for not addressing networking
- Compare against the PRD template at `.prd/templates/prd.md` (project override) for structural compliance. If no project override exists, fall back to `.ai-workflows/prd/templates/prd.md`
- A PRD that names specific controllers, playbooks, env vars, or internal conditions has design leakage. This is the most common failure mode — score it under User-Facing Focus
- If the PRD was produced by `/prd:draft`, check that clarification locked decisions are reflected

$ARGUMENTS
