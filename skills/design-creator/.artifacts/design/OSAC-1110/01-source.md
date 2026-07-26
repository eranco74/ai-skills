# OSAC-1110: Storage Tier Definition & Private API

## Metadata

- **Status**: In Progress
- **Priority**: Undefined
- **Assignee**: Roy Golan
- **Reporter**: Akshay Nadkarni
- **Components**: Storage
- **Labels**: None

## Description

## Summary

  Private API for defining and managing storage tiers (e.g., fast, standard, archive) in OSAC. Cloud Provider Admins
  use this API to create tiers that represent different storage quality-of-service levels, each associated with a
  registered StorageBackend.

  The API serves as the registration and catalog layer. Integration with the operator and AAP provisioning path (so
  that tier definitions drive StorageClass provisioning at runtime) is tracked separately under the Backend & Tier API
  Integration epic.

  ## Demo

  1. Create a storage tier: POST /api/private/v1/storage_tiers (description, backend association with protocol,
  bandwidth limits, quota, encryption)
  2. List tiers: GET /api/private/v1/storage_tiers
  3. Get a specific tier: GET /api/private/v1/storage_tiers/{id}
  4. Update tier configuration
  5. Attempt to create a tier referencing a non-existent backend (rejected)
  6. Delete a tier

  ## UI

  StorageTier CRUD screens (list, detail, create, edit, delete). Cloud Provider Admin facing. See OSAC-1252 for
  existing UI ticket.

  Form fields (from storage_tier_type.proto):

  • spec.description (string)
  • spec.backends[] (repeated BackendAssociation):
  • backend_id (reference to registered StorageBackend)
  • protocol (enum: NFS, BLOCK)
  • max_read_bandwidth_mbs / max_write_bandwidth_mbs (int32)
  • quota_gib (int64)
  • encryption_enabled (bool)

  v0.1 limitation: only one backend association per tier.

  ## Acceptance Criteria

  [x] Enhancement Proposal published and approved
  [x] StorageTier CRUD API (Create, Get, List, Update, Delete) in fulfillment-service
  [x] DB storage with referential integrity (referenced backends must exist)
  [x] Protobuf restructured to follow project spec/status conventions (OSAC-2396)
  [ ] UI: StorageTier CRUD screens (OSAC-1252)

  ## Enhancement Proposal

  • StorageTier PRD & Design https://github.com/osac-project/enhancement-proposals/tree/main/enhancements/storage-tier-
  OSAC-1110

## Linked Issues

- **OSAC-1123** (In Progress): CaaS Tenant Storage Setup
