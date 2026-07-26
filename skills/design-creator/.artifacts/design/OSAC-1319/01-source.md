# OSAC-1319: BaremetalInstance UI

## Metadata

- **Status**: In Progress
- **Priority**: Undefined
- **Assignee**: Rastislav Wagner
- **Reporter**: Adrien Gentil
- **Components**: BMaaS, UI
- **Labels**: OSAC-UI-0.1

## Description

UI Expectations — BaremetalInstance

  Based on the BareMetal Instance API EP ( https://github.com/osac-project/enhancement-proposals/pull/45
  https://github.com/osac-project/enhancement-proposals/pull/45 ) (PR #53 for latest revision).

  *Scope:* Tenant-facing UI only. Cloud Provider Admin flows (template/catalog item management) are out of scope for
  this epic.

  *Screens / flows required:*

  *1. BareMetalInstance catalog item browser*

  • Read-only list: title, description (Markdown-rendered), hardware profile summary from field_definitions
  • Entry point before provisioning — helps tenant choose the right profile
  • No create/edit/delete controls (admin-only via private API)

  *2. BareMetalInstance list*

  • Columns: name, catalog item (linked), state badge (PROVISIONING / RUNNING / FAILED / DELETING), age
  • Consistent with ComputeInstance list layout
  • Create button → opens Create form

  *3. Create BareMetalInstance form*

  • Catalog item — required, dropdown/selector populated from GET /api/fulfillment/v1/baremetal_instance_catalog_items;
  shows title + description
  • SSH public key — optional text field; validated as OpenSSH format client-side
  • User data — optional textarea (cloud-init); client-side size guard (max 64 KB)
  • Run strategy — radio: Always on (default) / Halted
  • Submit → POST /api/fulfillment/v1/baremetal_instances

  *4. BareMetalInstance detail*

  • State badge + conditions list (for error details when FAILED)
  • Spec summary: catalog item, run strategy, SSH key present/absent, user data present/absent
  • Power toggle — Always ↔ Halted via PATCH run_strategy; disabled while PROVISIONING or DELETING
  • Restart — button sets restart_requested_at to now via PATCH; disabled unless state is RUNNING
  • Delete — confirmation dialog; disabled while DELETING

## Linked Issues

- **OSAC-1277** (In Progress): BaremetalInstance UI
- **OSAC-2429** (In Progress): CLONE - BaremetalInstance UI
