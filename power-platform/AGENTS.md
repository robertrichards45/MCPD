# AGENTS.md — MCPD Sentinel Power Platform Rebuild

## Scope

This file governs work under `power-platform/`.

You are continuing the MCPD Sentinel Microsoft Power Platform rebuild.

## Critical source-of-truth rule

Do **not** use the current/live mclbpd.com website or the repository's current main implementation as the functional baseline.

The required functional baseline is:

1. The **full original MCPD Portal** feature set documented in:
   - `FULL_ORIGINAL_PORTAL_INVENTORY.md`
   - `module-registry.yaml`
2. The **original MCPD Sentinel** design documented in:
   - `ORIGINAL_BUILD_BASELINE.md`
3. The approved digital FTO implementation derived from the uploaded Field Training Program Manual and represented in:
   - `seed/fto-rating-categories.csv`
   - `seed/fto-rating-scale.csv`
   - `seed/fto-rating-anchors.csv`
   - `seed/fto-phase-tasks.csv`
   - `app/fto-screen-behavior.yaml`
4. The approved dark-blue visual design documented in:
   - `design/UI_DESIGN_SYSTEM.md`
   - `design/theme-tokens.yaml`
   - `design/SCREEN_BLUEPRINTS.md`
   - `prototype/`

## Product target

Build a portable Microsoft Power Platform solution using:

- Power Apps — user-facing application
- Dataverse — structured data
- Power Automate — workflows
- Power BI — analytics
- SharePoint — optional document/file libraries only
- Microsoft Entra ID — identity

The production goal is a managed solution that can be imported into a government Microsoft tenant with minimal reconfiguration.

## Development data rule

Use synthetic data only in personal/development environments.

Do not use real law-enforcement records, CJI, production personnel records, evidence, real report narratives, or sensitive operational data in the development tenant.

## UX rule

The approved dark Sentinel mockup is the target appearance.

Preserve the original functionality, but render it in the approved modern dark-blue design.

Do not re-create later live-site visual clutter simply because it exists in the current Flask portal.

## Functional scope

Everything listed in `FULL_ORIGINAL_PORTAL_INVENTORY.md` is in scope unless the owner explicitly removes it.

This includes, among other items:

- Dashboard
- Desktop and mobile incident reporting
- Forms library/manager
- Law Lookup / Policy Search
- Orders & Memoranda
- Training
- Bodycam/media module
- BOLO
- Personnel
- Performance Evaluation
- Accident Reconstruction
- Armory
- RFI
- Truck Gate
- Vehicle Inspections
- CLEO Structured Reporting
- Statistics
- Announcements
- Watch Commander / Digital Lieutenant
- Assistant Operations
- AI Assistant/tools
- Officer Handbook
- Incident Paperwork Guide
- Data import/export
- Administration / Builder equivalent
- Report Inspector
- FTO Center
- Digital DOR/task book
- Remedial training/re-evaluation
- Scenario Lab / Patrol Simulator
- Analytics

## Security rules

- Dataverse permissions are the security boundary; UI filtering is not.
- Preserve role scoping.
- Officer sees own records.
- FTO sees assigned trainees.
- Supervisor/Watch Commander sees authorized team/watch scope.
- Assistant Operations Officer sees authorized department-level operational scope.
- Administrator/System Controller handles configuration.
- Do not grant full administration merely because a role has broad operational visibility.

## Report Inspector rules

Never invent missing facts.

Keep these visually and logically separate:

1. Automated cue
2. Approved source
3. Authorized human judgment

Do not let AI make final determinations of guilt, probable cause, legal sufficiency, discipline, policy compliance, or final supervisor approval.

## FTO rules

- Standard and accelerated programs must remain supported.
- The 31 DOR categories and 1–7/N-O scale must be retained.
- Automated scenario scoring may create draft recommendations only.
- Final DOR ratings require an FTO.
- Trainee acknowledgment means receipt, not agreement.
- Supervisor review is preserved.
- Remedial training and re-evaluation are first-class workflows.
- Scenario evaluation mode must hide evaluator state from the trainee.

## Scenario engine rule

The trainee experience should feel like working patrol from a computer, not taking a quiz.

Use:

Dispatch → Response → Investigation → Decisions → Notifications → Disposition → Paperwork → Submission → FTO Review → Deficiency → Remedial → Re-evaluation → Closure.

## Portability rules

- Use environment variables for tenant-specific values.
- Use connection references.
- Avoid hard-coded tenant IDs, personal email addresses, SharePoint URLs, or personal user GUIDs.
- Build for managed-solution export.
- Keep government import/reconnect/testing lightweight.

## Before changing architecture

Read:

- `README.md`
- `ORIGINAL_BUILD_BASELINE.md`
- `FULL_ORIGINAL_PORTAL_INVENTORY.md`
- `solution-manifest.yaml`
- `dataverse-schema.yaml`
- `security-model.md`
- `app/app-screen-map.yaml`
- `design/UI_DESIGN_SYSTEM.md`
- `tests/acceptance-tests.md`

Do not silently delete scope to simplify implementation.
