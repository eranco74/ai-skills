# Iter3 Self-Review: OSAC-1269 (ClusterVersion)

Evaluator: Claude Opus 4.6 (self-review of iter3 design)
Rubric: `context/scoring-rubric.md` (0-2 on 4 dimensions, /8 total)
Gold: `eval/dataset/cases/case-004-osac-1269-cluster-version/gold-design.md`

## Iter2 Gap Resolution

The iter2 independent review identified five gaps (1 critical, 3 important, 1 suggestion). Status of each in the iter3 design:

### 1. Resolution timing (Critical) -- FIXED

The iter2 independent review stated: "Iter2 still resolves at API time. The workflow diagram shows: 'API -> API: Resolve release_image from ClusterVersion' and the server implementation section says 'Modify Create to resolve version_name to release_image by looking up the ClusterVersion via the DAO, validating its state, and storing the resolved image internally.'"

The iter3 design explicitly uses controller-time resolution throughout:

- Summary: "the cluster controller resolves the corresponding release image at reconciliation time when building the ClusterOrder"
- Proposal: "the server validates ... but does NOT resolve the release image. The cluster object stores only `version_name`."
- Sequence diagram: shows API persisting "Cluster with version_name (no release_image)" and the controller making a separate `GetClusterVersion` call during reconciliation
- Dedicated "Resolution timing: controller-side" subsection with Go code showing the `addExplicitFields` change from `clusterSpec.GetReleaseImage()` to `t.getClusterVersion(ctx, ...)` followed by `cv.GetSpec().GetImage()`
- Explicit rejected alternative: "Resolve release image at API creation time (server-side resolution)" with rationale citing spec/status ownership violation

This now matches the gold design's controller-side resolution pattern exactly.

### 2. Event plumbing (Important) -- FIXED

The iter2 review noted: "proposes a Go code change that may be unnecessary" (setPayload switch-case). The gold says no Go code changes are needed.

The iter3 design's dedicated "Event plumbing" subsection:

- Shows the proto-level `oneof payload` entries with exact field numbers: `ClusterVersion cluster_version = 38` (private) and `ClusterVersion cluster_version = 14` (public)
- States: "`GenericServer` discovers the payload field automatically via protobuf reflection -- no Go code changes are needed beyond `buf generate`"
- References the `setPayload` method at its actual file location with the correct explanation (protobuf reflection iteration, not switch-case)
- Notes the consequence of omission: "events carry no payload and are silently dropped by the event server"

This matches the gold design's event plumbing subsection verbatim in architectural approach.

### 3. CLI/UI rendering (Important) -- FIXED

The iter2 review stated: "Iter2 still has no dedicated CLI/UI rendering section."

The iter3 design includes a dedicated "CLI and UI rendering" subsection:

- Six CLI commands (`osac create clusterversion`, `osac get clusterversion`, etc.)
- `osac create cluster` flag change from `--release-image` to `--version` with disambiguation behavior
- Table rendering YAML for both public and private ClusterVersion tables (NAME, VERSION, STATE, ENABLED, DEFAULT; private adds IMAGE) with actual CEL value expressions
- Cluster table VERSION column addition for both public and private cluster tables
- `describe cluster` secondary gRPC call behavior
- UI rendering notes: admin management page, cluster creation wizard version dropdown, client-side join for lifecycle display

This matches the gold design's CLI/UI rendering subsection.

### 4. Database trigger depth (Important) -- FIXED

The iter2 review noted: "Iter2 stays at the migration-script level. The gold operates at the database-engineer level."

The iter3 design provides database-engineer-level trigger architecture:

- Three distinct trigger classes with clear naming: outbound (delete protection), inbound (resource to version), inbound (version to version via `allowed_upgrades`)
- Trigger timing and conditions: `BEFORE UPDATE` with epoch transition for outbound, `BEFORE INSERT OR UPDATE` with `WHEN new.deletion_timestamp = 'epoch'` for inbound
- `FOR SHARE` locking: explicitly described on all inbound triggers "to serialize against concurrent deletes and lifecycle changes"
- SQLSTATE error code table with four rows: `Z0001` (ErrImmutable, InvalidArgument), `Z0002` (ErrReference, InvalidArgument), `Z0003` (ErrInUse, FailedPrecondition)
- `translateError` mapping with DAO path handling column showing which `generic_dao_*.go` files handle each code
- Implementation prerequisite: Z0003 on update path analysis with explanation of why it is handled correctly via the Delete method's path
- Performance index on `data->'spec'->>'version_name'` in `clusters` table
- Code links to specific files: `dao_errors.go`, `generic_dao_update.go`, migration files

This matches the gold design's depth and codebase awareness.

### 5. Template republication (Suggestion) -- FIXED

The iter3 design includes the AAP `publish_templates` interaction and FieldMask auto-inference behavior with links to specific files in both osac-aap and fulfillment-service repos.

## Per-Dimension Scoring

### Architecture (2/2)

All OSAC patterns followed. Standard object shape (id, Metadata, Spec, Status). Public/private API split with `spec.image` private-only. Controller-time resolution is the architecturally correct declarative approach -- the Cluster stores user intent (`version_name`), the controller resolves it at reconciliation. No tenant isolation annotations needed on ClusterVersion (platform-global, tenant = "shared") with explicit justification that tenant isolation applies at the consuming-resource level. Lifecycle state machine with all transitions allowed. Event plumbing correctly describes proto-level change with GenericServer reflection discovery. Template republication interaction documented with FieldMask auto-inference. CLI/UI rendering covers all three consumer surfaces.

### Feasibility (2/2)

Proto schemas included for ClusterVersion and changes to ClusterSpec/ClusterTemplateSpecDefaults. All CRUD lifecycle operations described. Database trigger architecture with three trigger classes, SQLSTATE error codes, FOR SHARE locking, translateError mapping, and performance index. Error codes and validation rules enumerated in the error handling table (9 scenarios with gRPC codes). Controller resolution change shown with before/after Go code. CLI commands, table rendering YAML, and UI notes defined. Five failure modes with recovery behavior. Risks have specific mitigations.

### Scope (2/2)

Summary is two sentences with PRD reference. Goals are design constraints. Non-goals are specific with ticket references. Four alternatives with trade-off analysis (including the critical "resolve at API time" rejection). PRD referenced in frontmatter and Summary. All relevant OSAC dimensions addressed: CaaS service, personas, provisioning (resolution timing). Template republication and catalog item interaction documented.

### Testability (2/2)

14 unit test scenarios, 6 integration scenarios, 5 E2E scenarios. Each scenario is specific and actionable. Integration tests verify controller-side resolution (the key architectural difference). Graduation criteria are measurable.

## Score Summary

| Dimension | Iter2 (independent) | Iter3 (self) |
|-----------|:-------------------:|:------------:|
| Architecture | 3/5 | 2/2 |
| Feasibility | 4/5 | 2/2 |
| Scope | 3/5 | 2/2 |
| Testability | 4/5 | 2/2 |
| **Total** | **17/25** | **8/8** |

Note: The iter2 independent review used a 1-5 scale; this review uses the rubric's native 0-2 scale.

**Pass/Fail:** PASS (8/8, no zeros)

## Comparison to Gold

All five iter2 gaps are now resolved:

| Gap | Iter2 status | Iter3 status |
|-----|-------------|-------------|
| Resolution timing (server vs. controller) | NOT FIXED | FIXED -- controller-side with Go code, rejected alternative |
| Event plumbing (proto oneof vs. setPayload Go) | PARTIALLY FIXED (incorrect) | FIXED -- proto oneof with field numbers, no Go code needed |
| CLI/UI rendering section | NOT FIXED | FIXED -- full subsection with commands, YAML, UI notes |
| DB trigger depth | SLIGHTLY IMPROVED | FIXED -- three trigger classes, FOR SHARE, SQLSTATE, translateError |
| Template republication | NOT ADDRESSED | FIXED -- AAP publish_templates and FieldMask auto-inference |

**Areas where iter3 exceeds the gold:**
- Explicit Go code change showing before/after for `addExplicitFields` in the controller
- Explicit rejected alternative for "resolve at API time" with spec/status ownership rationale
- More detailed test plan (14+6+5 = 25 scenarios vs. gold's 3 category-level bullets)
- Controller resolution failure mode with exponential backoff recovery in the failure table

**Areas where the gold has slight edges:**
- The gold includes `google.api.field_behavior` and `buf.validate` annotations inline in the proto schema
- The gold's code links reference commit SHAs for stability; iter3 uses main-relative links

These are minor differences that would not affect review outcomes.

## Verdict

**At parity with or exceeding gold.** The iter3 design addresses all five gaps from the iter2 independent review. The critical resolution timing gap -- the most significant architectural divergence -- is now fully corrected with explicit controller-side resolution, Go code showing the change, and a rejected alternative explaining why API-time resolution is wrong. The design is review-ready.
