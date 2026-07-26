# Independent Design Evaluation: OSAC-1269 (ClusterVersion)

Generated: `artifacts/design-tasks/OSAC-1269-design.md`
Gold: `eval/dataset/cases/case-004-osac-1269-cluster-version/gold-design.md`

## Summary Scores

| Dimension              | Score (1-5) | Notes |
|------------------------|:-----------:|-------|
| Architecture Quality   | 3           | Core patterns followed; resolution timing and event plumbing gaps |
| Proto Schema Quality   | 4           | More detailed annotations than gold; minor field-number and deprecation-vs-removal differences |
| Scope Completeness     | 3           | Missing CLI/UI rendering, event plumbing, and detailed DB trigger subsections |
| Test Plan Quality      | 4           | Exceeds gold in specificity; concrete scenarios at every test level |
| Overall Quality        | 3           | Competent first draft; would need revisions to pass review |

**Total: 17/25**

## Top 3 Gaps vs Gold

### 1. Resolution timing: server-side at creation vs. controller at reconciliation

The most significant architectural divergence. The generated design resolves `version_name` to `release_image` at cluster creation time in the server and "stores the resolved image internally." The gold design keeps `version_name` as the only field on the Cluster object and defers resolution to the cluster controller at reconciliation time, where it fetches the ClusterVersion and passes the image to the ClusterOrder.

The gold approach is architecturally cleaner: the Cluster object declares intent (`version_name`), the controller resolves it -- consistent with the declarative reconciliation model used throughout osac-operator. The generated approach conflates API validation with resolution, making the Cluster object carry both the reference and the resolved value.

### 2. Missing event plumbing and CLI/UI rendering sections

The gold design has two dedicated subsections absent from the generated design:

- **Event plumbing** -- the gold explains that `ClusterVersion` needs an entry in the `oneof payload` of event type protos so CRUD operations emit change notifications. Without this, events carry no payload and are silently dropped. The generated mentions `setPayload()` but never discusses the event proto changes.
- **CLI and UI rendering** -- the gold specifies exact CLI commands (`osac create clusterversion`, `osac get clusterversions`, etc.), table columns (NAME, VERSION, STATE, ENABLED, DEFAULT), describe behavior (secondary gRPC call to fetch version details), and UI rendering notes. The generated design has none of this.

These sections are important for implementer guidance and cross-team coordination.

### 3. Database trigger design depth and codebase awareness

The gold design demonstrates deep codebase knowledge that the generated design lacks:

- **Trigger architecture**: Gold specifies three distinct trigger classes (outbound delete-protection, inbound resource-to-version, inbound version-to-version via allowed_upgrades) with `FOR SHARE` locking to serialize against concurrent deletes.
- **SQLSTATE error codes**: Gold maps specific codes (`Z0001` immutable, `Z0002` invalid reference, `Z0003` delete blocked) and documents how they translate to gRPC status codes.
- **Implementation prerequisite**: Gold identifies a pre-existing gap -- `translateError` in `generic_dao_update.go` does not translate `Z0002`/`Z0003` on the update path, which must be fixed before inbound triggers can return proper gRPC errors. This shows deep codebase analysis the generated missed.
- **Performance index**: Gold adds a JSONB index on `data->'spec'->>'version_name'` in the `clusters` table for efficient delete-protection scans.
- **Code links**: Gold references specific files and line numbers (e.g., `catalog_item_validation.go#L73`, `generic_dao_update.go#L207`).

The generated design has a competent migration section but stays at a higher level of abstraction.

## Top 3 Strengths

### 1. Proto schema detail exceeds gold

The generated design includes `google.api.field_behavior` annotations (REQUIRED, IMMUTABLE, OPTIONAL, OUTPUT_ONLY) and `buf.validate` annotations on `allowed_upgrades` that the gold design omits. It also provides the full service proto with REST transcoding routes, which the gold does not include. This level of proto detail would accelerate implementation.

### 2. Comprehensive error path enumeration

The generated design lists 10 specific error scenarios with exact gRPC status codes and user-facing error messages (e.g., "ClusterVersion '4.16.0' is obsolete; use an active version"). The failure handling table covers 8 failure modes with behavior, user observation, and recovery steps. The gold design's error table is shorter (7 scenarios) and less specific about error messages.

### 3. Test plan specificity

The generated test plan is significantly more detailed than the gold's. It lists specific unit test scenarios (13 items including auto-generated name verification, state transition timestamp behavior, allowed_upgrades self-reference rejection), 6 integration test scenarios, and 5 E2E scenarios. The gold design's test plan has only 3 bullet points listing categories without specific scenarios. The generated also includes more concrete graduation criteria.

## Other Notable Differences

- **release_image deprecation vs. removal**: The generated retains `release_image` as deprecated for backward compatibility. The gold removes it outright, noting that v0.2 assumes coordinated fresh deployment with no migration needed. The gold's approach is cleaner -- the backward compatibility concern is unnecessary given the deployment model.
- **Mermaid diagrams**: The generated has 3 sequence diagrams plus a component diagram (4 total). The gold has 1 sequence diagram plus 1 state machine diagram. The generated's workflow diagrams are more thorough; the gold's state machine diagram is more valuable for lifecycle documentation.
- **Terminology section**: The generated includes an explicit terminology table that the gold lacks. This is a useful addition.
- **Alternatives section**: The generated provides 4 alternatives with detailed pros/cons analysis. The gold has 3 alternatives. Both are substantive.
- **Template republication**: The gold explicitly addresses AAP `publish_templates` interaction and FieldMask auto-inference behavior. The generated does not mention this.
- **Catalog item field definition validation**: The gold describes `applyFieldDefinitions()` interaction and server-side validation of `version_name` defaults on catalog item create/update. The generated mentions catalog items but with less specificity.

## Verdict

**Slightly worse.**

The generated design is a competent first draft that follows OSAC patterns and provides strong proto schema detail and test planning. However, it falls short of gold in three critical areas: (1) the resolution timing decision reveals a less thoughtful architectural model, (2) missing CLI/event sections leave implementers without key guidance, and (3) the database design lacks the depth and codebase awareness that distinguishes a reviewable design from a draft. A reviewer would likely request revisions on the resolution model and the missing sections before approving.
