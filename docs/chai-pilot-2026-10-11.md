# Chai research pilot — 2026-10-11

## Implementation

Both standalone and Forge workflows now have a common organizational evidence
contract, `live`/`off`/`replay` modes, persisted source states and run identity,
citation rules, and requirement coverage sidecars. Standalone pipelines enforce
research completion and coverage readiness. Forge requires an external
Python-capable caller to enforce `research_context.py check-artifacts` before
promotion; skill instructions alone are not an enforcement hook.

The optional direct client and ask-only stdio bridge give Chai 900 seconds and
use system certificate trust. The bridge was tested through the real LangChain
MCP adapter and exposed only `ask_persona`. Forge's audited name-based read-only
filter does not exclude the upstream `submit_feedback`/`submit_lesson` tools.
Credentials remain in the runtime's environment, not this repository.

See the root and Forge READMEs for setup. `make research-check` passes 41 tests.
Whole-repository lint has the same eight pre-existing dotted-name errors and
six warnings as the baseline; no new warning remains.

## Comparison

Three cases: OSAC-5672 architecture, OSAC-5888 volume attachment, and OSAC-6008
retry failure visibility. Same Vertex Sonnet 4.5 model within each environment;
two repeats and two smaller-model reviewers. Gold/eval artifacts stayed outside
generation. Case inputs, skill trees, evidence, and ratings were frozen.

Forge had 18 generations: A = original 441f38d; B = revised workflow/research
off; C = the identical revised workflow with source-audited evidence replay from
one live Chai query per case. Standalone had 12 B/C first-draft generations with
tools disabled, reported separately from full Forge skill invocations.

Explicit requirement coverage, averaged over repeats and reviewers:

| Feature | Forge A | Forge B | Forge C | Native B | Native C |
|---|---:|---:|---:|---:|---:|
| Architecture | 46.9% | 45.3% | 43.8% | 48.4% | 76.6% |
| Volumes | 75.0% | 75.0% | 67.0% | 87.5% | 95.5% |
| Retry failures | 95.0% | 82.5% | 90.0% | 92.5% | 92.5% |

Chai improved coverage on two standalone first-draft cases; Forge did not show
an overall coverage gain. It recovered useful architecture/schema context and
identified that the accepted volume attachment PRD's design was unmerged at the
evidence cutoff. It did not eliminate omissions, design leakage, or inferred
diagnostic permissions. One reviewer flagged a native C scope error as severe;
the other classified it as major. Preserve that uncertainty.

The three main live calls completed in 390.7, 508.1, and 765.6 seconds. Raw answers
contained wrong dates, unverified citations, target echoes, and overstated
decision states. C measures **Chai plus independent primary-source auditing**,
not raw answers. The separate connector smoke returned a target-design source;
that content never entered generation, and the live corpus is not held out.

## Hardening after the frozen comparison

Failed outputs and development rounds were retained. Added deterministic artifact
checks and exact-schema coverage scaffolding, explicit final-document files,
clear six-heading Forge rules, source links, and native readiness gates. Fixed
the native design `{ID}.md` versus `{ID}-design.md` completion mismatch.

Three final development runs produced valid current-run artifacts; the gate held
the architecture draft for unresolved testing/resource-audit obligations. Passing
mechanical checks permits semantic review, not publication or owner approval.
Technical detail in PRDs and audience assumptions still need review.

## Limits and next step

This is a small purposeful sample with correlated model reviewers, not statistical
proof. Native results cover only first drafts; design generation was deferred
because no approved PRD inputs were supplied. No final-revision quality benchmark,
full native pipeline performance claim, or complete cost comparison is available.

Use bounded research when material decisions are missing. Reuse verified evidence
through review/revision and keep Jira/explicit owner decisions or an approved PRD
authoritative. Validate artifacts outside the model and review source/scope truth
before promotion. Run the final revision on new cases and approved design inputs
before making a broad Forge improvement claim.

The local pilot artifacts are under `/home/ercohen/artifacts/ai-skills-chai-pilot/`:
`report.md`, the self-contained `comparison.html`, raw questions/responses,
primary-source captures, frozen manifests, all 60 ratings, adjudication, traces,
and validation logs. They are separate from this repository so target outputs
cannot become skill context. No remote changes, feedback, or lessons were sent.
