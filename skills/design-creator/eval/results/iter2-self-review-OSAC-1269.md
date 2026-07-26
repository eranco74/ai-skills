# Iter2 (Regenerated) Self-Review: OSAC-1269 (ClusterVersion)

Evaluator: Claude Opus 4.6 (self-review of regenerated design)
Rubric: `context/scoring-rubric.md` (0-2 on 4 dimensions, /8 total)
Gold: `eval/dataset/cases/case-004-osac-1269-cluster-version/gold-design.md`

## Iter1 Gap Resolution

The iter1 independent review identified four gaps. Status of each in the regenerated design:

### 1. Resolution timing -- FIXED

The regenerated design explicitly uses controller-time resolution. Key evidence:

- Summary states: "The cluster controller resolves release images at reconciliation time, keeping the Cluster object declarative."
- The "Controller-time resolution" subsection describes the 4-step controller flow: read `version_name` from Cluster spec, call `GetClusterVersion`, extract `spec.image`, pass to ClusterOrder.
- The sequence diagram shows the controller making a separate `GetClusterVersion` call during reconciliation, not the API server resolving at creation time.
- The Cluster proto schema stores `version_name` only; no resolved image field.
- The "Resolve release image at API time" approach is explicitly listed as a rejected alternative with rationale (conflates intent with resolution, breaks declarative pattern).

This matches the gold design's approach.

### 2. Event plumbing -- FIXED

The regenerated design has a dedicated "Event plumbing" subsection that:

- States `ClusterVersion` needs entries in the `oneof payload` of both private and public event type protos.
- References the actual field numbers from the codebase: `ClusterVersion cluster_version = 38` (private) and `ClusterVersion cluster_version = 14` (public).
- Explains that `GenericServer` discovers the payload field via protobuf reflection in `setPayload` -- no Go code changes needed beyond `buf generate`.
- Notes the consequence of omitting the entries: events carry no payload and are silently dropped.

This matches the gold design's event plumbing subsection.

### 3. CLI/UI rendering -- FIXED

The regenerated design has a dedicated "CLI and UI rendering" subsection covering:

- Six CLI commands (`osac create clusterversion`, `osac get clusterversion`, etc.).
- `osac create cluster` flag change from `--release-image` to `--version`.
- Table rendering columns: private (NAME, VERSION, STATE, ENABLED, DEFAULT, IMAGE) and public (same minus IMAGE), referencing the actual YAML files in `internal/rendering/tables/`.
- `describe cluster` secondary gRPC call to fetch version details.
- UI rendering: admin management page, cluster creation wizard version dropdown, detail page client-side join.

This matches the gold design's CLI/UI rendering subsection.

### 4. Database trigger depth -- FIXED

The regenerated design provides detailed trigger architecture:

- Three trigger classes: outbound delete-protection, inbound resource-to-version, inbound version-to-version via allowed_upgrades.
- `FOR SHARE` locking on referenced rows for serialization against concurrent operations.
- SQLSTATE error code table: Z0001 (ErrImmutable), Z0002 (ErrReference), Z0003 (ErrInUse), Z0004 (ErrAlreadyExists).
- `translateError` mapping from SQLSTATE to gRPC codes.
- Implementation prerequisite: `translateError` in `generic_dao_update.go` does not handle Z0003 on the update path.
- Performance: JSONB index on `data->'spec'->>'version_name'` in `clusters` table.
- Codebase references: `internal/database/migrations/74_create_cluster_versions_tables.up.sql`, `internal/database/migrations/81_add_cluster_version_allowed_upgrades_ref_trigger.up.sql`, `internal/database/dao/dao_errors.go`, `internal/database/dao/generic_dao_update.go`.

This matches the gold design's depth and codebase awareness.

### Bonus: Template republication -- FIXED

The regenerated design addresses the AAP `publish_templates` interaction and FieldMask auto-inference behavior that the iter1 review noted as a suggestion-level gap. It references the specific files in osac-aap and fulfillment-service.

## Per-Dimension Scoring

### Architecture (2/2)

**Reasoning:** All OSAC patterns followed. Standard object shape (id, Metadata, Spec, Status). Public/private API split with `spec.image` private-only. Controller-time resolution is the correct declarative approach -- the Cluster stores intent (`version_name`), the controller resolves it. No tenant isolation annotations needed on ClusterVersion (platform-global, tenant = "shared") with explicit justification. Lifecycle state machine with all transitions allowed. Cross-repo impact enumerated (fulfillment-service only for v0.2, with osac-ui noted for proto type changes). Event plumbing subsection correctly describes the proto-level change. Template republication interaction documented.

No gaps. Dependencies clear, integration well-described, terminology consistent throughout.

### Feasibility (2/2)

**Reasoning:** Proto schemas included for ClusterVersion and changes to ClusterSpec/ClusterTemplateSpecDefaults. All CRUD lifecycle operations described (create, get, list, update, delete). Detailed database trigger architecture with three trigger classes, SQLSTATE error codes, FOR SHARE locking, and the translateError prerequisite gap. Error codes and validation rules enumerated in the error handling table (8 scenarios with gRPC codes). CLI commands and table rendering defined. Specific failure modes with recovery behavior (5 entries in the failure table). Alternative "resolve at API time" explicitly rejected with concrete rationale. Risks have specific mitigations (seeded versions, coordinated deployment, translateError fix).

No hand-waving. Implementation details are specific to file paths and line numbers.

### Scope (2/2)

**Reasoning:** Summary is concise (2 sentences with PRD reference). Goals are design constraints (replace raw input, resolve at controller time, preserve upgrade model). Non-goals are specific with ticket references (OSAC-1415, OSAC-979). Four alternatives with trade-off analysis. PRD referenced in frontmatter and Summary. All relevant dimensions addressed: CaaS service, Cloud Provider Admin and Tenant User personas, provisioning (version resolution at reconciliation), no changes to networking/storage/installation/tenant onboarding. CLI/UI sections cover the relevant rendering surfaces.

### Testability (2/2)

**Reasoning:** Test plan specifies concrete scenarios at each level: 11 unit test scenarios (SemVer validation, auto-generated names, state transitions, immutability, version resolution precedence, event payload), 6 integration scenarios (end-to-end flow, delete protection, default fallback, controller resolution, concurrent default race, catalog items), 5 E2E scenarios (admin + tenant workflow, deprecation visibility, delete rejection, default application, listing behavior). Graduation criteria are measurable (stable creation, correct resolution, operational docs).

## Score Summary

| Dimension | Score |
|-----------|:-----:|
| Architecture | 2 |
| Feasibility | 2 |
| Scope | 2 |
| Testability | 2 |
| **Total** | **8/8** |

**Pass/Fail:** PASS (8/8, no zeros)

## Comparison to Gold

The regenerated design is now closely aligned with the gold on all four previously-identified gaps:

1. **Controller-time resolution**: Both designs store `version_name` only on the Cluster and resolve at reconciliation time.
2. **Event plumbing**: Both designs describe the proto-level `oneof payload` change with GenericServer reflection discovery.
3. **CLI/UI rendering**: Both designs include commands, table columns, describe behavior, and UI rendering notes.
4. **Database trigger depth**: Both designs describe three trigger classes with FOR SHARE locking, SQLSTATE codes, translateError mapping, and the pre-existing Z0003 gap.

**Areas where this design exceeds the gold:**
- More detailed error handling table (8 scenarios vs. 7).
- More specific test plan (11+6+5 scenarios vs. 3 bullet points).
- Explicit alternative for "resolve at API time" (rejected) -- the gold does not explicitly reject this approach as an alternative, though it implements the controller approach.

**Areas where the gold still has slight edges:**
- The gold includes `google.api.field_behavior` and `buf.validate` annotations in the proto schema; the regenerated design uses comments instead.
- The gold's catalog item field definition validation mentions `applyFieldDefinitions()` at a specific line number; the regenerated mentions it but the line number reference may differ from current main.

These are minor differences that would not affect review outcomes.

## Verdict

**At parity with gold.** The regenerated design addresses all four gaps identified in the iter1 independent review. It follows the correct architectural approach (controller-time resolution), includes all missing subsections (event plumbing, CLI/UI rendering), and provides codebase-aware database trigger design with SQLSTATE codes and the translateError prerequisite. The design is review-ready.
