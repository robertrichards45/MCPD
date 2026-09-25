# MCPD Sentinel Power Platform — Project Status

## Overall status

**Active — Phase 1**

## Completed foundation

- Original Sentinel baseline recovered and locked
- Full original MCPD Portal feature inventory restored
- Full module registry created
- Codex handoff and AGENTS instructions created
- Initial solution manifest created
- Initial Dataverse schema created
- Initial security model created
- App screen map created
- Approved visual system/theme created
- Interactive visual prototype created
- FTO DOR categories/scale/anchors loaded
- FTO phase/task seed data created
- Report Inspector specification created
- Scenario Engine specification created
- Watch Commander specification/workflows created
- Assistant Operations role/workspace created
- Power Automate workflow specs created
- Power BI model spec created
- Synthetic demo data created
- Export/import helper scripts created
- Initial acceptance tests created
- GitHub project phase issues created (#54–#61)

## In progress

### Phase 1 — Active
Dataverse coverage has now been expanded across the full original Portal scope.

Completed this pass:
- full original-portal schema expansion
- normalized choice registry
- relationship map
- data classification/storage guidance

Remaining in Phase 1:
- normalize inline choices to the shared registry
- add table-by-table retention/ownership/security classification
- validate every module-to-table mapping
- add schema validation checklist/tests

## Blocked until Microsoft development environment is available

- Actual Dataverse table creation
- Actual Canvas App creation
- Actual Power Automate flow creation
- Actual Power BI workspace/model deployment
- Managed solution export

These are tenant-execution tasks, not design gaps.

## Next source-controlled work

1. Expand `dataverse-schema.yaml`.
2. Create normalized choices/enums.
3. Add full relationship map.
4. Add retention/ownership classification per table.
5. Add schema validation checklist.
6. Expand acceptance tests for newly modeled modules.
