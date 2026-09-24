# MCPD Sentinel Power Platform Rebuild — Original Build Baseline

## Source-of-truth rule

The live/current mclbpd.com website and the current `main` branch are **not** the product baseline for this rebuild.

The Power Platform rebuild must follow the recovered **original MCPD Sentinel build line** and the user's original Sentinel design decisions. The current website may be consulted only for a specific asset or feature the user explicitly decides to carry forward.

Recovered checkpoints documented in the user's library include:

- MCPD_Sentinel_v0.11
- MCPD_Sentinel_v0.13
- MCPD_Sentinel_v0.14 unfinished source, which was byte-for-byte identical to v0.13 at recovery time

The fullest intact recovered checkpoint is therefore treated as the implementation reference, while the earliest Sentinel design principles remain authoritative for simplicity and workflow.

## Original Sentinel design principles

- One simple department application.
- Large, clear controls and plain terminology.
- Role-aware access.
- Report Quality Inspector / Report Inspector.
- Policy / approved-source search.
- FTO Instructor & Evaluator.
- Selectable FTO scenarios plus random-call capability.
- Scenario state persists and trainee decisions have consequences.
- End Call transitions into required paperwork.
- FTO can review the trainee's decisions, paperwork, deficiencies, and remediation.
- Approved-source grounding; software does not invent facts or authority.
- Human supervisor/FTO retains final judgment.

## Original core functional families

### Report Inspector
- Narrative-quality review cues.
- Completeness/consistency checks.
- Approved-source/policy matching.
- Report packet requirements.
- Explain why an item was flagged.
- Supervisor review/correction lifecycle where applicable.

### Policy / Reference Search
- Search current approved reference material.
- Preserve source/version identity.
- Distinguish approved material from drafts/placeholders.

### FTO Instructor & Evaluator
- Standard and accelerated program support.
- Selectable scenarios.
- Random call / patrol simulation.
- Multi-turn investigation.
- Hidden evaluator internals during trainee evaluation.
- Dispatch/CAD interaction.
- Field notes.
- Evidence and world-state tracking.
- Required notification recognition including CID when applicable.
- End-of-call paperwork.
- FTO review.
- Remedial training.
- Re-evaluation.
- Longitudinal progress.

### User / Role Model
- Officer
- FTO
- Supervisor
- Administrator / system controller
- Additional department roles may be mapped only where needed for the Microsoft implementation.

## Not a baseline merely because it exists on the current website

Do not automatically copy current-live-site navigation, dashboards, route structure, Flask models, or later experimental modules into the Power Platform rebuild.

In particular, later live-site items previously removed or rejected must not reappear unless the user explicitly requests them.

## Microsoft implementation target

The original Sentinel experience will be reimplemented using:

- Power Apps for the user-facing application
- Dataverse for structured records
- Power Automate for workflow/notifications
- Power BI for analytics
- SharePoint only where useful for document libraries
- Microsoft Entra ID for identity

The Microsoft architecture may differ internally from the original Flask implementation, but the user-facing functions and workflows should remain faithful to the original build.

## FTO manual relationship

The uploaded Field Training Program Manual is an authoritative content source for the digital FTO program (DOR categories, task-book requirements, phases, evaluation rules, etc.). It supplements the original Sentinel build; it does not make the current live website the baseline.
