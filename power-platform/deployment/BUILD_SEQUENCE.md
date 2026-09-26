# MCPD Sentinel Power Platform Build Sequence

This sequence is designed so the maximum amount of work can be prepared in source control before a Power Platform development tenant is available.

## Phase 0 — Source-controlled definition

- [x] Lock original Sentinel baseline.
- [x] Define portable solution/environment variables.
- [x] Define Dataverse tables.
- [x] Define security roles and role scope.
- [x] Define Power Apps screens and reusable components.
- [x] Define FTO DOR categories and rating scale.
- [x] Define FTO phase/task seed data.
- [x] Define Action Center rules.
- [x] Define Report Inspector contract.
- [x] Define FTO Scenario Engine contract.
- [x] Define Watch Commander tables/workflows.
- [x] Define Power Automate workflow contracts.
- [x] Define Power BI semantic model.
- [x] Define government import checklist.
- [ ] Complete source-controlled Power Fx screen formulas.
- [ ] Complete seed/reference data mapping.
- [ ] Complete solution test cases.

Before any export, run `deployment/preflight.ps1` against the approved development environment and retain its output with the release evidence.

## Phase 1 — Development tenant

1. Create/select a Dataverse environment.
2. Create solution `MCPDSentinel` with publisher prefix `mcpd`.
3. Create environment variables and connection references.
4. Create Dataverse tables/relationships/choices from `dataverse-schema.yaml`.
5. Load seed records from `seed/`.
6. Create Dataverse security roles.
7. Create Canvas App and apply the screen/component specifications.
8. Implement formulas from `app/powerfx-formulas.md`.
9. Implement Power Automate flows from `flows/`.
10. Create Power BI model/report from `bi/model-spec.yaml`.
11. Load synthetic demo users/data only.
12. Run functional/security test cases.

## Phase 2 — Development export

1. Increment solution version.
2. Run solution checker.
3. Export unmanaged backup.
4. Export managed production solution.
5. Store the exported artifacts outside the government tenant only if policy permits.
6. Record Git commit corresponding to the export.

## Phase 3 — Government tenant

Follow `GOVERNMENT_IMPORT_CHECKLIST.md`.

## Design rule

Do not fix a tenant-specific value directly in a formula when it can be an environment variable or connection reference. This is what keeps the government transfer close to import/reconnect/test instead of rebuild.
