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

## Core Sentinel module scope

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
- [x] Original-build screen map converted to Power Apps screen specification
- [ ] Dataverse tables generated in development tenant
- [ ] Security roles generated in development tenant
- [ ] Power App shell generated in Microsoft development tenant
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


## Source-controlled assets now prepared

- Original Sentinel baseline lock
- Portable solution manifest
- Dataverse schema including Report Inspector, FTO, Scenario Engine, Action Center, and Watch Commander entities
- Role/security model and role permission seed matrix
- Power Apps screen map, reusable component spec, Action Center rules, core Power Fx patterns, and FTO screen behavior
- FTO DOR rating categories and rating scale from the uploaded Field Training Program Manual
- FTO phase/task seed data from the uploaded Field Training Program Manual
- Report Inspector specification
- Scenario Engine specification
- Grounding/human-judgment contract
- FTO, report, watch, policy-expiration Power Automate workflow specifications
- Power BI semantic-model specification
- Synthetic demo users/roles/FTO assignments
- Development export and government import helper scripts
- Government deployment checklist
- Functional/security acceptance tests


## Approved visual direction

The owner approved the 24 Sep 2026 dark MCPD Sentinel concept. The rebuild now includes:

- Approved visual design system
- Theme tokens
- Power Apps styling formulas
- Screen-by-screen blueprints
- Interactive HTML/CSS/JS prototype covering Home, Action Center, Reports, Report Inspector, Policy, FTO Center, DOR, Scenario Lab, Watch Commander, and Analytics
- Standardized DOR rating-anchor help for all 31 categories


See `FULL_ORIGINAL_PORTAL_INVENTORY.md` for the restored original-portal feature inventory.
