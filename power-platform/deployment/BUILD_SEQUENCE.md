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
- [x] Lock development solution identity: `MCPD Sentinel Development`, publisher `MCPD`, prefix `mcpd`.
- [x] Lock approved 26 Sep 2026 Sentinel theme tokens.
- [ ] Complete source-controlled Power Fx screen formulas.
- [ ] Complete seed/reference data mapping.
- [ ] Complete solution test cases.

Before any export, run `deployment/preflight.ps1` against the approved development environment and retain its output with the release evidence.

## Phase 1 — Development tenant

1. Verify the Power Platform development environment is in a ready state before Dataverse creation.
   - Currency: `USD ($)`
   - Language: `English (United States)`
   - Sample apps and data: `Off`
   - If Currency or Language lists are blank, do not repeatedly click Create. Diagnose environment provisioning, licensing/permissions, tenant policy, or service-side blocking first.
2. Provision Dataverse.
3. Create the unmanaged solution `MCPD Sentinel Development` with publisher `MCPD` and prefix `mcpd`.
4. Create environment variables and connection references.
5. Create Dataverse tables/relationships/choices from `dataverse-schema.yaml`.
6. Load seed records from `seed/`.
7. Create Dataverse security roles.
8. Create Canvas App `MCPD Sentinel` inside the development solution and apply the screen/component specifications.
9. Implement formulas from `app/powerfx-formulas.md`.
10. Implement Power Automate flows from `flows/`.
11. Create Power BI model/report from `bi/model-spec.yaml`.
12. Load synthetic demo users/data only.
13. Run functional/security test cases.

## Initial Canvas build priority

Build in this order to minimize rework:

1. reusable responsive application shell;
2. centralized theme values;
3. data-driven role-aware navigation;
4. Home / Dashboard;
5. Watch Commander;
6. remaining modules by project phase.

Use reusable components, galleries and responsive containers. Save frequently and resolve formula errors before expanding the next module.

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

## Data handling rule

Development uses synthetic data only. Do not place government personnel information, operational data, CAC credentials, STARK/GenAI keys, passwords, or sensitive Marine Corps information in the development tenant, repository, scripts, seed data, or test artifacts.
