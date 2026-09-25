# MCPD Sentinel — Codex Handoff

## Repository / branch

Repository: `robertrichards45/MCPD`

Work only on branch:

`power-platform-rebuild`

Primary working directory:

`power-platform/`

## Current state

The source-controlled Power Platform definition is substantially prepared.

Already present:

- original-build baseline lock
- full original MCPD Portal feature inventory
- full module registry
- solution manifest
- Dataverse schema
- security model
- role permission matrix
- Power Apps screen map
- component specifications
- Action Center rules
- Power Fx patterns
- approved UI design system/theme
- interactive HTML/CSS/JS prototype
- digital FTO behavior
- DOR categories/scale/rating anchors
- FTO phase/task seed data
- Report Inspector contract
- Scenario Engine contract
- grounding/human-judgment contract
- Power Automate workflow specifications
- Power BI model specification
- synthetic demo data
- export/import helper scripts
- acceptance tests

## Immediate Codex objectives

### 1. Validate and normalize the source-controlled model

Review all YAML/CSV/Markdown definitions for:
- naming consistency
- duplicate concepts
- invalid references
- missing relationships
- missing ownership/security assumptions
- choice-value consistency
- environment-variable coverage

Do not remove functionality to make normalization easier.

### 2. Expand Dataverse schema to full original-portal coverage

The current schema is strongest around Sentinel/FTO/Reports/Watch.

Add structured tables/relationships for all remaining original modules, including:

- incident reporting
- involved persons
- vehicles
- property/evidence
- attachments/photos metadata
- form instances
- legal/reference corpus
- orders/favorites/versioning
- training roster/signature/qualification
- BOLO
- performance evaluations
- accident reconstruction metadata
- armory
- RFI
- truck gate
- vehicle inspections
- CLEO structured reporting
- officer statistics/targets
- announcements
- Assistant Operations due-outs
- AI/learning requests metadata
- reference materials/versioning
- import/export job history

### 3. Build a complete security matrix

Create Dataverse-role definitions for:

- Patrol Officer
- Field Training Officer
- Desk Sergeant
- Watch Commander
- Assistant Operations Officer
- FTO Coordinator
- Training Manager
- Forms Manager
- Report Reviewer
- Website/System Controller
- Site Owner / Builder-equivalent role
- special module roles where required (Armory, RFI, Truck Gate, etc.)

### 4. Finish Power Apps implementation specification

For every module in `module-registry.yaml`, define:

- screen(s)
- data sources
- galleries/forms
- create/read/update/delete actions
- validation
- role visibility
- responsive behavior
- empty/error/loading states
- navigation
- required Power Fx patterns

Follow the approved dark Sentinel visual system.

### 5. Prepare solution-generation assets

Where Power Platform CLI/source formats can be produced reliably without inventing tenant-generated IDs:

- create solution folder structure
- create environment-variable definitions
- create connection-reference definitions
- create choice definitions
- create data import templates
- create deployment/settings templates
- create scripts that can be run after a development environment is available

Do not manufacture invalid Power Platform files just to make the folder look complete.

### 6. Expand acceptance testing

Add tests for every module in `FULL_ORIGINAL_PORTAL_INVENTORY.md`.

Include:
- role/security tests
- mobile tests
- workflow tests
- import/export tests
- government portability tests
- data retention tests
- audit tests
- failure/recovery tests

## Definition of done for pre-tenant work

Pre-tenant work is complete when a developer can open this branch, provision/connect a Power Platform development environment, and execute a documented build with minimal design decisions left unresolved.

## Next phase once Microsoft environment access is available

1. Create `MCPDSentinel` solution.
2. Create Dataverse tables/choices/relationships.
3. Seed synthetic data.
4. Create security roles.
5. Build Canvas App from the source specifications.
6. Build flows.
7. Build Power BI model/report.
8. Run acceptance tests.
9. Export unmanaged backup.
10. Export managed production package.
11. Import to government tenant.
12. Rebind government connections/environment variables.
13. Assign groups/roles.
14. Validate and publish.

## Important

Do not use the current live website as the feature baseline.

Do not remove original modules because they appear obsolete in the live Flask site.

Do not replace the approved dark Sentinel design with the current website's visual design.
