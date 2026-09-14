# MCPD Sentinel FTO Simulator — Build Progress

Date: 14 September 2026

This file records what is actually present in the application after the current simulator build work. It supplements `FTO_SIMULATOR_MASTER_SPEC.md` and `FTO_SIMULATOR_IMPLEMENTATION_STATUS.md`.

## Implemented / Usable Foundation

### Separate trainee and evaluator experiences

The live trainee screen is designed around the observable call rather than exposing the evaluator rubric. A separate FTO/Evaluator view exposes hidden state, evaluator evidence, structured evidence/records, NPC state, replay information, and instructor controls.

### Natural-language simulator foundation

The simulator package includes a semantic action-interpreter foundation with deterministic application logic. AI is used to interpret language where configured; structured simulator state remains authoritative.

### Persistent synthetic runs

Scenario runs are persisted and can be reopened for evaluator review. The run record is used to connect scenario state, replay events, notes, and post-call training work.

### Virtual shift foundation

A Virtual Shift / Shift CAD foundation exists so scenario work can be attached to a synthetic shift rather than only functioning as isolated call exercises.

### Persistent field notebook

Implemented in:

- `app/simulator/field_notebook.py`
- `app/routes/scenario_notebook.py`
- `app/templates/scenario_notebook.html`

The trainee can create field notes during the call. Notes are attached to the exact synthetic run. Revisions preserve the original note rather than silently replacing it. Once the run is closed, the notebook becomes read-only.

The FTO can review the same notebook from the evaluator side.

### No trainee blotter / desk-journal exercise

The simulator post-call requirements layer explicitly excludes blotter and desk-journal entries from trainee paperwork.

This rule is enforced in both the requirements service and post-call submission route.

### Scenario requirements bridge

Implemented in:

- `app/simulator/training_requirements.py`
- `app/data/fto_scenario_requirements.json`

The simulator reuses the existing Call Type Paperwork Manager as the paperwork source instead of creating a second independent paperwork list. A simulator-specific overlay adds training notification/CID requirements that are not represented in the older call-type schema.

### CID recognition decision

The post-call training workflow requires the trainee to make a CID screening/notification decision without revealing the configured answer in the trainee view.

Configured requirements appear only in the evaluator comparison. Requirements that have not been formally verified for training are explicitly labeled so they are not used blindly as deficiencies.

### Post-call training package

Implemented in:

- `app/routes/scenario_paperwork.py`
- `app/templates/scenario_paperwork.html`

After the synthetic call is complete, the trainee can:

1. identify the officer-completed paperwork/statements they believe are required;
2. make the CID screening/notification decision;
3. document notification/screening notes;
4. write the training narrative independently;
5. submit the package to the FTO.

Narrative Creator assistance is intentionally absent from this evaluation workflow.

### Original submission and revision preservation

Every submitted package is retained by revision number. A correction creates a new revision; it does not overwrite the trainee's original work.

### Trainee self-assessment before FTO disposition

After the paperwork is submitted, the trainee must complete a self-assessment covering:

- what they believe went well;
- what they would change;
- the facts/authority/policy or procedure they relied on;
- notifications or screenings they considered;
- areas where they want additional training.

The FTO's final package disposition is locked until this reflection is submitted.

### Human FTO package review

The evaluator may:

- accept the training package;
- return it for correction;
- assign remedial training.

FTO review actions and comments are preserved in review history.

If the run is associated with an FTO assignment, assigning remediation can create an actual open `FTORemediation` training record for human follow-up.

The software does not automatically create a DOR rating or employment decision.

### FTO review sync back to trainee

FTO review state is stored with the persistent simulator run. When the trainee reopens the training package, returned-for-correction, remediation, or acceptance state is synchronized into the trainee session rather than remaining stranded in the evaluator's browser session.

### Advisory scenario-to-report consistency analysis

Implemented in:

- `app/simulator/report_consistency.py`

Each submitted narrative can be checked against the exact synthetic run ledger, including:

- information actually developed;
- simulated conversations;
- evidence state;
- field notes;
- timeline events;
- recorded notification decision.

Deterministic checks work without AI. When AI is configured, it may supplement those checks using only the supplied synthetic run ledger.

The evaluator can see advisory cues for possible:

- factual inconsistency;
- unsupported assertion;
- material omission;
- source-attribution issue;
- chronology conflict;
- evidence inconsistency;
- notification inconsistency.

These are explicitly FTO review suggestions. They are not automatic errors, DOR findings, legal conclusions, pass/fail decisions, discipline, or employment decisions.

The trainee does not see these hidden consistency suggestions in the normal trainee paperwork view.

### Evaluator navigation

The evaluator screen links directly to:

- the trainee Field Notebook;
- the submitted Training Package;
- the persistent scenario/evaluator record.

### Post-call flow

The normal live-call screen now directs a trainee from a completed/terminated scenario into the Training Package instead of advertising the debrief immediately.

Target sequence:

**Call → Field Notes → Required Paperwork/Notifications → Submission → Self-Assessment → FTO Review/Debrief → Correction or Remediation when needed**

## Automated Tests Added

Current build work includes tests for:

- field-note creation;
- field-note revision preserving the original;
- field notes becoming read-only after call closure;
- no trainee blotter/desk-journal requirement;
- configured CID screening requirement for designated training scenarios;
- preventing post-call paperwork access during an active call;
- preserving original paperwork submissions and revisions;
- report-analysis fallback operating without live AI in test mode;
- report-consistency cues remaining hidden from the trainee view;
- report-consistency cues appearing in the evaluator view;
- FTO disposition remaining locked until self-assessment;
- FTO correction state synchronizing back into the trainee session.

Relevant test files:

- `app/tests/test_scenario_field_notebook.py`
- `app/tests/test_scenario_paperwork_workflow.py`
- `app/tests/test_scenario_report_consistency.py`

## Still Partial / Next Priority

### Complete debrief gate

The normal UI flow now routes the trainee through paperwork/self-assessment first, but the historical review route should also enforce the same gate server-side so a manually entered review URL cannot bypass the intended sequence.

### Actual training form replicas

The current package tests paperwork selection and narrative submission. The next major step is training-only replicas/state for the actual applicable forms without writing anything to official `SavedForm` or operational records.

### Line-by-line narrative FTO markup

Add highlights/comments tied to specific text ranges, preserve each marked revision, and support side-by-side original/corrected review.

### Supervisor / Watch Commander notification matrix

Extend the requirements overlay beyond CID so supervisory notification can be independently recognized and reviewed without revealing the answer during the live scenario.

### CID interaction during the live scenario

The current workflow tests recognition/documentation. Future scenarios should support a simulated CID contact when the scenario requires actual screening/coordination and when doing so adds training value.

### Deficiency/strength history and trend analytics

Current remediation can be opened, but long-term competency trend tracking, repeated-strength tracking, repeated-deficiency detection, and before/after remediation comparison still need deeper implementation.

### Remediation assignment to a different scenario

The system needs the automated recommendation layer that suggests a different scenario testing the same competency, subject to FTO approval.

### Exposure tracker / phase requirements / critical sign-offs

Still required at the program level.

### Final graduation virtual shift

Still required after the shift engine and paperwork backlog features are mature.

### Scenario Builder and governance workflow

Still required for non-code authoring, SME/policy approval, versioning, and retirement.

## Validation Status

Repository deployment status was still pending at the time of this update; no failed deployment status had been returned.

A local clone/test run could not be performed from the current execution environment because outbound DNS/network access to GitHub was unavailable. Therefore this file does not claim a local pytest pass.

## Build Rule

Do not mark a feature "implemented" simply because it appears in the master specification. Mark it implemented only when the code path exists, is integrated into the user workflow, and has appropriate tests or verification coverage.
