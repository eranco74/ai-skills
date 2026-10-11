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
4. **No unsupported claims.** Every requirement must trace to explicit Jira
   scope or an applicable, explicit owner decision recorded in the evidence
   record. A Chai claim's decision state alone does not make it a requirement.
   Do not invent customers, metrics, SLA numbers, or evidence.
5. **Evidence completion is a hard gate.** A supplied `research-input.json` or
   replay record is input, not proof that this run's completion artifacts were
   saved. Before drafting, write the current-run research JSON and cited brief
   using the caller's `research_record_path` or artifact workspace, then
   reread and validate them. Verify schema version, required fields and enums,
   references, and exact feature/stage/run/mode identity. If replay input is
   missing or invalid, or either completion artifact cannot be written or
   validated, stop without drafting a PRD.
6. **Account for every requirement ID.** During review, map each explicit
   requirement ID to a PRD section or an unresolved question in the cited-brief
   sidecar. Translate technical Jira acceptance criteria into user-facing
   outcomes for observable behavior. Preserve technical verification duties in
   the sidecar. Do not omit requirements to meet length or style
   rules; an omitted material requirement prevents readiness.
7. **Cite research and qualify diagnostic access.** Material organizational
   facts require a `[Chai:CLAIM_ID]` marker and a link to the verified original
   source in an existing PRD section. A persona's ability to see tenants does
   not authorize access to every diagnostic payload; qualify the audience by
   verified access controls or keep authorization as an unresolved question.
8. **Final response only.** Return only the PRD document, with no preamble,
   progress note, review commentary, rubric, separator, or epilogue.
9. **Save the document itself.** Write the final document to the caller's
   `document_output_path` before responding. A filesystem-only runner without
   an explicit document path uses `/home/user/prd.md`. Return the same document
   bytes. Save `{KEY}-coverage.json` beside the research record during review.

The coverage JSON must use these exact keys; repeat the row for every ID in the
research record, replacing placeholders with this run's identity and verdicts:

```json
{"schema_version":1,"feature_key":"KEY","stage":"prd","run_id":"RUN_ID",
 "requirements":[{"id":"R1","status":"unresolved","evidence":"Actual draft passage or open question"}]}
```

`coverage`, `requirement_id`, `location`, or `statement` are not substitutes for
these keys. A mechanical artifact check rejects a different shape. Mark a row
covered only when the draft or preserved verification handoff supports it.

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
8. `skills/osac/generate-prd/context/organizational-research.md` — how to
   collect, record, cite, and validate optional Chai evidence.

## Phase 2: Prepare Evidence and Scope

Before drafting, read `skills/osac/generate-prd/steps/generate.md` through
"Step 1.5: Extract Requirements and Build the Scoped Evidence Record". Use
caller-provided research context when present; if `research_mode` is absent,
default to `live`. The steps document defines the per-run identifier, replay
input, `research_record_path`, and artifact fallback without assuming Forge
exposes a particular CLI or configuration interface. Create and reread the
durable per-run `prd` research record, cited brief, and raw retrieval sidecar
before drafting. Keep the Jira extraction in
`/tmp/scope-contract.md` and copy its explicit requirements into the durable
record. In `live` mode, use only the read-only `ask_persona` research tool
described by that contract; do not submit lessons or feedback.

If the default or selected `live` mode has no exposed tool, record
`unavailable`; if a call times out, record `timeout`. Continue from Jira and
explicitly approved inputs without implying research succeeded or turning
unverified evidence into requirements. Reuse this record during self-review
and revision; validate source references as directed by the contract and keep
unresolved material conflicts explicit. A material unresolved conflict must
remain visible in Assumptions and makes the PRD incomplete for downstream
design.

## Phase 3: Generate

Read `skills/osac/generate-prd/steps/generate.md` and follow its instructions
to produce the initial PRD draft.

Write the draft to the output file.

## Phase 4: Self-Review

Read `skills/osac/generate-prd/steps/review.md` and follow its instructions
to score your draft against the 5-criterion rubric (WHAT, WHY, User-Facing
Focus, Right-Sized, Testability — each 0-2, total /10).

**Perform this review silently — do NOT output scores, reasoning, or check
results as text. Evaluate internally, then act on the results.**

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
directly to Phase 6 (Output).

If any check fails or the rubric total is < 7 or any criterion scored 0,
proceed to Phase 5 (Revise).

## Phase 5: Revise

Read `skills/osac/generate-prd/steps/revise.md` and follow its instructions
to fix the issues identified in Phase 4.

Key principles:
- Only fix what the review flagged — do not rewrite sections that scored well.
- Reframe design leakage as user-observable outcomes — do not simply delete.
- Never invent requirements to improve a score.

After revision, re-run the inline checks from Phase 4 to verify no regressions.

## Phase 6: Output

Write the final PRD ensuring:

- [ ] The final document was written to `document_output_path` (filesystem-only
      fallback `/home/user/prd.md`), without commentary.
- [ ] The machine-readable `{KEY}-coverage.json` exists beside the research
      record, uses the same feature/stage/run identity, and accounts for every
      requirement ID with its status and actual draft passage or question.
- [ ] The current-run research JSON and cited brief exist and were reread.
- [ ] The record has `schema_version: 1`, required fields and valid enums,
      valid source references, and matching `feature_key`, `stage: prd`,
      `run_id`, and `research_mode` for this run.
- [ ] Every material research-backed statement has an inline `[Chai:CLAIM_ID]`
      marker and a nearby link to its verified
      original source; the claim and source URL/date/revision also appear in
      the evidence record and cited brief.
- [ ] The cited-brief coverage sidecar maps every requirement ID as covered,
      unresolved, or omitted to a PRD statement or open question. No material
      requirement is omitted; unresolved requirements remain visible and block
      readiness.
- [ ] Diagnostic user stories identify only audiences authorized by verified
      requirements or existing access controls; persona names alone do not
      authorize cross-tenant diagnostic details.
- [ ] Any unresolved material conflict remains explicit in Assumptions; the
      PRD is not described as complete for downstream design while it remains.
- [ ] No trailing whitespace on any line
- [ ] File ends with exactly one newline
- [ ] Directory name follows `{issue-key}-<slug>` convention
  (e.g., `enhancements/OSAC-2135-caas-baremetal-provisioning/prd.md`)
- [ ] Filename is lowercase `prd.md`

The final response must contain only the PRD, starting with its title and ending
with its final document line. Do not include a preamble, progress note,
separator, self-review, rubric, explanation, or epilogue. If an evidence setup or
completion-artifact gate fails, stop without a PRD and report only the specific
failure and required path.
