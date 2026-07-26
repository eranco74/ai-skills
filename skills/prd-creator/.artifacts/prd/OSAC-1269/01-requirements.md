# OSAC-1269: Managed Cluster Versions

## Metadata

- **Status**: In Progress
- **Priority**: Critical
- **Assignee**: Ilya Skornyakov
- **Reporter**: Elad Tabak
- **Components**: CaaS
- **Labels**: None

## Description

Cluster creation currently requires users to provide a full OCI release image URL (e.g., quay.io/openshift-release-
  dev/ocp-release:4.17.0-multi ). This leaks infrastructure details into the user-facing API — users must know exact
  registry paths and tag formats, typos are caught only at provisioning time, and there is no way to discover which
  versions are available, deprecated, or end-of-life.

  This feature introduces a managed list of cluster versions. Users select a version by number (e.g., "4.17.0")
  instead of pasting URLs. The platform resolves the image internally, validates the version's lifecycle state before
  provisioning begins, and prevents deletion of in-use versions.

  **What this enables:**

  • Tenants create clusters self-service by selecting a version number — no out-of-band coordination with admins for
  release image URLs
  • Admins govern which OCP versions tenants can provision, with lifecycle states that signal deprecation and block
  obsolete versions
  • Version validation at API time catches errors before provisioning begins, eliminating wasted build cycles from
  invalid or stale references
  • Deprecated versions surface warnings with replacement guidance, helping tenants plan ahead
  • Delete protection prevents accidental removal of versions backing active clusters
  • Establishes the version management approach that cluster upgrade operations (OSAC-1415) and ACM version auto-sync
  will build on
  **Goals:**
  • Users specify an OpenShift version by number instead of a raw OCI release image URL when creating a cluster
  • Users receive immediate, descriptive feedback when specifying an invalid, obsolete, or deprecated version — before
  any provisioning begins
  • Cloud Provider Admins manage available cluster versions through the CLI and UI console
  • Tenant Users can discover and select from available versions when creating a cluster — in the CLI, UI, and API
  **Non-Goals:**
  • Cluster upgrade operations and channel propagation to the hosted cluster (OSAC-1415). Channels are stored as
  version catalog metadata but not propagated in v0.2
  • ACM ClusterImageSet auto-sync — versions are admin-managed in v0.2
  • VM image management — separate resource under OSAC-979
  • In-place upgrade migration — OSAC does not support in-place upgrades; this feature assumes fresh deployment

## Linked Issues

- **OSAC-1834** (In Progress): CaaS UX: Surface bare metal machine availability to tenants during cluster creation
- **OSAC-1423** (In Progress): Replace release_image URL with OpenShift version in Cluster API
