# MCPD Sentinel FTO Simulator — Implementation Status

This file tracks implementation against `FTO_SIMULATOR_MASTER_SPEC.md`.

## Status Legend

- **Implemented** — present in the current application and usable.
- **Partial** — foundation exists but does not yet meet the master specification.
- **Required** — not yet implemented or not yet verified.

---

# Current Foundation

## Scenario families and staged calls — Implemented / Partial

The current Scenario Lab includes multiple synthetic call families and staged fact development.

Existing call families include examples involving calls for service, access control, investigations, traffic enforcement, and medical response.

**Next:** convert fixed/staged flows into deeper scenario-family generation with controlled random variables and multiple legitimate paths.

## Natural-language trainee decisions — Partial

The trainee can already enter free-text actions and questions.

**Current limitation:** portions of state interpretation still depend on keyword/signal matching.

**Next:** semantic action interpreter that converts natural language to structured actions while keeping deterministic world state authoritative.

## NPC conversations — Partial

The current simulator supports conversations with scenario actors and has deterministic fallback responses when AI is unavailable.

**Next:** persistent NPC memory, stronger knowledge boundaries, independent emotional state, reliability/deception variation, and location/state changes.

## Persistent scene state — Partial

Current state tracks items such as call clock, scene risk, person state, backup/resource status, evidence state, actor state, branch events, complaint/review flags, scene updates, and decision history.

**Next:** expand into a full world-state model including locations, environmental conditions, records/CAD state, notification state, outstanding tasks, and richer evidence objects.

## Time progression and delayed consequences — Implemented / Partial

Time already advances and can trigger delayed developments such as resource arrival, witness availability changes, or evidence-related events.

**Next:** larger library of controlled time/event triggers and realistic shift-level interruptions.

## Branch events and consequences — Implemented / Partial

The simulator already supports branch events and consequences created by trainee actions.

**Next:** broaden consequence logic, support more legitimate resolutions, and reduce dependence on scripted event paths.

## Irreversible / terminal outcomes — Implemented / Partial

The simulator supports terminal training outcomes for sufficiently serious scenario decisions.

**Next:** formalize irreversible decisions and preserve them in the complete FTO training record.

## Reproducible run identifiers — Implemented / Partial

Current UI exposes a run identifier for discussing an exact synthetic fact pattern.

**Next:** formal seeded reproducibility across core scenario truth and remediation comparisons.

## Evidence state — Partial

The current engine tracks some evidence-preservation state.

**Next:** evidence as structured objects with source, location, discovery, preservation, collection, and custody state.

---

# Immediate Gaps Requiring Priority Work

## 1. Separate trainee view from evaluator view — Required

The active trainee UI currently exposes simulator internals such as risk, branch information, phase/progress information, and immediate FTO feedback.

**Required change:** hide evaluator internals during normal evaluation runs and move them to an FTO/Evaluator workspace.

## 2. Semantic action interpreter — Required

Replace keyword/signal dependence with AI-assisted intent parsing into structured actions.

The deterministic engine remains authoritative for world-state changes.

## 3. Digital field notebook — Required

Add persistent trainee notes that carry from the call into paperwork.

Do not provide a perfect automatic after-call fact summary.

## 4. Training CAD / radio chronology — Required

Add dedicated radio/Dispatch interactions, call/status history, resource requests, records returns, and a reviewable chronology.

## 5. Authoritative MCPD requirements matrix — Required

Build one source of truth for:

- officer-required paperwork
- written statements
- evidence requirements
- CID notification/screening
- supervisor notification
- investigative referral
- applicable references

The Scenario Engine and Call Type Paperwork Manager must use the same source.

## 6. Blotter rule — Required

**Do not include blotter entry as trainee paperwork in the simulator.**

This is explicitly excluded from the trainee paperwork workflow.

## 7. CID recognition and notification — Required

The trainee must independently recognize when CID notification/screening is required.

Add:

- scenario-specific CID rules
- natural-language notification
- simulated CID response when useful
- timing/content tracking
- FTO review of notification quality
- CID-specific remediation

## 8. Supervisor / Watch Commander notification — Required

Use the same principle as CID: the trainee should recognize the requirement rather than being told by the simulator during evaluation.

## 9. Call-to-paperwork workflow — Required

After call disposition, transition into officer-required training paperwork.

Use only facts actually developed during that run.

## 10. Paperwork selection test — Required

When appropriate, require the trainee to identify which paperwork is necessary before revealing the authoritative requirements.

## 11. Narrative Creator evaluation lockout — Required

During formal evaluation, the trainee must write the narrative independently.

Narrative Creator may be used by the FTO afterward for comparison/coaching or in deliberately enabled Coaching Mode.

## 12. Formal submission and revision history — Required

Preserve:

- Original Submission
- Revision 1
- Revision 2, etc.

Never silently overwrite a trainee’s original work.

## 13. FTO Review workspace — Required

Create one place to review:

- what happened
- what trainee knew
- what trainee did
- radio/CAD
- evidence
- notifications
- final disposition
- paperwork
- original/revised narrative
- Sentinel review suggestions

## 14. Scenario-to-report consistency checker — Required

Compare submitted forms/narrative against scenario truth and surface possible discrepancies to the FTO.

AI suggestions require human confirmation.

## 15. Separate field vs documentation evaluation — Required

Do not combine these into one score.

A trainee may handle a call well and document it poorly, or the reverse.

## 16. Deficiency and strength tracking — Required

Track both repeated weaknesses and repeated strengths across training events.

## 17. Remediation workflow — Required

Support:

- FTO-approved remediation
- different scenario testing same competency
- paperwork-only remediation
- instruction before re-test when appropriate
- before/after comparison
- FTO confirmation of improvement

## 18. Trainee self-assessment — Required

Require a reflection before final feedback is revealed.

## 19. Trainee acknowledgement/comments — Required

Acknowledgement means the evaluation was reviewed, not necessarily agreed with.

## 20. FTO intervention tracking — Required

Record when the FTO had to intervene and distinguish that from ordinary trainee mistakes.

---

# Program-Level Requirements

## FTO profile integration — Required

Show assigned/completed scenarios, pending paperwork, open reviews, strengths, deficiencies, remediation, and competency trends.

## Scenario assignments — Required

Support specific scenarios, scenario families, competencies, remediation, full shifts, and paperwork-only assignments.

## Phase-based packages — Required

Support standard and accelerated FTO structures with different autonomy levels and required exposure.

## Exposure tracker — Required

Track which call types/skills were actually practiced.

## Critical skill sign-offs — Required

FTO decides when competency is consistently demonstrated.

## Final graduation virtual shift — Required

A complete simulated shift with mixed calls, interruptions, notifications, paperwork, and no routine coaching.

---

# Virtual Shift Requirements

## START SHIFT — Required

Trainee signs on and receives calls through Dispatch rather than selecting a scenario title.

## Mixed call workload — Required

Include routine and complex calls. Do not make every call high risk.

## Pending calls / prioritization — Required

Advanced training should include held work and competing priorities.

## Report backlog — Required

Allow multiple calls before all paperwork is complete to test notes and organization.

## End-of-shift review — Required

Summarize calls, reports, evidence, notifications, outstanding follow-up, and lessons learned.

## Follow-up / supplemental investigations — Required

Some synthetic cases should continue beyond the initial call.

---

# Scenario Authoring / Governance

## Scenario Builder — Required

Authorized instructors can build scenarios without editing Python.

## AI-assisted drafting — Required

AI may draft, but authorized humans must approve scenarios before trainee use.

## Sanitized real-incident conversion — Required

Allow lessons learned from real incidents to be transformed into synthetic training scenarios without sensitive/identifying details.

## Approval lifecycle — Required

Draft → SME Review → Legal/Policy Review → Approved → Retired.

## Scenario quality feedback — Required

FTOs can flag unrealistic behavior, incorrect requirements, AI errors, unclear facts, and policy conflicts.

## Scenario analytics — Required

Identify unusually high failure concentrations that may indicate scenario problems.

## Policy/reference versioning — Required

Preserve the rule/reference version active when each run occurred.

---

# FTO Program Management

## FTO standardization/calibration — Required

Provide common synthetic evaluations so FTO rating differences can be identified and addressed.

## Coordinator dashboard — Required

Show active trainees, phases, overdue reviews, remediation, missing competencies, completion dates, FTO workload, and department-level training trends.

## Workload balancing — Required

Show review backlog and trainee assignments by FTO.

## In-service mode — Required / Future

Extend simulator use to qualified officers for refresher training.

## Supervisor mode — Required / Future

Create supervisory decision-making and review scenarios.

---

# Records / Audit / Security

## Complete training record — Required

Preserve all major scenario, notification, paperwork, FTO review, remediation, and acknowledgement data.

## Lifecycle states — Required

ASSIGNED → IN PROGRESS → CALL CLEARED → NOTIFICATIONS/PAPERWORK → TRAINEE SUBMITTED → AWAITING FTO REVIEW → FTO REVIEWED → CORRECTION/REMEDIATION when applicable → FTO CLOSED.

## Audit trail — Required

Do not silently overwrite historical actions or submissions.

## Downloadable training packet — Required

Allow authorized export of the complete training package.

## Training/operational separation — Required

Synthetic training records must never become official operational records.

## Synthetic / non-sensitive data — Required

Use training-safe identities, records, vehicles, and locations.

## Role-based access — Required

Trainee, FTO, FTO Coordinator, and Administrator permissions must be separated.

## Employee-training privacy — Required

Use role-based access, audit logs, retention rules, and restricted visibility.

---

# AI / Architecture / Reliability

## Structured truth vs generated dialogue — Partial / Required

Current design already limits some AI behavior. Continue moving all fundamental facts into structured state.

## AI guardrails — Required

Prevent hallucinated facts/evidence, knowledge leakage, future-fact leakage, NPC coaching, contradictory world states, and scoring manipulation.

## AI failure fallback — Partial / Required

Current fallback responses exist. Expand fallback behavior so the whole simulator remains usable during AI outages.

## Cost controls — Required

Use structured state, compact prompts, bounded history, and deterministic logic where AI adds no value.

## Human-readable AI review rationale — Required

No unexplained “AI score.” Every suggestion should include supporting evidence.

## Componentized architecture — Required

Separate scenario definitions, state engine, action interpreter, dispatch/radio, NPCs, evidence, records, requirements, paperwork, evaluator, FTO review, remediation, replay, authoring, and audit services.

## Backwards compatibility — Required

Do not break existing Sentinel authentication, FTO Center, reports, forms, Narrative Creator, or portal functions.

---

# Instructor Controls / Replay

## Live event injection — Required

Authorized FTO may inject scenario developments without manually running every branch.

## Live observation — Required

FTO may observe transcript, radio traffic, hidden state, evidence, pending events, competency evidence, and intervention triggers.

## Pause / resume — Required

Persist exact scenario state.

## Replay — Required

FTO can review the run step by step and see what the trainee knew at each decision point.

## Compare runs — Required

Compare original vs remediation and longer-term trends.

---

# Design Principles to Enforce

- Difficulty is not the same as danger.
- Advanced scenarios can be difficult because of ambiguity, conflicting information, time pressure, documentation, or competing priorities.
- Include irrelevant information and occasional false leads so the trainee must determine what matters.
- Use hidden secondary issues carefully; do not turn every scenario into a trick.
- Include professionalism-focused calls with no major enforcement action.
- Allow later simulated complaints where appropriate for communication/professionalism training.
- Support legitimate “not enough information yet” decisions.
- Support lawful no-enforcement outcomes.
- Do not reveal what competency is being tested.

---

# Automated Test Requirements

Required tests include:

- hidden facts stay hidden
- NPC knowledge boundaries hold
- time triggers work
- evidence can be lost
- resources do not arrive instantly without cause
- equivalent natural-language actions map consistently
- keyword gaming does not earn credit
- multiple reasonable dispositions can succeed
- irreversible decisions remain irreversible
- AI outage does not break the scenario
- CID/supervisor notification state is accurate
- paperwork fields compare correctly against scenario truth
- revisions preserve original work
- training records cannot enter operational records
- AI review suggestions require human confirmation

---

# Implementation Sequence

## Phase 1 — Immersion and Interpretation

- separate trainee/FTO views
- hide grading internals
- semantic action interpreter
- field notebook
- CAD/radio timeline
- stronger NPC memory/knowledge

## Phase 2 — Complete Call-to-Paperwork

- authoritative requirements matrix
- no blotter entry in trainee paperwork
- CID/supervisor recognition
- paperwork selection
- training-only forms
- Narrative Creator evaluation lockout
- formal submissions/revisions

## Phase 3 — FTO Review and Remediation

- FTO Review workspace
- report consistency checking
- line-by-line review
- field/documentation separation
- strengths/deficiencies
- remediation
- self-assessment and acknowledgement

## Phase 4 — Virtual Shift

- START SHIFT
- mixed dispatch calls
- pending calls/prioritization
- report backlog
- follow-up/supplements
- final graduation shift

## Phase 5 — Program Management and Scale

- Scenario Builder
- phase packages
- exposure/sign-offs
- FTO calibration
- coordinator dashboard
- agency configuration
- scenario versioning/retirement
- in-service and supervisor modes

---

# Acceptance Standard

Do not consider the simulator complete merely because a trainee can finish a scenario.

The target system must support the complete loop:

**Work the call → recognize notifications → make disposition → complete officer paperwork → submit → FTO reconstructs decisions → FTO reviews paperwork → strengths/deficiencies confirmed → remediation assigned → different exercise tests the weak skill → improvement confirmed → complete training record retained.**

The final product should feel like a real FTO training environment built around simulated patrol work, not a web-based quiz.
