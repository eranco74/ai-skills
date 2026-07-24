# Iter2 Independent Design Evaluation

Evaluator: Claude Opus 4.6 (independent, no access to generator prompts)
Rubric: `context/scoring-rubric.md` (0-2 on 4 dimensions; mapped to 1-5 scale per request)

## Summary Table

| Dimension              | OSAC-1269 (ClusterVersion) | OSAC-1567 (Secret Management) |
|------------------------|:--------------------------:|:-----------------------------:|
| Architecture Quality   | 3                          | 4                             |
| Proto Schema Quality   | 4                          | 4                             |
| Scope Completeness     | 3                          | 4                             |
| Test Plan Quality      | 4                          | 4                             |
| Overall Quality        | 3                          | 4                             |
| **Total**              | **17/25**                  | **20/25**                     |

## OSAC-1269 (ClusterVersion): Iter1 Gap Check

The iter1 review identified four gaps. Status of each in iter2:

### 1. Resolution timing: server-side at creation vs. controller at reconciliation -- NOT FIXED

The gold design states: "the cluster controller resolves the release image from the
ClusterVersion when building the ClusterOrder -- the Cluster object itself stores only
the version_name, not the release image." The gold sequence diagram shows the controller
making a separate `GetClusterVersion` call during reconciliation.

Iter2 still resolves at API time. The workflow diagram shows: "API -> API: Resolve
release_image from ClusterVersion" and the server implementation section says "Modify
Create to resolve version_name to release_image by looking up the ClusterVersion via the
DAO, validating its state, and storing the resolved image internally."

This is the same architectural divergence as iter1. The gold's controller-side resolution
is more consistent with the declarative reconciliation model used throughout
osac-operator. Server-side resolution also means that if a ClusterVersion's image is
corrected (via delete + recreate), existing clusters cannot pick up the fix without
updating each cluster -- whereas controller-side resolution would re-resolve on the next
reconciliation.

### 2. Missing event plumbing -- PARTIALLY FIXED

Iter2 mentions the `setPayload()` switch statement change in generic_server.go:
"Add case *publicv1.ClusterVersion and case *privatev1.ClusterVersion to the
setPayload() switch statement." However, this is incorrect per the gold.

The gold's dedicated "Event plumbing" section explains: "ClusterVersion needs an entry
in the oneof payload of both the private and public event type protos so that create,
update, and delete operations emit change notifications with the resource attached. The
GenericServer discovers the payload field automatically via protobuf reflection -- no Go
code changes are needed beyond buf generate. Without the oneof entries, CRUD operations
still succeed, but emitted events carry no payload and are silently dropped by the event
server."

Iter2 mentions the Go code change (setPayload switch) but misses the actual critical
change: the proto-level `oneof payload` entries in event type protos. This suggests the
generator does not fully understand the event dispatch mechanism. The gold says no Go
code changes are needed beyond `buf generate`; the generated proposes a Go code change
that may be unnecessary.

### 3. Missing CLI/UI rendering -- NOT FIXED

Iter2 still has no dedicated CLI/UI rendering section. The graduation criteria mention
"CLI supports version catalog management and cluster creation with --version-name" but
provide no detail on:
- CLI commands (e.g., `osac create clusterversion`, `osac get clusterversions`)
- Table rendering columns (NAME, VERSION, STATE, ENABLED, DEFAULT for public; IMAGE added for private)
- `describe cluster` behavior (secondary gRPC call to fetch version details)
- UI rendering notes (two API calls, client-side join)

The gold design has all of this in a structured subsection. This is important for
implementer guidance and cross-team coordination with CLI/UI teams.

### 4. Shallower database triggers -- SLIGHTLY IMPROVED

Iter2 now mentions:
- CHECK constraints for version and image
- Three unique indexes (name, spec.version, single default)
- `check_immutable_columns` trigger
- `check_immutable_data_fields` trigger for JSONB field immutability
- A separate migration for allowed_upgrades referential integrity

This is an improvement over iter1. However, the gold design goes significantly deeper:
- Three distinct trigger classes (outbound delete-protection, inbound resource-to-version, inbound version-to-version) with detailed descriptions
- `FOR SHARE` locking to serialize against concurrent deletes
- SQLSTATE error code mapping (Z0001/Z0002/Z0003 -> gRPC codes)
- Identification of a pre-existing gap: `translateError` in `generic_dao_update.go` does not translate Z0002/Z0003 on the update path
- Performance index on `data->'spec'->>'version_name'` in the clusters table
- Code links to specific files and line numbers (e.g., `catalog_item_validation.go#L73`, `generic_dao_update.go#L207`)

Iter2 stays at the migration-script level. The gold operates at the database-engineer
level, demonstrating codebase-aware trigger design.

## OSAC-1269: Per-Dimension Reasoning

**Architecture (3):** Core OSAC patterns followed: standard object shape, public/private
API split, generic server/DAO, tenant isolation via platform-scoped convention, proper
state machine for lifecycle. The resolution timing divergence is a meaningful
architectural choice that differs from the gold's more idiomatic controller-side
approach. Event plumbing mentioned but incorrectly (proposes setPayload Go change
instead of proto oneof). No dedicated CLI/UI section means the design omits guidance for
two out of three consumer surfaces (API is covered, CLI and UI are not). Component
interaction diagram is present and accurate.

**Proto Schema (4):** Exceeds the gold in annotation detail: `google.api.field_behavior`
annotations (REQUIRED, IMMUTABLE, OPTIONAL, OUTPUT_ONLY) and `buf.validate` constraints
on `allowed_upgrades`. Full service proto with REST transcoding routes is included, which
the gold omits. Both public and private type variants are clearly distinguished.
`ClusterVersionSpec` field numbering is well-chosen with image at field 1 (reserved in
public). Minor issue: double `field_behavior` annotation on `spec.version` field (both
REQUIRED and IMMUTABLE) -- both are valid but uncommon to see together.

**Scope Completeness (3):** Summary, motivation, goals, and non-goals are well-defined.
Non-goals are specific (upgrade operations, ACM sync, VM images, CRD/operator). Four
alternatives with detailed pros/cons. Terminology table is a positive addition absent
from the gold. However, missing CLI/UI rendering and incomplete event plumbing leave two
important cross-cutting concerns unaddressed. The gold's template republication analysis
(AAP `publish_templates` and FieldMask auto-inference) is also absent.

**Test Plan (4):** Significantly more detailed than the gold: 13+ unit test scenarios, 6
integration scenarios, 5 E2E scenarios. Each scenario is specific and actionable (e.g.,
"Reject update attempts on spec.version, spec.image, and metadata.name with
INVALID_ARGUMENT"). Graduation criteria are measurable ("All CRUD operations pass
integration tests. Version resolution in cluster creation works end-to-end."). The gold's
test plan has only 3 category-level bullet points.

**Overall (3):** A competent design that would need revisions before approval. The
persistent resolution timing gap and missing CLI/UI section would trigger reviewer
requests. The proto detail and test planning are strengths that exceed the gold.

## OSAC-1567 (Secret Management): Per-Dimension Reasoning

**Architecture (4):** Sound two-backend architecture with clear separation of metadata
(PostgreSQL) and data (Vault/Hub). Three authentication paths are well-described with
appropriate scope for each. Per-tenant Vault namespace isolation is correctly motivated
and designed. GenericServer integration is explicit, including `SetRedactFunc` for event
payloads and `setPayload()` switch case. Secret reference model with deprecation of
inline fields is comprehensive (7 resource fields across 5 resource types). Tenant
namespace lifecycle integrated into onboarding/offboarding controller.

Compared to gold: the generated adds explicit event plumbing (field number 40 in oneof),
table rendering YAML, and more structured configuration flags. The gold has slightly more
detail on network requirements across cluster boundaries and an extensibility note for
future OAuth 2.0 consumers (e.g., AAP/Ansible). Both are strong; the generated is at
parity or slightly ahead on implementation specificity.

**Proto Schema (4):** Full proto schemas for both type and service, including
request/response message definitions with field numbers. The gold's service proto is
more compact (lists RPCs without full message definitions). Both correctly separate
public/private variants. The `data` field as `map<string, bytes>` matches Kubernetes
conventions. The generated includes HTTP transcoding annotations on the service RPCs;
the gold does not. Secret proto omits `status` field with a justified explanation
(no async lifecycle).

**Scope Completeness (4):** Covers all relevant personas (Cloud Infrastructure Admin,
Tenant User, system/controller). Workflow descriptions include all four paths (admin
config, user CRUD, secret references, automatic creation). Non-goals are specific (no
rotation, no UI, no store deployment, no per-project Vault policies). Four alternatives
with substantive rejection rationale. UX alignment correctly deferred. CLI commands
table is comprehensive. Credential migration is thoroughly described with idempotency
guarantees. The gold includes a "full backwards compatibility" alternative that the
generated omits -- but this is a minor difference.

**Test Plan (4):** Structured across all three levels with specific scenarios. Unit tests
cover 10 areas including backend dispatch, failure handling, and migration idempotency.
Integration tests cover 9 scenarios including JWT auth paths, token caching, and
credential resolution. E2E tests cover 3 scenarios. The gold's E2E section has only 1
scenario (automatic creation during provisioning); the generated adds CRUD lifecycle and
tenant isolation E2E tests. Graduation criteria are concise and measurable.

**Overall (4):** A strong design that is competitive with the gold. Architecture is sound,
proto schemas are detailed, scope is comprehensive, and test planning is solid. The main
areas where the gold edges ahead are: (1) network requirements section detail for
multi-cluster deployments, (2) extensibility for future consumers via OAuth 2.0 client
credentials, and (3) more nuanced framing of the Keycloak trust model compromise. None
of these gaps would likely block approval -- the generated design is review-ready.

## Top Improvements from Iter1 to Iter2

1. **OSAC-1567 added as second case**: Iter1 only evaluated OSAC-1269. The OSAC-1567
   generated design is a strong result, scoring 20/25 and demonstrating parity with
   the gold on a complex multi-backend architecture.

2. **OSAC-1269 database migration detail**: Iter2 now includes CHECK constraints,
   three unique index definitions, and both column-level and JSONB-level immutability
   triggers. Iter1 had a "competent migration section" but fewer specifics.

3. **OSAC-1269 error handling**: The failure handling table remains comprehensive (8
   failure modes with behavior, user observation, recovery). This was already a strength
   in iter1 and is maintained.

## Remaining Gaps (OSAC-1269)

| Gap | Severity | Status |
|-----|----------|--------|
| Resolution timing (server vs. controller) | Critical | Not fixed -- same architectural divergence |
| Event plumbing (proto oneof vs. setPayload Go code) | Important | Partially addressed but incorrectly |
| CLI/UI rendering section | Important | Not fixed -- still absent |
| DB trigger depth (FOR SHARE, SQLSTATE mapping, translateError gap, performance index, code links) | Important | Slightly improved but still shallow vs. gold |
| Template republication (AAP publish_templates interaction) | Suggestion | Not addressed |

## Verdict

**OSAC-1269:** Slightly worse than gold (same assessment as iter1). The total score
(17/25) is unchanged. The resolution timing gap and missing CLI/UI section are the
primary differentiators. The design would need at least one revision round to pass
review.

**OSAC-1567:** Near parity with gold. The generated design is comprehensive, architecturally
sound, and implementation-ready. Minor gaps (network requirements, extensibility note)
would not block approval. This is a strong result for the generator.
