# PRD Section Guidance

Instructions for the AI on how to fill each section of the OSAC PRD
template (`enhancement-proposals/guidelines/prd_template.md`). This file
is read during the `/draft` phase. It is not included in the final output.

This is a project-level override of the upstream `ai-workflows` section
guidance. OSAC's PRD template has 6 sections — Problem Statement, In
Scope, Out of Scope, User Stories, Assumptions, Dependencies — not the
upstream 8-section template (Goals and Non-Goals, Requirements with
FR-N/NFR-N, Acceptance Criteria, Risks, Open Questions). Only the
sections below apply; do not add sections the OSAC template doesn't have.

## General Rules

These apply across all sections:

- **Favor conciseness.** These documents are read by humans. Write enough
  to communicate clearly and no more. If a section can be said in three
  sentences, do not use ten. Long PRDs don't get read — there are no
  awards for a long PRD.
- Write prose in third person, present tense. The User Stories formula
  ("As a {persona}, I want...") is a stated exception — write it in first
  person as specified in the User Stories section below.
- Be specific. Vague requirements produce vague implementations.
- Every claim should be traceable to the source requirements or
  clarification answers. Use standardized source markers for
  traceability:
  - `[Jira: OSAC-3254]` — from the Jira issue description or acceptance
    criteria
  - `[Jira: OSAC-3254, comment by @user]` — from a specific Jira comment
  - `[Clarify: R1.Q3]` — from clarification round 1, question 3 (matches
    `R1.Q3` headings in `02-clarifications.md`)
  - `[User]` — from direct user instruction during the workflow
  - Place markers at the end of the requirement or statement they
    support.
- **Consolidate markers.** When most content traces to the same Jira
  issue, tagging every statement with `[Jira: OSAC-NNNN]` adds noise
  without aiding traceability. Instead:
  - Tag a statement with its specific source only when the source is
    non-obvious or differs from the primary issue.
  - Rely on the metadata table's Jira field for the overall issue
    reference.
  - Reserve inline markers for clarification-derived changes
    (`[Clarify: ...]`) and direct user instructions (`[User]`).
- **Incorporate, don't narrate.** When a clarification changed the scope
  or corrected an assumption from the source material, write the content
  in its corrected form. Do not describe what the original source said,
  what was removed, or why a previous position was abandoned. The PRD
  states current intent; the clarification log preserves the editorial
  history.
- Do not invent features, constraints, or details not supported by the
  ingested requirements or clarification responses.
- If information for a section is genuinely unavailable after
  clarification, write "To be determined — {what's needed}" rather than
  fabricating content.
- **Formatting restraint.** Use bold sparingly for genuine emphasis —
  terms the reader must not miss or that distinguish this requirement
  from a similar one. When every noun phrase is bold, nothing stands out.
- **User-facing focus.** PRDs are written from a Product Manager's
  perspective. Every statement should describe something a user can do,
  see, or experience. Signs that content has strayed into design: it
  describes specific API fields, it references where in the code
  something will happen, or it describes something the user wouldn't be
  able to observe. Those details belong in the design document, not the
  PRD.
- **Persona consolidation.** When two or more personas want the
  genuinely identical capability, combine them under a single heading
  and story instead of duplicating: `### Tenant Admin / Tenant User`
  with "As a Tenant Admin or Tenant User, I want persistent storage to
  be available on my CaaS cluster when it is ready...". Only combine
  when the capability is truly identical — if personas experience the
  capability differently (different constraints, different visibility
  scope), keep separate stories. See `prd_guide.md`'s "Duplicated persona
  stories" entry (Common Mistakes) for the canonical rule statement.
- **Illustrative-example allowance.** A single minimal example (a sample
  request/response shape, a short flow list, a format a user types) may
  accompany prose when it is the clearest way to convey a user-observable
  capability or constraint — modeled on the diagram rule below (sparing
  use, always followed by prose stating the user-facing implication).
  This is not license to describe internal architecture, controller or
  reconciler logic, or name CRD fields/conditions — the PRD vs Design
  litmus test in `prd_guide.md` still governs what the example may
  contain. See `prd_guide.md`'s "A narrow exception: illustrative
  examples" entry for the canonical rule statement and worked example
  (the port-mapping format a tenant types, `8080:80`, versus a
  reconciler's internal condition payload).
- **Source dimensions, don't transcribe them.**
  `.design/context/osac-dimensions.md` and `review-patterns.md` help
  identify what content a feature needs (which personas, which
  cross-cutting dimensions apply)
  — they are not a checklist to copy into In Scope/Out of Scope. Only
  include a dimension's content if the feature's Jira issue plausibly
  touches it (see `osac-dimensions.md`'s own "Applying These Dimensions"
  triage rule); when a dimension applies, state its user-facing impact in
  your own words rather than restating the dimension file's questions
  verbatim.
- **Diagrams.** When a visual clarifies user flows, interaction
  sequences, or system boundaries in any section, use Mermaid diagrams.
  Only include a diagram when it adds clarity that prose alone cannot.
  - Use only `flowchart` or `sequenceDiagram` types (these render
    reliably on GitHub).
  - Keep diagrams simple: labeled nodes, clear edge labels, no styling
    directives (`style`, `classDef`, color codes).
  - Always introduce a diagram with a sentence explaining what it shows
    and why it's relevant.
  - Do not use ASCII art or PlantUML.

## Problem Statement

- Lead with the user's pain, not the solution.
- Quantify impact if the source material supports it (e.g., "affects N
  tenants," "adds M minutes per deployment").
- Explain the cost of inaction — what happens if this work is not done.
- Typically 3-5 sentences when the source material supports that length —
  this is a ceiling, not a floor. If the problem is genuinely clear in
  fewer sentences, stop there; if it takes more than 5, the problem isn't
  well enough understood yet — that's a signal to ask more clarifying
  questions, not to write more prose.

## In Scope

- Bullet list; each item should trace to a user story below it, not
  restate one. "Tenants can create persistent volumes on CaaS clusters"
  duplicates a user story with no new boundary — omit it. "Storage is
  available on both new and pre-existing clusters after upgrade" adds a
  boundary a user story alone wouldn't convey — keep it.
- Only state a cross-cutting dimension's in-scope content when the
  feature's Jira issue plausibly touches that dimension (per
  `osac-dimensions.md`'s triage rule). Do not add a bullet for every
  dimension in the checklist just to show coverage.
- If there is little to say beyond what the user stories already convey,
  a short list (2-4 items) is correct — do not pad to look thorough.

## Out of Scope

- Bullet list; only include what a reader might reasonably assume is
  included but isn't. "Advanced features are out of scope" tells the
  reader nothing; "Auto-scaling and multi-region placement are out of
  scope — addressed in a separate proposal" does.
- Do not restate user stories in negative form ("Tenants cannot use
  feature X" when X was never proposed). Every entry should close a
  boundary a reasonable reader would otherwise assume is open.
- **This section is optional.** If there's nothing beyond the obvious,
  omit the section body entirely — do not write "N/A" or invent
  non-goals to fill the section.

## User Stories

- Group by persona, using the standard formula: "As a {persona}, I want
  {capability} so that {outcome}."
- One capability per story. If a story has "and", split it.
- Ground each story in concrete artifacts, workflows, or scenarios — name
  the specific things users interact with, not generic capabilities.
  "I want to store SSH keypairs and OIDC client secrets" is actionable;
  "I want to create and manage secrets" is too vague to review.
- Apply the persona-consolidation rule from General Rules when the
  capability is genuinely identical across personas — this is the
  primary lever for keeping this section from becoming redundant.
- Every affected persona (from `.design/context/osac-dimensions.md`'s
  Personas table) needs at least one story, standalone or consolidated.
  Do not mention a persona in prose without a corresponding story — the
  reader cannot verify what that persona can actually do.

## Assumptions

- **This section is optional.** If the requirements rest on no unverified
  assumptions, omit this section rather than writing "None."
- An assumption is a statement the PRD treats as true but that has not
  been confirmed. If it turns out to be false, one or more user stories
  or scope boundaries may need to change.
- Do not list things that are verifiable right now — verify them and
  fold them into the Problem Statement or In Scope instead.
- Assumptions are valuable specifically because they invite challenge.
  Reviewers should be able to look at this list and say "that one isn't
  true" before implementation begins.
- **Not the same as `[Assumption: ...]` markers.** Inline markers flag AI
  judgment calls during drafting — they are transient and resolved with
  the user before the document is saved. This section captures
  product-level preconditions the user has acknowledged but that remain
  unverified.

## Dependencies

- **This section is optional.** If the source material identifies no
  external dependencies, omit this section rather than writing "None."
- List teams, services, APIs, or external systems that this work depends
  on or that depend on this work.
- Include ordering constraints: "Networking API changes must land before
  this feature's VirtualNetwork integration."
