# MCPD Sentinel — Power Platform Rebuild

This folder is the working source of truth for rebuilding MCPD Sentinel as a portable Microsoft Power Platform solution.

## Target architecture

- **Power Apps** — primary user-facing MCPD Sentinel application.
- **Dataverse** — structured operational, FTO, training, personnel-profile, workflow, and app configuration data.
- **Power Automate** — approvals, notifications, assignments, overdue workflows, and scheduled processing.
- **Power BI** — command, FTO, training, report-quality, and activity analytics.
- **SharePoint** — optional document repository for Orders, PDIs, SOPs, reference files, attachments, and other file-heavy content.
- **Microsoft Entra ID** — user identity and department access.

SharePoint is not the primary website. Officers should open one Sentinel app and see the tools/data appropriate to their role.

## Migration rule

The personal Microsoft environment is a development/test environment only. Do not place real MCPD law-enforcement, personnel, investigative, or sensitive records in the personal tenant. Use synthetic test users and test records.

The production deliverable must be portable to the government tenant through a managed Power Platform solution and environment-specific configuration.

## Initial module scope

1. Home / My Work
2. Reports Center
3. Narrative Creator
4. Report Quality Review
5. Accident Tools
6. Forms Library
7. Saved Work
8. Call Type Paperwork Manager
9. Training Center
10. FTO Center
11. Digital FTO Program
12. Qualifications / Readiness
13. Law Lookup
14. Orders & Memos
15. BOLO / Notices
16. Personnel
17. Statistics / Power BI
18. Administration / Configuration
19. FTO Patrol Simulator

## Explicitly not restored by default

Do not re-add modules the owner previously removed unless requested.

## Build status

- [x] Existing Flask/GitHub portal inventoried
- [x] Existing roles/permission model reviewed
- [x] Existing FTO simulator master specification reviewed
- [x] Existing forms flow map reviewed
- [ ] Dataverse tables created in development tenant
- [ ] Security roles created
- [ ] Power App shell created
- [ ] FTO module created
- [ ] Forms/report modules migrated
- [ ] Power Automate workflows created
- [ ] Power BI dataset/report created
- [ ] Government deployment package validated

## Development branch

All rebuild planning and source-controlled deployment assets begin on:

`power-platform-rebuild`
