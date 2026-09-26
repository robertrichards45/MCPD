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
- resolve overlapping concepts, required fields and relationship cardinality constraints
- extend source validation to seed values, workflow transitions and cross-file mappings
- repair BI source YAML quoting and validate analytics table references

### 25 Sep 2026 — Module coverage and table data policies

- Mapped all 33 registered modules to explicit tables and external document stores
  in `module-data-map.yaml`; all 87 tables are covered.
- Added per-table ownership, design classification, security and retention profiles
  in `table-data-policies.yaml`. Approved production schedules remain deployment
  inputs; automatic deletion is disabled and legal holds must block disposition.
- Corrected 45 organization-owned declarations to user/team ownership to support
  required scopes. Actual roles, teams, sharing, evaluator field security and
  lifecycle enforcement remain tenant/Phase 2 work.
- Mapped every existing URL column and added the empty, non-secret
  `mcpd_EvidenceMediaStoreId` environment setting for future approved media storage.
- Extended validation to module/table-policy coverage, storage dependencies,
  environment references, ownership consistency and evaluator/retention safeguards.
- All 20 regression tests and the validator pass, including intentionally broken
  mappings, ownership, storage references and safeguards.
- Documented boundaries and remaining decisions in `DATA_MODEL_CONTRACT.md`.
  Structural coverage does not imply feature completion or deployed security.
  Full original scope and approved UI assets remain unchanged.

### 25 Sep 2026 — Choice normalization and executable validation

- Resolved all 104 inline/unbound choice declarations across the 87-table schema:
  102 now reference named registries; locally configurable report type and shift
  labels are text, with the decision documented in `tests/schema-validation.md`.
- Preserved every existing inline option value and order, all tables/columns,
  lookup relationships, ownership declarations, and the approved UI assets.
- Added source validation for duplicate YAML keys, named choices, lookup targets,
  ownership values, and protected FTO program/phase/acknowledgment vocabulary.
- Added six regression tests, including intentionally broken references and
  duplicate definitions. Validator and all six tests pass locally.
- GenAI remains disabled by default with endpoint/model supplied by environment
  configuration. No endpoint, authentication format or credential was invented.

This completes the choice-normalization slice, not Phase 1 or tenant deployment.
Numeric Dataverse option IDs remain part of solution-generation work.

## Blocked until Microsoft development environment is available

- Actual Dataverse table creation
- Actual Canvas App creation
- Actual Power Automate flow creation
- Actual Power BI workspace/model deployment
- Managed solution export

These tenant tasks are separate from the remaining source-model decisions above.

## Next source-controlled work

1. Resolve Report/CLEO and reference-versioning overlaps and cardinality constraints.
2. Validate required/unique fields, seed values and workflow transitions.
3. Repair BI source YAML and validate analytics mappings.
4. Complete Phase 2 role/team/column-security definitions using the table policies.
