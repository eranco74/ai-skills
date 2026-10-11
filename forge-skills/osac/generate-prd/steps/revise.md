# Phase 5: Revise PRD

Your self-review identified issues in the draft. Fix them following these rules.

## Critical Rules

1. **Only fix what the review flagged.** If a criterion scored 2, do not touch
   that section. Focus on criteria that scored 0 or 1, and failed deterministic
   checks.
2. **Reframe, don't remove.** When design leakage is flagged, rewrite as a
   user-observable outcome — do not delete the underlying need.
   "The controller invokes AAP to install CSI" → "Persistent storage is
   automatically available on the cluster."
3. **Never invent requirements or evidence.** If WHY is weak, use only the Jira
   input and verified, cited research claims that support user-facing context.
   Do NOT fabricate customers, metrics, impacts, dates, or decisions, and do
   not promote proposed, superseded, unknown, or unverified claims.
4. **Preserve working user stories.** Don't rewrite stories that were not
   flagged. Only fix the ones marked as too generic or containing design leakage.
5. **Don't add sections to fix scores.** If WHAT scored low, improve existing
   user stories — don't add a Risks or AC section.

## Fix Strategies by Criterion

### WHAT scored 0 or 1

- Add missing persona headings and user stories
- Make generic stories specific — name concrete artifacts and scenarios
  ("manage secrets" → "store SSH keypairs and retrieve cluster kubeconfigs")
- Add "Not affected by this feature." notes for unaffected personas
- Add OSAC services identification if missing

### WHY scored 0 or 1

- Strengthen Problem Statement with available evidence
- Use relevant, verified organizational evidence only for user-facing context
  and cite its claim ID; retain its URL, date, and revision in the durable
  record/cited brief. A claim state alone does not authorize new PRD scope.
- Add cost of inaction ("If not addressed, ...")
- Name who is affected ("Tenants cannot...", "Cloud Provider Admins must...")
- Do NOT fabricate evidence — use only Jira and verified, cited research

### User-Facing Focus scored 0 or 1

- Replace controller/reconciler/finalizer names with user outcomes
- Replace playbook parameters with operational outcomes
- Remove SLA numbers not from Jira (60 seconds, 10 minutes, etc.)
- Remove internal condition names (BareMetalInstanceReady, etc.)
- Remove cleanup mechanics (disk wipe, network reset) — say "securely
  sanitized" instead
- Keep platform vocabulary (ClusterOrder, ComputeInstance, etc.)

### Right-Sized scored 0 or 1

- Note that scope should be reconsidered but do NOT remove capabilities
- If clearly bundling independent features, add an In Scope note suggesting
  the scope is tightly coupled (or note the coupling)

### Testability scored 0 or 1

- Rewrite vague stories with specific, PM-verifiable outcomes
- Replace "handle appropriately" with named behavior
- Replace system-internal metrics with user-observable ones
- Replace "system does X" with "user can observe/do X"

## Fix Strategies for Deterministic Check Failures

### Extra sections found

Remove any sections not in the template: Terminology, Milestone Scoping,
Acceptance Criteria, Risks, Open Questions. Move any valuable content from
those sections into the appropriate template section (e.g., risk info into
Assumptions or Out of Scope).

### Missing persona coverage

Add missing persona headings to User Stories with either a concrete story or
"Not affected by this feature."

### Design leakage terms found

For each flagged term, rewrite the containing sentence as a user-observable
outcome. See the design leakage examples table in `steps/generate.md`.

### Over/under length

- If too long: consolidate duplicate user stories, remove padding from Out of
  Scope, tighten In Scope bullets, shorten Problem Statement
- If too short: check that all affected personas have stories, verify In Scope
  covers key boundaries

## Post-Revision Check

After revising, verify:

- [ ] Problem Statement still user-focused (not weakened)
- [ ] All persona headings still present
- [ ] No new design leakage introduced
- [ ] User stories still specific
- [ ] No fabricated requirements added
- [ ] Every In Scope and Out of Scope item traces to Jira or an applicable,
      explicit owner decision with verified source references in the durable
      record; do not turn Jira omissions or unresolved questions into scope
- [ ] Every research-backed statement retains `[Chai:CLAIM_ID]` and a nearby
      link to its verified original source; reuse the same per-run record and
      check source references, URLs, dates, and revisions in the cited brief
- [ ] Refresh the cited-brief coverage table after revision: every explicit
      requirement ID is `covered`, `unresolved`, or `omitted` and maps to the
      current PRD statement/section or an open question. Preserve remaining
      technical verification duties in the sidecar/handoff; no material ID is
      omitted. Unresolved owner decisions remain questions.
- [ ] Diagnostic payload stories qualify access by an explicit approved
      requirement or verified existing access control; tenant visibility alone
      does not authorize diagnostic access
- [ ] The current-run JSON and cited brief exist and were reread after revision;
      record identity still matches the Jira key, `prd` stage, run ID, and mode
- [ ] Unresolved material conflicts remain marked unresolved, not rewritten as
      settled requirements; while any remain, mark the PRD incomplete for
      downstream design
- [ ] Template structure preserved (still exactly 6 sections)
- [ ] No trailing whitespace on any line
- [ ] File ends with exactly one newline
