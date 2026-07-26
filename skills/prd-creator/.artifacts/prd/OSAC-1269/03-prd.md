---
prd_id: OSAC-1269
title: "ClusterVersion \u2014 Managed Version Catalog for Cluster Provisioning"
jira_key: OSAC-1269
status: Draft
---
# ClusterVersion — Managed Version Catalog for Cluster Provisioning

| Field       | Value   |
|-------------|---------|
| Author(s)   | Ilya Skornyakov |
| Jira        | [OSAC-1269](https://issues.redhat.com/browse/OSAC-1269) |
| Date        | 2026-07-25 |

## Problem Statement

Cluster creation currently requires users to provide a full OCI release image URL (e.g., `quay.io/openshift-release-dev/ocp-release:4.17.0-multi`). This leaks infrastructure details into the user-facing API: users must know exact registry paths and tag formats, typos are caught only at provisioning time rather than at API validation, and there is no way to discover which versions are available, deprecated, or end-of-life. Without a managed version catalog, version validation errors surface late in the provisioning cycle, wasting time and resources on clusters that will never complete.

## In Scope

- Users specify an OpenShift version by number (e.g., "4.17.0") instead of a raw OCI release image URL when creating a cluster
- Users receive immediate, descriptive feedback at API validation time when specifying an invalid, obsolete, or deprecated version — before any provisioning begins
- Cloud Provider Admins create, update, and delete version catalog entries via CLI, API, and UI
- Tenant users browse available versions and select from them when creating clusters
- Version lifecycle states (active, deprecated, obsolete) control visibility and creation eligibility
- Deprecated versions allow cluster creation but surface a warning to users
- Obsolete versions block new cluster creation with a descriptive error
- Deleting a version referenced by active clusters or template defaults is rejected with an error identifying the referencing resource
- Templates can specify a default version; one system-wide default version is supported
- Cluster status displays the version number and its current lifecycle state
- Catalog items reference version instead of release image in field definitions

## Out of Scope

- Cluster upgrade operations, triggering, tracking, or rolling back upgrades (owned by OSAC-1415)
- Channel metadata propagation to hosted clusters (OSAC-1415)
- ACM ClusterImageSet auto-sync — versions are admin-managed in v0.2
- VM image management — separate resource under OSAC-979
- In-place upgrade migration — OSAC does not support in-place upgrades; this feature assumes fresh deployment
- Multi-cluster version policy enforcement (e.g., "all clusters must use versions >= 4.16")
- Version compatibility matrices (e.g., "version 4.17 requires VAST backend 5.x")
- Automatic version catalog population from external sources

## User Stories

### Cloud Provider Admin

- As a Cloud Provider Admin, I want to create version catalog entries by providing a version number and release image URL, so that tenants can create clusters by selecting a version without knowing infrastructure registry paths.
- As a Cloud Provider Admin, I want to mark a version as deprecated or obsolete, so that users are warned before creating clusters with deprecated versions and blocked from using obsolete versions.
- As a Cloud Provider Admin, I want to set one version as the default, so that users and templates can omit the version field and get a known-good default.
- As a Cloud Provider Admin, I want to be prevented from deleting a version that is in use by active clusters or template defaults, so that I cannot break existing resources by removing their version reference.

### Tenant Admin / Tenant User

- As a Tenant User, I want to browse available versions and see their lifecycle state, so that I can choose a supported version for my cluster.
- As a Tenant User, I want to create a cluster by selecting a version number (e.g., "4.17.0"), so that I do not need to know or type release image URLs.
- As a Tenant User, I want to receive a descriptive error at cluster creation time if I select a non-existent or obsolete version, so that I know immediately that my cluster will not provision and can fix the error before wasting time.
- As a Tenant User, I want to see which version my cluster is using and whether it is deprecated or obsolete, so that I can plan upgrades or replacements for clusters on deprecated versions.

### Cloud Infrastructure Admin

Not affected by this feature. Version catalog management is a Cloud Provider Admin responsibility; catalog consumption is a tenant capability.

## Assumptions

- OSAC does not support in-place upgrades. Existing clusters created with release image URLs will not automatically display a version value after the feature lands. Administrators must re-create templates and catalog items with version references.
- No production catalog items exist that reference release image, so the change to version-based selection requires no migration of existing catalog items.

## Dependencies

- **OSAC-1531 (Default Catalog Items):** Default version catalog entries should ship alongside default catalog items. Version catalog population is a prerequisite for catalog items that reference version-based clusters.
