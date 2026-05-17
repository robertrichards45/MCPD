# Command-Level Readiness Plan

## Purpose
This plan defines the remaining work required to make the MCPD Portal ready for a controlled command demonstration.

## Readiness Objective
The immediate objective is not full production deployment. The immediate objective is a polished, reliable, sample-data demonstration that shows leadership how the platform improves field reporting, supervisory review, operational visibility, training tracking, and specialized section workflows.

## Command Demo Standard
The portal should feel like an internal operational platform, not a prototype. A command demo should run end-to-end without blank pages, broken links, unprofessional spacing, or confusing navigation.

## Priority 1: Critical Demonstration Path
The following path must be reliable before any leadership demonstration:

1. Load demo data.
2. Impersonate patrol officer.
3. Open officer mobile home.
4. Run law lookup.
5. Start sample report.
6. Enter parties and facts.
7. Generate draft narrative.
8. Review suggested forms.
9. Submit packet.
10. Switch to supervisor role.
11. Review pending report.
12. Return one report for correction.
13. Approve one report.
14. Show Watch Commander dashboard.
15. Show training roster status.
16. Show accident workflow.
17. Show command metrics.

## Priority 2: User Interface Stabilization
- Fix mobile bottom navigation overlap.
- Fix light/dark mode contrast issues.
- Ensure card spacing is consistent.
- Ensure action buttons are visible above mobile safe areas.
- Remove unfinished placeholder visuals from demo paths.
- Ensure dashboards look professional on desktop and tablet.

## Priority 3: Workflow Hardening
- Every workflow step must have a recovery path.
- No page should render blank.
- Errors should display professional guidance.
- Demo records must be clearly marked as sample data.
- Demo reset must never affect real records.

## Priority 4: Operational Credibility
- Use operational language instead of developer language.
- Show realistic role-based dashboards.
- Present Watch Commander and section dashboards as mission tools.
- Keep AI clearly marked as draft support requiring human review.
- Clarify that the portal supports workflow into CLEOC and does not replace CLEOC.

## Priority 5: Documentation
The following documents should be complete before command demonstration:
- Command demo script
- Command readiness checklist
- Known limitations
- Capabilities summary
- ISSM/G6 review notes
- Demo data description

## Command-Demo Ready Definition
Command-demo ready means a supervisor can click through the primary workflows with sample data and understand the operational value without requiring technical explanation.

## Production Ready Definition
Production ready requires separate review for hosting, authentication, records handling, PII, audit logs, mobile device access, AI use, cybersecurity, and command approval.
