# Deep Review: OSAC PRD Creator Audit

**Date:** 2026-07-24
**Reviewer:** Engineering audit via systematic comparison of generated PRDs, gold-standard PRDs, Jira source material, and actual PR review comments.

---

## Section 1: Strengths

### 1.1 Design leakage avoidance is excellent

The generator consistently produces PRDs with less design leakage than the gold-standard human-authored PRDs. The independent reviews confirm this across all three cases evaluated in iter3:

- **OSAC-2917:** Generated says "infrastructure-level GPU passthrough plumbing" vs gold's "Ansible-level GPU passthrough plumbing in `osac-aap`." The generated version is cleaner.
- **OSAC-2872:** Generated avoids naming "tier resolution (maps a tenant's StorageClass to the correct vendor backend)" as a mechanism. The gold includes borderline leakage that the generator avoids.
- **OSAC-1567:** Generated avoids prescribing "Vault-compatible" technology choice, using "compatible secret store" instead.

The leakage checker in `score_prd.py` correctly catches controller, reconciler, finalizer, playbook, env var, AAP job, CRD field, osac-operator, osac-aap, and ansible role. The pattern `\bcontroller\b(?!\s+Planes?)` correctly excludes "Hosted Control Planes."

### 1.2 Problem statement quality is consistently strong

Generated PRDs lead with user pain and include cost-of-inaction language. OSAC-1332 is a standout:

> "CaaS tenant clusters are provisioned without persistent storage. When a tenant's cluster becomes ready, it has compute and networking but no ability to create persistent volumes. Tenants cannot run stateful workloads -- databases, message queues, AI model checkpoints -- until someone manually configures storage on their cluster."

This is specific, user-focused, and names concrete workload types.

### 1.3 Persona coverage is thorough

Every generated PRD addresses all four OSAC personas with explicit headings. Unaffected personas are noted with rationale (e.g., OSAC-2917: "Not affected by this feature. GPU node installation and configuration is a prerequisite handled outside OSAC."). The gold PRDs sometimes omit unaffected personas entirely (OSAC-2872 gold omits Cloud Infrastructure Admin).

### 1.4 Out of Scope sections are exhaustive

Generated PRDs consistently have 10-14 Out of Scope items with deferral notes, exceeding the gold standard in boundary-setting. OSAC-1567 generated has 10 Out of Scope items vs gold's 2. OSAC-2540 generated has 12 items with reasons for each.

### 1.5 Template adherence is perfect

100% structure pass rate across all iterations. Every PRD has Problem Statement, In Scope, Out of Scope, User Stories, and optional Assumptions/Dependencies.

### 1.6 Iteration loop works

The iter1-to-iter2 improvements are measurable. All six gaps identified in the OSAC-1567 independent review were fixed in iter2 (wrong strategic framing, missing encryption, missing pluggable backends, missing secret update, UI incorrectly included, missing Cloud Infrastructure Admin).

---

## Section 2: Gaps vs Gold Standard

### 2.1 OSAC-2917 (GPU-Enabled Compute Instances)

**Generated score: 9/10 (self-review). Gold score: 9/10. Independent iter3: 4.6/5.**

Differences are minimal after iter2 revision:
- Generated adds "GPU ComputeInstances carry the standard OSAC tenant isolation metadata" and "When requested GPU hardware is unavailable, ComputeInstance creation follows the same failure behavior" to In Scope. Gold has these only in Acceptance Criteria. This is a valid structural difference, not a gap.
- Generated strips `[Clarify: R1.Q*]` provenance tags from gold -- expected behavior.
- Generated says "infrastructure-level GPU passthrough plumbing" vs gold's "Ansible-level GPU passthrough plumbing in `osac-aap`" -- generated is cleaner.

**Remaining gap:** Self-review gives testability 1/2 but overall 9/10, matching gold. The self-review correctly identifies the imprecise AC items but the final score is appropriate.

### 2.2 OSAC-1270 (Base OS Management for Bare Metal)

**Generated score: 10/10 (self-review). Gold score: 10/10.**

The generated PRD is significantly longer than the gold (57 lines vs 38 lines). Key differences:
- Generated has 5 In Scope items vs gold's 5, but the generated version has more explanation per item.
- Generated has 12 Out of Scope items vs gold's 5. The extra items (audit logging, quota/metering, UI integration, image caching, image scanning, image versioning, MaaS/CaaS image management) provide useful boundary-setting.
- Generated has 11 user stories vs gold's 8. The extra stories (Cloud Provider Admin listing all images, Tenant User seeing template default applied automatically) add specificity.

**Gap:** The gold PRD scopes this feature as BMaaS-only DiskImage integration (after OSAC-2540 defined the shared DiskImage resource). The generated PRD treats it as a standalone BMaaS image catalog feature. The gold says "This PRD covers the integration of the DiskImage resource (defined in OSAC-2540) into BMaaS. It does not change DiskImage behavior." The generated PRD does not include this scoping statement, instead building a more comprehensive standalone feature. This is a significant framing difference -- the generated version is correct for the Jira input (which describes a standalone feature), but differs from how the gold PRD was eventually scoped after review.

### 2.3 OSAC-2540 (DiskImage Resource)

**Generated score: 10/10 (self-review). Gold score: 9/10.**

The generated PRD is longer (102 lines vs 78 lines) due to an appended "OSAC Dimensions" section. This section duplicates information from the main body (personas, provisioning, installation, milestone scoping).

**Gap:** The gold PRD has a "Provenance" section with authoring metadata. The generated PRD does not. This is expected -- provenance is added by the publishing workflow, not the generator.

**Gap:** The gold PRD uses em-dashes consistently while the generated uses double-hyphens. Minor formatting difference.

### 2.4 OSAC-1332 (CaaS Cluster Storage)

**Generated score: 10/10 (self-review). Gold score: 8/10.**

The generated PRD is nearly twice the length of the gold (59 lines vs 31 lines). The gold combines Tenant Admin and Tenant User under one heading; the generated separates them with overlapping stories.

**Gap:** Gold concisely states "Tenant Admin / Tenant User" with combined stories. Generated creates separate sections with 4 stories each, where 3 are near-duplicates. The gold's approach is more pragmatic and communicates that these personas share capabilities -- important scoping information.

**Gap:** Gold has 4 Out of Scope items. Generated has 14. Many generated items (volume resize/snapshots/clones, CSI certification, audit logging, multi-vendor storage, cross-cluster migration) are legitimate boundary items. But "Storage metering and billing," "Storage quotas," and "Cross-cluster storage migration" feel distant from the feature boundary.

### 2.5 OSAC-1567 (Secret Management)

**Generated score: 10/10 (self-review). Gold score: 8/10. Independent iter1: 3/5, iter3: 4.2/5.**

After iter2 revisions, the generated PRD closely matches the gold. Remaining difference:
- Gold uses "Vault-compatible" throughout. Generated uses "compatible" without naming Vault. This loses a meaningful requirement constraint -- the gold deliberately names the Vault API as the compatibility target. This is the most significant content gap in the iter2 output.

### 2.6 OSAC-2872 (OSAC Storage Control Plane)

**Generated score: 10/10 (self-review). Gold score: 9/10. Independent iter3: 4.6/5.**

The iter2 generated PRD matches the gold structurally and substantively. Three differences noted:
- Generated adds adoption impact sentence to Problem Statement (improvement over gold).
- Generated adds Cloud Infrastructure Admin "Not affected" section (improvement).
- Generated adds VAST reachability assumption (improvement).

No meaningful gaps remain.

---

## Section 3: Fabrication Risk

### 3.1 Source files are empty

The most critical finding in this audit: **the source files for OSAC-2917 and OSAC-1567 contain "(No description)"** despite the Jira issues having rich descriptions. The `fetch_feature.py` script fails to parse the `jira` CLI output format.

Looking at the actual Jira output for OSAC-2917:
```
  # GPU-Enabled InstanceTypes for ComputeInstances (MVP)
  ...
  ------------------------ Description ------------------------
  ## Feature Goal
  Enable OSAC tenants to create ComputeInstances with GPU hardware...
```

The script looks for `line.startswith("Description:")` but the jira CLI `--plain` output uses a section header `"Description"` with decorative dashes, not a `Key: Value` format. The script is parsing a different output format than what `jira issue view --plain` produces. **This means the generator is working from the exemplars and context alone, not from the actual Jira source.** The fact that the generated PRDs are still high quality indicates the exemplars are doing heavy lifting, but it also means the "no fabrication" rule is being satisfied by coincidence rather than by design.

### 3.2 Content not traceable to Jira source

Since the source files are empty, every requirement in the generated PRDs is technically "fabricated" relative to the source file, though it actually comes from the exemplars (which are copies of the gold PRDs from enhancement-proposals). This creates a circular dependency: the generator learns from the exemplars (which are the gold PRDs) and produces output similar to them.

### 3.3 OSAC-2540 Over-specification

The generated OSAC-2540 PRD includes an "OSAC Dimensions" section with sub-sections (Services, Personas, Provisioning, User-Facing API, Tenant Onboarding, Networking/Storage/Inventory, Installation, Milestone Scoping) that the gold PRD also has (because the gold was produced by the same PRD workflow). However, this section duplicates information already in the main body and is not part of the PRD template. It appears to be a prompt artifact -- the `osac-dimensions.md` context file describes these dimensions, and the generator creates a section for them rather than weaving the information into the existing sections.

### 3.4 OSAC-1332 Over-expansion

The generated OSAC-1332 has 14 Out of Scope items where the gold has 4. Several items (e.g., "BMaaS storage changes," "Cross-cluster storage migration," "CSI certification") are plausible but not mentioned in the Jira source or the gold. These are technically fabricated scope boundary items, though defensible ones. The generator seems to draw from the `osac-dimensions.md` context to generate boundary items, which occasionally produces items too distant from the feature.

---

## Section 4: Prompt Improvements

### 4.1 generate-prd.md: Fix duplicate numbering

Current text:
```
6. **Be concise.** Target 40-80 non-blank lines...
7. **Derive Author from Jira.**...
6. **Scope tightly.**...
7. **No design leakage smell tests:**...
```

The rules 6 and 7 are numbered twice. This is a formatting bug.

Improved version:
```
6. **Be concise.** Target 40-80 non-blank lines...
7. **Derive Author from Jira.**...
8. **Scope tightly.**...
9. **No design leakage smell tests:**...
```

### 4.2 generate-prd.md: Add OSAC Dimensions integration guidance

Current text does not instruct the generator on how to handle the OSAC Dimensions context. The generator sometimes creates a separate "OSAC Dimensions" section, duplicating the main body.

Add after the template structure section:
```markdown
### OSAC Dimensions Integration

Do NOT create a separate "OSAC Dimensions" section. Instead, weave dimensional
information into the existing sections:
- Services: Note in the metadata table (Service field) or Problem Statement
- Personas: Cover in User Stories section
- Cross-cutting dimensions: Address in In Scope / Out of Scope as appropriate

The dimensions context is a checklist for completeness, not a section to copy.
```

### 4.3 generate-prd.md: Add persona combination guidance

Current text says:
```
If two personas have identical capabilities in this feature, combine them
(e.g., "### Tenant Admin/User")
```

This guidance works but needs stronger emphasis. The generator sometimes ignores it and creates duplicate stories. Add:
```markdown
**Combined persona test:** Before writing separate Tenant Admin and Tenant User
sections, ask: "Does the Tenant Admin have any capability in this feature that
the Tenant User does not?" If not, combine them under "### Tenant Admin/User"
with a note: "Tenant Admin and Tenant User have the same capabilities in this
scope." This eliminates 3-4 duplicate stories and communicates important scope
information to reviewers. The gold-standard PRDs for OSAC-1332 and OSAC-2872
both use this pattern.
```

### 4.4 generate-prd.md: Add Out of Scope boundary proximity guidance

Current text says:
```
Out of Scope contains 8-15 items at the feature boundary -- items closely related
but deferred. NOT distant, unrelated capabilities that nobody would expect.
```

This guidance is good but the generator still produces distant items. Strengthen it:
```markdown
**Out of Scope boundary test:** For each item, ask: "Would a reviewer
plausibly ask 'is this included?'" If not, the item is too distant. Examples:
- GOOD: "Volume resize" for a storage feature (closely related)
- GOOD: "GPU discovery API" for a GPU InstanceType feature (natural question)
- BAD: "Cross-region storage replication" for a cluster storage feature (nobody
  would expect this in a first storage feature)
- BAD: "Storage performance monitoring" for a storage control plane (unrelated)
```

### 4.5 generate-prd.md: Preserve technology specificity from Jira

Add a new rule:
```markdown
8. **Preserve technology constraints from Jira.** If the Jira source names a
   specific technology standard or compatibility target (e.g., "Vault-compatible
   API," "OCI artifact"), preserve it in the PRD. These are requirement
   constraints, not design leakage -- they tell the design phase which API
   surface to target. Do not abstract away meaningful specificity.
```

### 4.6 review-prd.md: Fix calibration drift

The self-review scores 10/10 on 5 out of 6 generated PRDs in iter2. The iter3 independent review scores them 4.0-4.6/5 on overall quality. This indicates the self-review is still too generous.

Current calibration text:
```
A 10/10 PRD is exceptional -- it means every criterion is perfect with no room
for improvement. Be honest about imperfections.
```

Add stronger calibration:
```markdown
### Score Distribution Targets

A well-calibrated reviewer produces scores matching this distribution:
- 10/10: 10-15% of PRDs (truly exceptional, no improvements possible)
- 9/10: 30-40% of PRDs (strong with one minor imperfection)
- 8/10: 30-40% of PRDs (good with 1-2 areas for improvement)
- 7/10: 10-15% of PRDs (passes but has clear gaps)
- <7/10: 5-10% of PRDs (fails, needs revision)

If you are scoring >80% of PRDs at 10/10, you are not calibrated. Look harder
for imperfections in testability, specificity, or scope boundary quality.

### Common Deductions to Apply

- **Testability at 1 not 2**: AC items that say "follows the same behavior as X"
  without specifying what behavior X is. A PM cannot test by reference.
- **WHAT at 1 not 2**: More than two duplicate user stories across personas
  (stories should be combined, not copied with pronoun changes).
- **Right-Sized at 1 not 2**: OSAC Dimensions section that duplicates the main
  body indicates scope boundary confusion.
```

### 4.7 revise-prd.md: Add source file verification

Add to the critical rules:
```markdown
6. **Verify source content.** Before revising, check that
   `artifacts/prd-tasks/{PRD_ID}-source.md` contains actual Jira content (not
   "(No description)"). If the source is empty, flag this as an issue -- the
   PRD may contain fabricated requirements that cannot be traced to Jira.
```

---

## Section 5: Script Improvements

### 5.1 fetch_feature.py: Fix Jira output parsing

**Critical bug.** The script looks for `line.startswith("Summary:")` and `line.startswith("Description:")` but the `jira issue view --plain` output uses a different format:

```
  # GPU-Enabled InstanceTypes for ComputeInstances (MVP)
  ...
  ------------------------ Description ------------------------
  ## Feature Goal
  Enable OSAC tenants...
```

The actual format uses:
- The first `# Title` line for the summary (after metadata lines)
- `------------------------ Description ------------------------` as a section separator
- `------------------------ Linked Issues ------------------------` as a section separator

The script needs to be rewritten to parse the actual `jira` CLI `--plain` output format. Key changes:

1. Parse the title from the first `#`-prefixed line
2. Parse metadata from emoji-prefixed header lines (e.g., `👷 Dakota Crowder`)
3. Parse description between `Description` and the next section separator
4. Parse linked issues from the `Linked Issues` section

### 5.2 score_prd.py: Add content-based leakage patterns

Current leakage patterns miss several design-leakage terms found in real PRD reviews:

Missing patterns to add:
```python
DESIGN_LEAKAGE_PATTERNS = [
    # ... existing patterns ...
    (r'\bhelm\s+chart\b', 'Helm chart'),
    (r'\bkustomize\b', 'kustomize'),
    (r'\bOLM\b', 'OLM'),
    (r'\bCRD\b(?!\s+field)', 'CRD'),
    (r'\breconcile\s+loop\b', 'reconcile loop'),
    (r'\bwebhook\b', 'webhook'),
    (r'\bgrpc-gateway\b', 'grpc-gateway'),
    (r'\bprotobuf\b', 'protobuf'),
    (r'\binterceptor\b', 'interceptor'),
]
```

However, some of these need careful context handling. "Helm chart" in a Dependencies section is acceptable context. Consider adding a section-aware check that only flags leakage in Problem Statement, In Scope, and User Stories sections, not in Assumptions or Dependencies.

### 5.3 score_prd.py: Add duplicate story detection

Add a new check `check-duplicates` that detects near-duplicate user stories across persona sections. Logic:

```python
def check_duplicates(prd_path: str) -> Dict[str, Any]:
    """Detect near-duplicate user stories across persona sections."""
    content = read_markdown(prd_path)
    stories = re.findall(r'- As a .+?, I want .+? so that .+?\.', content)
    # Normalize: remove persona name, lowercase
    normalized = []
    for story in stories:
        norm = re.sub(r'As a [^,]+,', 'As a PERSONA,', story).lower()
        normalized.append((norm, story))
    # Find duplicates with >80% similarity
    duplicates = []
    for i, (norm_a, orig_a) in enumerate(normalized):
        for j, (norm_b, orig_b) in enumerate(normalized):
            if j <= i:
                continue
            # Simple similarity: shared words / total words
            words_a = set(norm_a.split())
            words_b = set(norm_b.split())
            similarity = len(words_a & words_b) / max(len(words_a | words_b), 1)
            if similarity > 0.8:
                duplicates.append(f"Near-duplicate: '{orig_a[:60]}...' and '{orig_b[:60]}...'")
    return {"pass": len(duplicates) == 0, "issues": duplicates}
```

### 5.4 score_prd.py: Add line count check

The prompt says "Target 40-80 non-blank lines." Add a check:

```python
def check_length(prd_path: str) -> Dict[str, Any]:
    """Check PRD is within target length range."""
    content = read_markdown(prd_path)
    non_blank = len([l for l in content.split("\n") if l.strip()])
    issues = []
    if non_blank > 120:
        issues.append(f"PRD has {non_blank} non-blank lines (target: 40-80). Consider trimming.")
    elif non_blank < 30:
        issues.append(f"PRD has {non_blank} non-blank lines (target: 40-80). May be too sparse.")
    return {"pass": non_blank <= 120, "issues": issues}
```

### 5.5 run_eval.py: Add gold content comparison

The `compare_with_gold` function only compares section headings and persona mentions. Add content-level comparison:

- Extract In Scope bullet items and compare overlap
- Extract Out of Scope bullet items and compare overlap
- Count user stories per persona in both and compare
- Measure length ratio per section, not just overall

### 5.6 fetch_feature.py: Add source content validation

After fetching, validate the source file has actual content:

```python
def validate_source(path: str) -> bool:
    """Check that source file has substantive content."""
    content = Path(path).read_text()
    if "(No description)" in content:
        print(f"WARNING: Source file {path} has no description. "
              f"Jira parsing may have failed.", file=sys.stderr)
        return False
    if len(content.strip().split("\n")) < 10:
        print(f"WARNING: Source file {path} has very little content "
              f"({len(content.strip().split(chr(10)))} lines).", file=sys.stderr)
        return False
    return True
```

---

## Section 6: Context Improvements

### 6.1 Missing exemplar diversity

The exemplar set contains three PRDs:
- OSAC-1269 (ClusterVersion, CaaS, scored 10/10)
- OSAC-2917 (GPU InstanceTypes, VMaaS, scored 9/10)
- OSAC-2872 (Storage Control Plane, CaaS/Storage, scored 9/10)

Missing service coverage:
- **BMaaS**: No BMaaS exemplar. OSAC-1270 (Base OS Management, 10/10) would be an excellent addition.
- **Cross-service**: No exemplar covering all services. OSAC-1567 (Secret Management, all services) would add variety.
- **UI-focused**: No UI-focused exemplar. OSAC-1319 (BareMetal Instance UI, 8/10) would show a different PRD shape.

Recommended additions:
1. Add `context/exemplars/OSAC-1270-prd.md` (BMaaS, 10/10)
2. Add `context/exemplars/OSAC-1567-prd.md` (cross-service, after correcting to gold version)

### 6.2 Rubric calibration gaps

The scoring rubric has detailed calibration examples for each criterion but does not include examples of combined persona handling. Add to the WHAT section:

```markdown
- **W=2 (combined personas)**: "Tenant Admin and Tenant User have the same
  storage capabilities in v0.2. As a Tenant Admin/User, I want to create a PVC
  using a StorageClass named after one of my configured storage tiers..."
  -- correctly identifies when personas share capabilities and combines them.
```

### 6.3 Review patterns missing PR review themes

The `review-patterns.md` file does not include patterns from actual PR review comments. Based on the PR review analysis (Section 9), add these patterns:

```markdown
### Common PR Review Feedback

| Theme | What reviewers ask | Anticipate by |
|-------|-------------------|---------------|
| Lifecycle semantics | "What happens when X is deleted while Y references it?" | Always specify deletion protection behavior for new resources |
| Failure paths | "What does the tenant see when this fails?" | Include failure behavior in In Scope and AC |
| Scope overlap with siblings | "Isn't this already covered by OSAC-XXXX?" | State relationship to sibling features explicitly |
| "Update" ambiguity | "Does update mean in-place modification or delete+recreate?" | Specify which fields are mutable vs immutable |
| Technology specificity | "Why not name the compatibility target?" | Preserve technology constraints from Jira |
| Completed work in scope | "Is OSAC-YYYY already done?" | Do not list completed dependencies as in-scope |
```

### 6.4 Missing context: relationship between features

When the Jira feature references related features (e.g., OSAC-1270 references OSAC-2540), the generator should understand the relationship and scope appropriately. Add a context note:

```markdown
### Feature Relationship Patterns

When a Jira feature explicitly references another feature:
- **"should be unified with"** = scope for independent delivery now, note
  alignment as an assumption
- **"depends on"** = list as a dependency, scope only the new work
- **"is related to"** = note in Related Features, ensure no scope overlap

If the feature is a follow-up/integration of an existing resource (e.g.,
adding DiskImage to BMaaS after DiskImage was created for VMaaS), scope the
PRD to the integration work only. Reference the parent feature for shared
resource behavior.
```

---

## Section 7: Eval Dataset Gaps

### 7.1 No low-scoring test cases

The dataset has 10 cases scoring 8-10/10. All pass the quality threshold. There are no cases testing the generator's behavior on:
- Features that should score low (content-only features, design-as-PRD)
- Features with insufficient Jira content
- Features that need splitting (bundles 3+ capabilities)

Recommended additions:
1. **OSAC-1061 (Resource Names, 5/10)**: A low-scoring PRD that mixes implementation details with requirements. Tests whether the generator avoids the same mistakes.
2. **OSAC-1577 (API Quality, 5/10)**: Another low-scoring PRD that includes completed work as in-scope and has contradictory scope statements. Tests scope discipline.
3. A synthetic case with minimal Jira content (just a title and one-sentence description) to test "TBD" handling.

### 7.2 No cases testing the prd.create skill in isolation

All evaluation runs go through the speedrun pipeline. There is no test of the `prd.create` skill running independently against a fresh Jira issue that is not in the exemplars.

### 7.3 Missing annotation fields

The `annotations.yaml` files lack:
- `key_requirements`: List of requirements that must appear in the generated PRD
- `expected_personas`: Which personas should be affected vs unaffected
- `expected_scope_items`: Critical In Scope items that must appear
- `known_traps`: Design leakage patterns specific to this feature that the generator should avoid

Adding these would enable more targeted evaluation beyond section overlap.

### 7.4 Gold PRDs from different template eras

The OSAC-1269 gold PRD uses numbered sections (1. Problem Statement, 2. Goals and Non-Goals, 3. Requirements) with FR-N/NFR-N requirement IDs. The OSAC-1270 and OSAC-2540 gold PRDs use the newer template (Problem Statement, In Scope, Out of Scope, User Stories). The `find_section` function in `score_prd.py` handles aliases (Goals -> In Scope, Non-Goals -> Out of Scope) but the gold comparison in `run_eval.py` does not normalize these, leading to artificially low section overlap for OSAC-1269.

### 7.5 Missing OSAC-1319 from generated set

OSAC-1319 (BareMetal Instance UI) has a gold PRD in the eval dataset but no generated PRD in `artifacts/prd-tasks/`. This case tests a UI-focused PRD shape that differs from API/backend features. It should be included in evaluation runs.

---

## Section 8: Pipeline Improvements

### 8.1 Source file validation missing

The pipeline fetches Jira content but never validates that the fetch was successful. When `fetch_feature.py` produces "(No description)", the pipeline continues with empty source material. Add a validation step:

```
FETCH → VALIDATE_SOURCE → GENERATE → ...
```

If source validation fails, the pipeline should either:
1. Re-fetch with a different parsing strategy
2. Fall back to reading the Jira issue directly via `jira issue view`
3. Halt with an error rather than generating from empty source

### 8.2 No comparison with Jira source during review

The review phase (`prompts/review-prd.md`) scores the PRD against the rubric but never compares it against the source material. A requirement that appears in the PRD but not in the Jira source is a fabrication. Add a source-traceability check:

```
REVIEW phase should:
1. Read the source file
2. For each In Scope item, verify it appears in or can be inferred from the source
3. Flag items with no source backing as "potential fabrication"
```

### 8.3 No diff between original and revised PRD

The REVISE phase creates a backup in `prd-originals/` but the pipeline never computes or reports the diff. Adding a diff step would make revision quality visible:

```bash
diff artifacts/prd-originals/{PRD_ID}.md artifacts/prd-tasks/{PRD_ID}.md
```

### 8.4 REASSESS cycle limit may be too low

The pipeline limits reassessment to 2 cycles. For complex features, this may not be enough. Consider making it configurable via `--max-reassess N`.

### 8.5 No independent review in pipeline

The pipeline only runs self-review (same model scores its own output). The eval harness has LLM judges for independent evaluation, but the speedrun pipeline does not. Consider adding an optional `--independent-review` flag that runs a second model to score the PRD.

---

## Section 9: Reviewer Feedback Patterns

Based on analysis of PR review comments from enhancement-proposals PRs #74, #124, #132, #134, #135, #150, and #152:

### 9.1 Deletion protection and lifecycle semantics (most common)

Reviewers consistently ask: "What happens when resource X is deleted while resource Y references it?"

- PR #132 (OSAC-2917): "Define retirement and delete behavior for GPU InstanceTypes" and "Define deletion behavior for referenced InstanceTypes"
- PR #135 (OSAC-1270): "Apply deletion protection consistently to global and tenant images" and "Define mandatory after catalog default resolution"
- PR #150 (OSAC-1061): "Reserve names while deletion is pending"

**Generator action:** The OSAC-2540 and OSAC-1270 generated PRDs correctly include deletion protection. This pattern should be codified as a mandatory check: every PRD that introduces a new resource must specify what happens when it is deleted while referenced.

### 9.2 Failure path specification (second most common)

Reviewers ask: "What does the tenant see when this operation fails?"

- PR #132 (OSAC-2917): "Add the GPU failure-path criterion" -- requested explicit tenant-visible behavior when GPU hardware is unavailable
- PR #74 (OSAC-1269): "Acceptance criteria miss two stated mandatory requirements" -- FR-4 and FR-15 not in AC

**Generator action:** The iter2 prompt already includes "What are the failure scenarios?" in the analysis step. The generated PRDs include failure behavior when guided by the exemplars. Strengthen by making failure path a mandatory In Scope item for any provisioning feature.

### 9.3 Scope overlap with sibling features

Reviewers ask: "Isn't this already covered by OSAC-XXXX?"

- PR #135 (OSAC-1270): "Keep OSAC-1270 limited to BMaaS integration" -- reviewer noted that browsing, lifecycle UI, and deprecation warnings duplicate OSAC-2540
- PR #152 (OSAC-1577): "Clarify whether OSAC-1275 is a deliverable or a completed prerequisite"

**Generator action:** When the Jira feature mentions related features, the generator should explicitly state which behaviors are inherited vs newly defined.

### 9.4 Design leakage in PRD

Even human-authored PRDs get flagged:
- PR #74 (OSAC-1269): "Keep the problem statement user-facing" (regex/URL discussion), "Split requirements from schema decisions" (FR-1, FR-2 read like resource shape), "NFRs are too implementation-shaped"
- PR #150 (OSAC-1061): "This is implementation detail and not a PRD concern" (reviewer response to CodeRabbit)

**Generator action:** The generator already handles this well. No action needed.

### 9.5 "Update" ambiguity

- PR #132 (OSAC-2917): Reviewer asked about "update" vs "delete and define new" for InstanceTypes
- PR #135 (OSAC-1270): "Constrain 'update' to mutable DiskImage fields"

**Generator action:** When a user story says "update resource X", specify which fields are mutable. If fields are immutable, use "delete and create new" instead.

### 9.6 Consistency and terminology

- PR #135 (OSAC-1270): "Hyphenate 'bare-metal' consistently"
- PR #74 (OSAC-1269): Multiple clarification questions about version semantics

**Generator action:** Minor. The generator should use consistent hyphenation and define ambiguous terms.

---

## Section 10: Priority-Ordered Action Items

### 1. Fix fetch_feature.py Jira parsing (Critical, Effort: M)

The script fails to parse `jira issue view --plain` output, producing empty source files. This is the single most impactful bug -- without it, the "no fabrication" guarantee is hollow. The generator works from exemplars and context, not from actual Jira content.

**Action:** Rewrite the parser to handle the actual `jira` CLI output format with section separators (`--- Description ---`), emoji-prefixed metadata, and markdown-formatted descriptions.

### 2. Add source content validation to pipeline (Critical, Effort: S)

After fetching, verify the source file has substantive content before proceeding to generation. If empty, halt or retry.

**Action:** Add `validate_source()` to `fetch_feature.py` and a VALIDATE_SOURCE phase to the pipeline.

### 3. Fix self-review score inflation (High, Effort: M)

Self-review scores 10/10 on 83% of PRDs. Independent review scores them 4.0-4.6/5 (roughly 8-9/10 equivalent). The calibration guidance exists but is not strong enough.

**Action:** Add score distribution targets and specific common deductions to the review prompt. Consider adding a "deduction checklist" that the reviewer must explicitly evaluate before scoring.

### 4. Add persona combination logic (High, Effort: S)

The generator creates duplicate user stories for Tenant Admin and Tenant User when they have identical capabilities. Gold PRDs correctly combine them.

**Action:** Strengthen the combination guidance in `generate-prd.md` with an explicit test and gold-standard examples. Add a duplicate story detection check to `score_prd.py`.

### 5. Trim Out of Scope to boundary-adjacent items (Medium, Effort: S)

Generated PRDs include 10-14 Out of Scope items, some too distant from the feature boundary. Gold PRDs have 4-12 items, all closely related.

**Action:** Add a boundary proximity test to the generation prompt. Remove distant items that no reviewer would plausibly ask about.

### 6. Add BMaaS and cross-service exemplars (Medium, Effort: S)

Exemplar set covers only CaaS and VMaaS. BMaaS and cross-service features are underrepresented.

**Action:** Add OSAC-1270 (BMaaS) and OSAC-1567 (cross-service) gold PRDs as exemplars.

### 7. Preserve technology specificity from Jira source (Medium, Effort: S)

The generator abstracts away technology constraints (e.g., "Vault-compatible" becomes "compatible"), losing meaningful requirement constraints.

**Action:** Add rule to `generate-prd.md` to preserve technology names from Jira when they are requirement constraints, not implementation choices.

### 8. Add low-scoring test cases to eval dataset (Medium, Effort: M)

Dataset only has 8-10/10 PRDs. No calibration against low-scoring or failing PRDs.

**Action:** Add OSAC-1061 and OSAC-1577 as test cases with expected scores of 5/10. Add a synthetic minimal-input case.

### 9. Add source traceability to review phase (Medium, Effort: M)

Review phase does not compare generated PRD against Jira source. Cannot detect fabrication.

**Action:** Add source comparison step to review prompt. Flag requirements not traceable to source.

### 10. Eliminate OSAC Dimensions section duplication (Low, Effort: S)

Generated PRDs sometimes create a separate "OSAC Dimensions" section that duplicates the main body.

**Action:** Add explicit "do NOT create a separate OSAC Dimensions section" guidance to the generation prompt.

---

## Appendix: Files Reviewed

### prd-creator system files
- `AGENTS.md`, `PLAN.md`
- `prompts/generate-prd.md`, `prompts/review-prd.md`, `prompts/revise-prd.md`, `prompts/respond-feedback.md`
- `context/prd-template.md`, `context/osac-dimensions.md`, `context/review-patterns.md`, `context/scoring-rubric.md`
- `context/exemplars/OSAC-1269-prd.md`, `OSAC-2917-prd.md`, `OSAC-2872-prd.md`
- `scripts/score_prd.py`, `scripts/run_eval.py`, `scripts/fetch_feature.py`, `scripts/pipeline_state.py`
- `skills/prd.create/SKILL.md`, `skills/prd.speedrun/SKILL.md`, `skills/prd.review/SKILL.md`, `skills/prd.respond/SKILL.md`
- `eval/eval.yaml`, `eval/dataset/cases/*/`

### Generated PRDs (6)
- `artifacts/prd-tasks/OSAC-2917.md`, `OSAC-1270.md`, `OSAC-2540.md`, `OSAC-1332.md`, `OSAC-1567.md`, `OSAC-2872.md`

### Gold PRDs (10)
- `eval/dataset/cases/OSAC-{1269,1270,1319,1332,1567,2540,2872,2917,1110,1330}/gold-prd.md`

### Reviews
- `artifacts/prd-reviews/OSAC-{2917,1270,2540,1332,1567,2872}-review.md`
- `artifacts/prd-reviews/OSAC-{2917,2872,1567}-independent-review.md`
- `eval/results/iter3-independent-review.md`

### PR review comments
- enhancement-proposals PRs: #74, #124, #132, #134, #135, #150, #152

### Jira issues
- OSAC-2917, OSAC-1270, OSAC-1567 (via `jira issue view --plain`)
