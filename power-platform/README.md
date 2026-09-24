# MCPD Sentinel — Power Platform Rebuild

This folder is the working source of truth for rebuilding the **original MCPD Sentinel** as a portable Microsoft Power Platform solution.

> **Baseline warning:** the current/live mclbpd.com website and current GitHub `main` implementation are not the product baseline. See `ORIGINAL_BUILD_BASELINE.md`.

## Target architecture

- **Power Apps** — primary user-facing MCPD Sentinel application.
- **Dataverse** — structured FTO, reports, training, user, workflow, and configuration data.
- **Power Automate** — approvals, notifications, assignments, overdue workflows, and scheduled processing.
- **Power BI** — command, FTO, training, report-quality, and activity analytics.
- **SharePoint** — optional document repository for Orders, PDIs, SOPs, references, attachments, and other file-heavy content.
- **Microsoft Entra ID** — user identity and department access.

SharePoint is not the primary website. Officers should open one Sentinel application and see the tools and records appropriate to their role.

## Migration rule

The personal Microsoft environment is a development/test environment only. Use synthetic users and synthetic records. Do not place real MCPD law-enforcement, personnel, investigative, CJI, or other sensitive production records in the personal tenant.

The production deliverable must be portable to the government tenant through a managed Power Platform solution and environment-specific configuration.

## Original-build module scope

1. Home / My Work
2. Report Inspector / Report Quality Inspector
3. Policy / Approved-Source Search
4. FTO Instructor & Evaluator
5. Digital FTO Program
6. Scenario Lab / Patrol Simulator
7. End-of-call paperwork and FTO review
8. Remedial training and re-evaluation
9. Training / qualification tracking
10. Department personnel/profile and role access
11. Power BI analytics built from the above records
12. Administration / configuration

Additional forms, accident tools, call-type rules, orders/reference tools, and other MCPD functions can be incorporated where they belong, but the **original Sentinel build remains the UX/workflow baseline**.

## Build status

- [x] Recovered original Sentinel build lineage located
- [x] Original Sentinel baseline documented
- [x] Uploaded Field Training Program Manual reviewed for DOR/task-book content
- [x] Initial portable solution manifest created
- [x] Initial Dataverse schema created
- [x] Initial security model created
- [ ] Original-build screen map converted to Power Apps screen specification
- [ ] Dataverse tables generated in development tenant
- [ ] Security roles generated in development tenant
- [ ] Power App shell generated
- [ ] Digital FTO module generated
- [ ] Report Inspector generated
- [ ] Policy/Reference Search generated
- [ ] Scenario Lab generated
- [ ] Power Automate workflows generated
- [ ] Power BI dataset/report generated
- [ ] Government deployment package validated

## Development branch

All rebuild planning and source-controlled deployment assets are maintained on:

`power-platform-rebuild`
