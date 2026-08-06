---
name: generate-prd
description: Generate an OSAC Product Requirements Document from Jira Feature issues with self-review and revision loop.
---

# OSAC PRD Generator

You are generating a Product Requirements Document for the OSAC (Open Sovereign
AI Cloud) project. OSAC is a fulfillment system for provisioning OpenShift
clusters, virtual machines, and bare metal instances with networking and storage.

This skill follows a **generate → self-review → revise** loop to produce
review-ready PRDs. Do not skip any phase.

## Critical Rules

These rules override all other guidance. Violating any is a document failure.

1. **Follow the template exactly.** The PRD has exactly 6 sections: Problem
   Statement, In Scope, Out of Scope, User Stories, Assumptions, Dependencies.
   Do NOT add extra sections — no Terminology, Milestone, Acceptance Criteria,
   Risks, or Open Questions. Extra sections are the most common rejection.
2. **User-facing only.** Never name controllers, reconcilers, finalizers,
   playbooks, conditions, env vars, CRD field names, or AAP job parameters.
3. **Shorter is better.** Top-scoring PRDs average 60 non-blank lines. Most
   PRDs over-generate, not under-generate.
4. **No fabrication.** Every requirement must trace to the Jira source. Do not
   invent customers, metrics, SLA numbers, or requirements.

## Phase 1: Read Context

Read these files in order before generating:

1. `skills/osac/generate-prd/prd-template.md` — output template
2. `skills/osac/generate-prd/osac-context.md` — domain context and common mistakes
3. `skills/osac/generate-prd/context/section-guidance.md` — per-section instructions
4. `skills/osac/generate-prd/context/scoring-rubric.md` — how your output will be scored
5. `skills/osac/generate-prd/context/review-patterns.md` — common reviewer expectations
6. `skills/osac/generate-prd/context/osac-dimensions.md` — services, personas, dimensions
7. All exemplar PRDs from `skills/osac/generate-prd/context/exemplars/` —
   these are merged, reviewer-approved PRDs that scored 9-10/10. Study their
   length, structure, and tone before writing.

## Phase 2: Generate

Read `skills/osac/generate-prd/steps/generate.md` and follow its instructions
to produce the initial PRD draft.

Write the draft to the output file.

## Phase 3: Self-Review

Read `skills/osac/generate-prd/steps/review.md` and follow its instructions
to score your draft against the 5-criterion rubric (WHAT, WHY, User-Facing
Focus, Right-Sized, Testability — each 0-2, total /10).

Also run these inline checks against your draft:

1. **Section count:** Exactly 6 sections (Problem Statement, In Scope, Out of
   Scope, User Stories, Assumptions, Dependencies). No extra sections.
2. **Persona coverage:** All 4 OSAC personas mentioned (with stories or "Not
   affected" notes).
3. **Design leakage scan:** Search your draft for these terms — any match is a
   failure: `reconciler`, `reconciliation`, `finalizer`, `playbook`, `env var`,
   `AAP job`, `CRD field`, `osac-operator`, `osac-aap`, `ansible role`,
   `controller` (excluding "Hosted Control Planes").
4. **Line count:** 15-120 non-blank lines (target 40-80).

If the rubric total is >= 7 with no zeros AND all inline checks pass, proceed
directly to Phase 5 (Output).

If any check fails or the rubric total is < 7 or any criterion scored 0,
proceed to Phase 4 (Revise).

## Phase 4: Revise

Read `skills/osac/generate-prd/steps/revise.md` and follow its instructions
to fix the issues identified in Phase 3.

Key principles:
- Only fix what the review flagged — do not rewrite sections that scored well.
- Reframe design leakage as user-observable outcomes — do not simply delete.
- Never invent requirements to improve a score.

After revision, re-run the inline checks from Phase 3 to verify no regressions.

## Phase 5: Output

Write the final PRD ensuring:

- [ ] No trailing whitespace on any line
- [ ] File ends with exactly one newline
- [ ] Directory name follows `{issue-key}-<slug>` convention
  (e.g., `enhancements/OSAC-2135-caas-baremetal-provisioning/prd.md`)
- [ ] Filename is lowercase `prd.md`
