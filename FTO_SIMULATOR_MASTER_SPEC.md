# MCPD Sentinel FTO Patrol Simulator — Master Specification

## Purpose

This file is the authoritative product and training specification for the MCPD Sentinel FTO Scenario Engine.

The primary design standard is simple:

> The trainee should feel like they are working patrol from a computer, not completing an online course, quiz, or game.

The complete training loop is:

**Dispatch → Response → Investigation → Decisions → Required Notifications → Disposition → Officer Paperwork → Trainee Submission → FTO Review → Deficiency Identification → Remedial Training → Re-evaluation → FTO Closure**

The simulator should train complete job performance, not just whether a trainee can select a correct answer.

---

# 1. Preserve the Existing Strengths

Do not discard useful systems already present in Sentinel. Preserve and improve:

- persistent call state
- branching consequences
- changing scene conditions
- time progression
- delayed resource arrival
- witnesses or evidence becoming unavailable
- NPC conversations
- controlled NPC knowledge
- randomized run facts
- reproducible run identifiers
- terminal outcomes
- irreversible consequences
- remediation capability
- scenario-specific competencies
- FTO review concepts
- deterministic fallback behavior when AI is unavailable

The new architecture should evolve around these systems rather than replacing them with a generic chatbot.

---

# 2. Trainee Experience

## 2.1 Hide Evaluator Internals During Active Calls

During a normal evaluation run, the trainee should not see:

- risk scores
- branch counts
- hidden rubric criteria
- internal scoring logic
- competency scores
- pass/fail indicators
- “demonstrated” or “unresolved” grading lists
- internal event names
- evaluator reasoning

The trainee should see only information that an officer could reasonably perceive or receive.

## 2.2 Separate Simulation, Coaching, and FTO Modes

### Simulation / Evaluation Mode

The trainee works independently with no solution-revealing prompts.

### Coaching Mode

Used for early phases or deliberate remediation. An FTO may provide limited coaching questions without directly giving the answer.

### FTO / Evaluator Mode

Authorized FTOs can view hidden state, competency evidence, missed opportunities, evidence status, notification requirements, intervention triggers, and the complete decision history.

## 2.3 Natural-Language Officer Actions

Do not force the trainee to use solution-revealing buttons.

The trainee should be able to type or later speak natural actions such as:

- updating Dispatch
- requesting an additional unit or resource
- contacting a reporting party
- interviewing a witness
- asking for records information
- preserving evidence
- requesting medical assistance
- notifying CID
- notifying a supervisor
- making a disposition

Equivalent wording should be understood as equivalent intent.

## 2.4 Semantic Action Interpreter

Replace dependence on keyword matching with a semantic action interpreter.

AI should translate the trainee’s language into structured actions. The deterministic simulation engine should then apply those actions to world state.

Supported action categories should include:

- radio communication
- movement and observation
- interviews and questions
- commands/directions
- records requests
- resource requests
- evidence actions
- detention/arrest/release decisions where applicable
- medical requests
- CID notification
- supervisor notification
- disposition
- follow-up and reporting actions

**AI interprets language. The simulation engine controls truth.**

## 2.5 Dedicated Radio / Dispatch Interface

Create a radio interface separate from face-to-face NPC conversations.

The trainee should be able to communicate with:

- Dispatch
- patrol units
- supervisor / Watch Commander
- CID / investigators
- EMS / Fire
- gate/access-control personnel
- other configured resources

Dispatch should remember prior transmissions and know only information reasonably available through callers, simulated databases, CAD, and radio traffic.

## 2.6 Future Voice / Push-to-Talk

Typing must remain fully functional, but architect the system so voice interaction can be added later without redesigning the simulator.

## 2.7 Independent NPC Memory and Knowledge

Each NPC should have structured:

- identity
- role
- personality
- emotional state
- current location
- known facts
- incorrect beliefs
- observations
- motivations
- willingness to cooperate
- conversation history
- memory of prior interactions

NPCs must not know facts they did not observe or receive.

Some witnesses may be accurate, mistaken, incomplete, evasive, or intentionally deceptive. Not every scenario should involve deception.

## 2.8 No NPC Coaching

NPCs must never reveal the rubric, future facts, hidden facts, or recommended officer actions during an evaluation.

## 2.9 Persistent World-State Engine

Maintain authoritative state for:

- simulation clock
- officer location
- people and locations
- resource status
- subject/person state
- witness availability
- environment
- evidence condition/location
- vehicles and relevant property
- injuries/medical condition
- crowd behavior
- video/surveillance availability
- records-check state
- Dispatch/CAD information
- known versus unknown facts
- legal/policy-relevant facts
- prior officer actions
- outstanding tasks
- consequences already created
- notification state

The AI must not independently rewrite scenario truth.

## 2.10 Time Must Matter

The simulator should allow realistic time-based developments such as:

- witnesses becoming unavailable
- evidence becoming harder to preserve
- resources arriving later
- additional callers providing updates
- subject or complainant behavior changing
- supervisor or CID follow-up
- environmental changes

Not every event should occur in every run.

## 2.11 Dynamic Consequences

Consequences should reflect what would reasonably happen because of the trainee’s decisions rather than artificially punishing deviations from a preferred script.

Some mistakes may have no immediate visible consequence but should still be available for FTO review.

## 2.12 Multiple Legitimate Paths

Avoid a single correct route.

Support multiple lawful and reasonable dispositions, different investigation orders, different professional communication styles, different resource decisions, and appropriate no-enforcement outcomes.

Evaluate decisions using only the facts available at the time.

## 2.13 Legitimate Uncertainty

The simulator should recognize appropriate conclusions such as:

- insufficient information
- additional investigation needed
- no enforcement action appropriate
- unable to determine an offense yet

Do not reward premature conclusions simply because they end a scenario quickly.

## 2.14 Scenario Families and Randomization

Build reusable scenario families with controlled variation in:

- location type
- number of involved persons
- witness reliability
- subject cooperation
- available evidence
- surveillance availability
- injuries
- communication difficulties
- supervisor/resource availability
- caller accuracy
- time of day
- environmental conditions
- records responses

Each run must have a reproducible seed/run identifier.

## 2.15 Full Virtual Shift Mode — START SHIFT

This is a major feature.

The trainee should be able to start a simulated shift, sign on with Dispatch, receive calls naturally, work each call, clear it, manage paperwork, receive additional calls, manage pending work, and complete end-of-shift responsibilities.

The trainee should not be shown the scenario category or difficulty before the call.

Include routine calls heavily. Not every call should become high-risk.

## 2.16 Evolving Dispatch Information

Initial dispatch information should often be incomplete and may change while the trainee is responding. Initial caller information may also turn out to be inaccurate.

## 2.17 Synthetic Records / Database Responses

Support synthetic training responses for appropriate records queries such as identification status, vehicle information, warrants, access information, prior call cues, and other training-safe records.

Never use real personal information.

## 2.18 Observation and Scene Position

Allow the trainee to state what they are observing or where they are moving. Reveal only information that could reasonably be perceived from that position.

A simple scene/location model is more important initially than expensive 3-D graphics.

## 2.19 Environmental Conditions

Scenarios may include day/night, weather, lighting, noise, traffic, crowd size, public/restricted areas, and visibility when these factors materially affect the exercise.

## 2.20 Interruptions and Competing Priorities

Occasionally interrupt a call with realistic developments such as radio traffic, additional witnesses, arriving resources, changing conditions, supervisor questions, new information, or another involved person.

Advanced shift mode should support held/pending calls and prioritization.

## 2.21 Simulated Backup / Partner

Allow simulated partner or backup officers who can receive reasonable assignments without solving the call for the trainee.

## 2.22 Future Two-Trainee Scenarios

Support a future mode where two trainees share a call, divide responsibilities, communicate, and receive separate FTO evaluations.

## 2.23 Irreversible Decisions

Consequential decisions should remain part of the run. The trainee should not be able to simply rewrite the action and continue as if it never happened.

## 2.24 Near-Miss Errors

Not every poor decision should create a dramatic outcome. The FTO should still be able to identify a weak decision even if no negative event followed from it.

---

# 3. Field Notes, CAD, Evidence, and Documentation

## 3.1 Digital Field Notebook

Add a notebook that remains available throughout the call.

The trainee may record:

- names
- times
- phone numbers
- vehicle information
- witness details
- statements
- evidence information
- CID information
- supervisor information
- other investigative notes

At the end of the call, the trainee should work from information actually gathered and documented. Sentinel should not automatically provide a perfect summary.

## 3.2 Simulated CAD / Radio History

Provide a training CAD/radio chronology that can preserve appropriate timestamps and status history, including dispatch, acknowledgement, on-scene status, resource requests, database returns, significant updates, and clearing the call.

The FTO should be able to review this chronology later.

## 3.3 Evidence as Structured Training Objects

Evidence should be represented as objects rather than only prose.

Examples may include:

- photographs
- surveillance material
- written statements
- receipts
- damaged property
- identification records
- vehicle information
- screenshots
- synthetic documents

Each evidence item should have a source, location, discovery conditions, preservation state, and collection state.

## 3.4 Evidence / Chain-of-Custody Training

When relevant, train correct identification, preservation, collection, labeling, transfer, and documentation.

Distinguish between evidence that was merely noticed, requested, preserved, or actually collected.

## 3.5 Synthetic Visual Evidence

Use visual material only when it adds training value. Every visual must correspond to structured scenario truth.

---

# 4. One Authoritative MCPD Requirements Matrix

Create one source of truth for:

- officer-completed paperwork
- written-statement requirements
- evidence requirements
- CID notification/screening
- supervisor notification
- investigative referral
- other required notifications
- applicable policy/PDI/base-order/reference

The Scenario Engine, Call Type Paperwork Manager, and FTO Review system should use the same configuration.

Do not maintain contradictory rule sets.

---

# 5. Blotter Rule

**Do not require the trainee officer to complete a blotter entry as part of the Scenario Engine paperwork exercise.**

Blotter-entry responsibility is outside this trainee paperwork workflow.

The simulator may internally log the training event, but it should not present a blotter form to the trainee or grade the trainee on producing a blotter entry.

---

# 6. CID and Supervisor Notification Training

## 6.1 CID Recognition Must Be Tested

When a scenario requires CID notification, screening, referral, or consultation, the trainee should be expected to recognize that requirement.

Do not simply display “CID REQUIRED” during an evaluation.

## 6.2 CID Requirements Must Be Scenario-Specific

Use the authoritative requirements matrix to determine:

- whether CID notification is required
- whether screening is required
- when contact should occur
- what information should be provided
- what evidence/statements should be available
- related paperwork
- applicable references

## 6.3 Natural-Language CID Notification

The simulator should understand reasonable equivalent statements requesting CID contact or screening.

## 6.4 Simulated CID Response

Where training value exists, simulated CID may acknowledge the contact, request additional facts or supporting material, provide a screening response, or provide configured follow-up instructions.

CID should not solve the call for the trainee.

## 6.5 Track CID Timing and Quality

Record:

- whether CID was required
- whether trainee recognized the requirement
- when contact occurred
- what information was provided
- response/instructions
- whether follow-up was completed

A late notification may remain a training deficiency even if contact eventually occurs.

## 6.6 Supervisor / Watch Commander Recognition

Train supervisor-notification judgment in the same way. Do not reveal the requirement in advance during normal evaluation mode.

---

# 7. Post-Call Paperwork Workflow

## 7.1 The Exercise Continues After the Call Clears

A scenario is not complete simply because the scene is resolved. The trainee must transition to required officer paperwork using the exact facts from the run.

## 7.2 Officer-Required Paperwork Only

Depending on the scenario, training paperwork may include:

- full CCN with narrative
- written statements
- evidence/property documentation
- lost/found property documentation when applicable
- traffic or crash documentation
- warrant-related documentation
- medical-assist documentation
- CID/investigative screening or referral information
- other officer-completed MCPD forms

All training forms must be marked clearly as synthetic training records and must remain separate from operational records.

## 7.3 Trainee Determines What Paperwork Is Required

When appropriate, ask the trainee to select the paperwork they believe is required before revealing the correct set.

The FTO should later be able to see missing or unnecessary selections.

## 7.4 Use Only Facts Actually Developed

Do not supply information the trainee failed to obtain.

Examples:

- no witness identity if it was never obtained
- no vehicle identifier if it was never developed
- no preserved evidence if it was lost
- no statement if it was never obtained
- no claim that CID was notified when no contact occurred

Field performance must directly affect report-writing difficulty.

## 7.5 Trainee Completes Their Own Paperwork

Do not automatically write the entire report for the trainee.

The trainee should complete applicable fields, narrative, notifications, evidence information, disposition, and legal articulation where required.

## 7.6 Narrative Creator Lockout During Formal Evaluation

Disable automatic narrative-generation assistance during formal FTO evaluation scenarios.

After the original submission, the FTO may optionally use the Narrative Creator for comparison or coaching.

Coaching Mode may permit limited assistance if deliberately enabled.

## 7.7 Formal Trainee Submission

Require the trainee to formally submit the training package to the FTO.

The original submission must be preserved.

## 7.8 Report Return / Revision Workflow

Support FTO dispositions such as:

- Accepted
- Correction Required
- Remedial Training Required

If corrections are required, preserve the original and create Revision 1, Revision 2, etc. Never silently overwrite an earlier submission.

## 7.9 Report-Field Verification

Compare important form fields against scenario truth, including people, vehicles, location, property, witnesses, evidence, notifications, disposition, and times.

Potential discrepancies should be presented to the FTO for human review.

## 7.10 Line-by-Line Narrative Review

Allow FTOs to highlight text, comment, identify inaccuracies, identify missing information, identify unsupported conclusions, identify articulation issues, and compare revisions.

## 7.11 Scenario-to-Report Consistency Review

Sentinel should flag potential contradictions between the scenario record and the submitted paperwork.

Examples include:

- firsthand observation attributed to someone who did not personally observe it
- notification documented when none occurred
- evidence referenced but never preserved
- critical event timing inconsistent with the run
- material facts omitted

These are review suggestions, not automatic findings.

## 7.12 Report Integrity Review

Give special attention to discrepancies that make the trainee’s conduct appear materially different from the actual scenario timeline.

---

# 8. FTO Review Workspace

Create one review workspace containing:

### Scenario Record

- dispatch and updates
- trainee actions
- radio traffic
- NPC interviews
- evidence discovered/missed
- database responses
- major decisions
- changing conditions
- final disposition

### Notifications

- required notifications
- notifications actually made
- CID requirement/contact/timing
- supervisor requirement/contact
- follow-up actions

### Paperwork

- paperwork selected
- paperwork required
- original submission
- revisions
- narrative
- statements
- evidence documentation

### Sentinel Review Suggestions

- possible field deficiencies
- possible notification deficiencies
- possible report errors
- factual inconsistencies
- missing information
- policy/legal research cues

The FTO makes the final evaluation.

---

# 9. Separate Field and Documentation Performance

## 9.1 Field Performance Categories

Include areas such as:

- officer safety
- radio communication
- scene management
- investigation
- interviews
- witness development
- evidence preservation
- legal/policy articulation
- de-escalation and professionalism
- decision-making
- traffic procedure
- detention/arrest/release procedure where applicable
- CID recognition
- supervisor notification
- final disposition

## 9.2 Documentation Performance Categories

Include:

- correct paperwork selected
- completeness
- factual accuracy
- chronology
- objective writing
- persons/property accuracy
- evidence documentation
- statement documentation
- notification documentation
- legal/offense articulation
- consistency with scenario facts
- disposition accuracy
- readability

An officer may perform well in the field and poorly in documentation, or the reverse.

---

# 10. AI Is an FTO Assistant, Not the Final Evaluator

AI may generate evidence-based review suggestions, but it must not independently:

- assign official DOR ratings
- fail a trainee
- advance a trainee
- make employment decisions

The FTO remains the human evaluator.

For every AI suggestion, preserve a human-readable explanation of why it was raised.

---

# 11. Decision Reconstruction / No Hindsight Grading

For every major decision, the FTO should be able to see:

**Information available to trainee at this exact moment**

A decision should not be judged using facts revealed later.

---

# 12. FTO Intervention Tracking

Record exactly when and why an FTO intervention was required.

Differentiate:

- ordinary trainee mistake
- simulator consequence
- required FTO intervention

Track progressive independence over time, but do not turn this into an automated employment score.

---

# 13. Trainee Self-Assessment, FTO Comments, and Acknowledgement

Before viewing final FTO feedback, require a trainee self-assessment addressing what went well, what should change, key decision reasoning, safety concerns, notification requirements, and evidence priorities.

FTO review should support:

- strengths
- deficiencies
- coaching provided
- remediation
- expectations

The trainee may acknowledge the review and optionally provide comments. Acknowledgement means reviewed, not necessarily agreed.

---

# 14. Deficiency and Strength Tracking

Track confirmed deficiencies and repeated strengths across scenarios.

Deficiency categories may include field performance, investigative skills, radio, notification/CID, evidence, decision-making, and documentation.

Strengths should also be retained so the system does not become a mistake-only record.

---

# 15. Targeted Remediation

Sentinel should recommend remediation based on confirmed deficiencies.

Examples:

- weak witness development → different scenario requiring careful source identification
- weak radio updates → changing-conditions scenario
- weak documentation → paperwork-only exercise
- missed CID notification → different qualifying scenario requiring independent recognition

The FTO approves remediation assignments.

Do not simply replay the identical call unless intentionally requested. Test the same skill using different facts.

If the trainee clearly lacks knowledge of a rule, allow instruction before re-testing.

Remediation is not closed merely because a scenario was completed. The FTO must confirm that improvement was demonstrated.

---

# 16. Before-and-After Remediation Comparison

Show original versus remediation performance for relevant competencies and documentation.

Track recurring deficiencies and surface repeated patterns to the FTO/coordinator.

Generate optional FTO lesson plans with learning objective, discussion points, applicable references, practical exercise, success criteria, and re-evaluation method.

---

# 17. FTO Program Integration

From the trainee’s FTO profile, show:

- assigned scenarios
- completed scenarios
- pending paperwork
- awaiting-review packages
- field deficiencies
- paperwork deficiencies
- notification/CID deficiencies
- strengths
- remediation assignments
- completed remediation
- competency trends
- FTO comments
- trainee acknowledgements

---

# 18. Scenario Assignments and Training Packages

FTOs should be able to assign:

- specific scenario
- random scenario family
- specific competency
- remediation scenario
- full virtual shift
- paperwork-only exercise

Support phase-based packages for fundamentals, investigation, and independent decision-making, plus accelerated-program configurations where approved.

---

# 19. Phase-Dependent Autonomy

Early phases may allow Coaching Mode. Later phases should progressively reduce prompts. Final phases should require independent performance unless an intervention is necessary.

---

# 20. Exposure Tracking and Critical Skill Sign-Off

Track which call types and competencies a trainee has actually practiced.

Allow configurable minimum exposure and critical-task sign-offs.

One successful scenario does not automatically equal qualification. The FTO decides when competency has been consistently demonstrated.

Do not tell the trainee what competency a scenario is testing.

---

# 21. Final Graduation Virtual Shift

Create a capstone shift where the trainee signs on, receives a realistic mix of calls, manages interruptions and paperwork, recognizes required notifications, and completes the shift with no routine coaching.

Include at least one previously weak competency without telling the trainee.

The objective is to answer:

> Can the trainee actually perform the job?

---

# 22. Shift-Level Realism

Advanced virtual shifts should support:

- multiple calls
- held/pending calls
- prioritization
- delayed paperwork
- report backlog
- end-of-shift review
- follow-up investigations
- supplemental report exercises

The end-of-shift review should show calls handled, paperwork status, evidence status, notifications, outstanding follow-up, and lessons learned.

---

# 23. Scenario Builder

Authorized instructors should be able to create/edit scenarios without editing Python.

Configurable fields should include:

- scenario family
- dispatch
- environment
- NPCs
- NPC knowledge
- hidden facts
- evidence
- references
- possible events
- time/behavior triggers
- terminal outcomes
- competencies
- acceptable dispositions
- random variables
- difficulty
- remediation targets
- notification requirements
- paperwork requirements

---

# 24. AI-Assisted Scenario Authoring With Human Approval

AI may draft scenarios from an instructor prompt, but nothing should become assignable until an authorized human reviews and approves it.

Allow sanitized lessons learned from real incidents to be converted into synthetic training scenarios without retaining identifying or sensitive details.

---

# 25. Scenario Governance

Support scenario lifecycle states such as:

- Draft
- SME Review
- Legal/Policy Review
- Approved for Training
- Retired

FTOs should be able to flag unrealistic behavior, incorrect requirements, unclear facts, policy conflicts, or AI-response errors.

Scenario analytics should identify unusually high failure concentrations that may indicate a scenario-quality problem.

When policy changes, dependent scenarios should be easy to suspend and review.

Every run should preserve which policy/reference version was active at that time.

---

# 26. FTO Standardization / Calibration

Periodically provide FTOs the same synthetic performance package and compare how they evaluate it. Use large differences to identify FTO standardization needs.

---

# 27. FTO Coordinator Dashboard

Provide department-wide visibility into:

- active trainees
- current phases
- overdue reviews
- open remediation
- missing competencies
- upcoming completion dates
- FTO workload
- common trainee deficiencies
- common paperwork errors
- common notification/CID errors
- scenario quality trends

Include FTO workload balancing and review timeliness.

---

# 28. In-Service and Supervisor Modes

Future use should extend beyond recruits.

### In-Service

Periodic scenarios for policy refreshers, legal updates, report writing, investigations, and unusual calls.

### Supervisor

Scenarios for supervisory decision-making, scene coordination, report review, complaints, serious incidents, CID coordination, and other supervisory responsibilities.

---

# 29. Complete Training Record

Every run should preserve:

- trainee
- FTO
- date/time
- scenario family
- run seed/identifier
- dispatch
- action history
- radio traffic
- NPC conversations
- evidence discovered/missed
- records responses
- decisions
- world-state changes
- consequences
- disposition
- notifications
- paperwork selection
- submitted paperwork
- narrative
- FTO review
- strengths
- deficiencies
- remediation
- remediation result
- acknowledgement

---

# 30. Training Lifecycle

Use clear states such as:

**ASSIGNED**
→ **IN PROGRESS**
→ **CALL CLEARED**
→ **NOTIFICATIONS / PAPERWORK**
→ **TRAINEE SUBMITTED**
→ **AWAITING FTO REVIEW**
→ **FTO REVIEWED**
→ **CORRECTION REQUIRED** and/or **REMEDIATION ASSIGNED** when applicable
→ **REMEDIATION COMPLETED**
→ **FTO CLOSED**

---

# 31. Audit Trail

Record important actions such as assignment, scenario start, call clearance, notifications, paperwork selection, submission, FTO review, returned-for-correction action, revisions, remediation, and closure.

Never silently overwrite historical training actions.

---

# 32. Downloadable Training Packet

Allow authorized users to produce a consolidated training packet containing, as appropriate:

- dispatch/CAD history
- trainee actions
- conversations
- decisions
- notifications
- evidence
- paperwork
- original report
- corrected report(s)
- FTO comments
- strengths
- deficiencies
- remediation
- remediation outcome
- acknowledgement

---

# 33. Trainee Training Timeline and Analytics

Show a chronological trainee history and identify long-term trends such as repeated communication issues, witness-development problems, evidence issues, premature conclusions, strong professionalism, documentation problems, or missed notifications.

Do not expose hidden analytics during the active call.

---

# 34. Training / Operational Separation

This requirement is absolute.

Simulator reports, forms, names, case numbers, evidence, citations, vehicles, and records are synthetic training materials and must never be written into official operational records.

Use unmistakable training identifiers and labels.

---

# 35. Synthetic / Non-Sensitive Data

Do not expose restricted security information or operational vulnerabilities.

Use authorized/synthetic locations and training-safe identities, records, vehicles, and identifiers.

---

# 36. Role-Based Access

### Trainee

- work assigned training
- complete paperwork
- view released feedback
- acknowledge evaluation

### FTO

- assign approved scenarios
- observe/review assigned trainees
- return paperwork
- assign approved remediation

### FTO Coordinator

- create/edit/approve scenarios according to policy
- manage packages and competency requirements
- view program analytics

### Administrator

- agency configuration
- notification/paperwork matrices
- permissions
- retention/configuration

Trainees must not be able to view hidden scenario definitions or answers.

---

# 37. Performance Privacy and Audit Logging

Protect employee training information with role-based access, audit logs, retention rules, and clear separation from general portal data.

---

# 38. Structured Truth vs Generated Dialogue

Fundamental scenario facts must live in structured state.

The model may generate natural wording but must not invent or change core facts, evidence, records, witness knowledge, injuries, or notification requirements.

---

# 39. AI Guardrails

Test and defend against:

- hallucinated evidence
- hallucinated facts
- knowledge leakage
- future-stage leakage
- NPC coaching
- prompt injection attempts
- contradictory world states
- duplicate evidence
- actors returning after departure without cause
- impossible resource timing
- database results changing without cause
- trainees gaming keyword scoring

---

# 40. Reproducible Runs

Given the same seed and same trainee actions, core facts should remain reproducible even if dialogue wording varies.

This supports FTO review, QA, remediation comparison, and bug reproduction.

---

# 41. AI Failure Fallback and Cost Controls

The simulator should remain usable if AI service is unavailable.

Use deterministic fallback responses, structured event logic, bounded conversation history, and efficient model calls.

---

# 42. Human-Readable AI Audit Trail

For every AI review suggestion, preserve an understandable reason rather than an unexplained score.

---

# 43. Componentized Architecture

Refactor toward separate services/components for:

- scenario definitions
- world-state engine
- action interpreter
- dispatch/radio
- NPC engine
- evidence engine
- records simulator
- event/consequence engine
- requirements/notification matrix
- paperwork service
- evaluator
- FTO review
- remediation
- after-action/replay
- scenario authoring
- persistence/audit

Avoid making one route file the entire simulator.

Maintain backwards compatibility with authentication, FTO Center, reporting tools, forms, Narrative Creator, and other portal functions.

---

# 44. Live Instructor Controls

The simulator should normally run autonomously, but an authorized FTO should optionally be able to inject events such as new caller information, resource delays, witness arrival/departure, changing behavior, supervisor requests, CID responses, evidence updates, or environmental changes.

The trainee does not need to know whether the event came from the rules engine, AI, or instructor.

---

# 45. Live Instructor Observation

Allow optional live observation of:

- trainee transcript
- radio traffic
- hidden state
- NPC knowledge
- evidence state
- pending events
- competency evidence
- intervention triggers
- timeline

---

# 46. Pause, Resume, Replay, and Compare

Persist exact state so sessions can be paused/resumed.

Allow FTOs to replay runs step by step and compare original versus remediation attempts.

---

# 47. Scenario Design Principles

## Difficulty Is Not Just Danger

Advanced scenarios may be difficult because of ambiguity, conflicting information, unclear authority, simultaneous problems, time pressure, subtle evidence, competing priorities, and communication challenges.

## Include Noise

Real calls contain irrelevant information, opinions, mistakes, and false leads. The trainee should decide what matters.

## Hidden Secondary Problems

Use secondary issues carefully without turning every scenario into a trick.

## Professionalism Matters

Some scenarios should have no major enforcement action but strongly test patience, explanation, professionalism, conflict management, procedural fairness, and communication.

## Complaint Follow-Through

Where appropriate, poor communication or professionalism can lead to a later simulated complaint that can be compared against the scenario record and report.

---

# 48. Automated Testing Requirements

Add tests confirming that:

- hidden information is not revealed early
- NPC knowledge boundaries are respected
- time triggers work
- evidence can be lost
- resources take time
- equivalent natural-language actions map to equivalent intent
- keyword gaming does not earn credit
- multiple reasonable dispositions can succeed
- irreversible decisions remain irreversible
- AI failure does not break the exercise
- notification state is accurate
- paperwork fields compare correctly against scenario truth
- training data never enters operational records
- revisions preserve original submissions
- AI suggestions require human confirmation

---

# 49. Implementation Priorities

## Phase 1 — Immersion and Core Interpretation

1. Separate trainee and FTO evaluator views.
2. Hide grading/risk/branch information from trainee.
3. Build semantic action interpreter.
4. Preserve deterministic state engine as source of truth.
5. Add field notebook.
6. Add radio/CAD timeline.
7. Strengthen NPC memory/knowledge controls.

## Phase 2 — Call-to-Paperwork Workflow

1. Build authoritative MCPD requirements matrix.
2. Exclude blotter entry from trainee paperwork workflow.
3. Add CID/supervisor recognition and simulated notification.
4. Add paperwork selection.
5. Add training-only forms and narrative workflow.
6. Disable Narrative Creator during formal evaluation.
7. Add formal trainee submission and revision history.

## Phase 3 — FTO Review and Remediation

1. Build unified FTO Review workspace.
2. Add scenario-to-report comparison.
3. Add line-by-line report review.
4. Separate field and documentation evaluation.
5. Add deficiency and strength tracking.
6. Add remediation assignment and before/after comparison.
7. Add self-assessment and acknowledgement.

## Phase 4 — Virtual Shift

1. Add START SHIFT.
2. Add mixed/random dispatch calls.
3. Add pending calls, interruptions, and prioritization.
4. Add report backlog/end-of-shift review.
5. Add follow-up and supplemental investigations.
6. Add graduation virtual shift.

## Phase 5 — Program Management and Scale

1. Scenario Builder.
2. FTO phase packages.
3. Exposure/competency tracking.
4. FTO standardization/calibration.
5. Coordinator dashboard.
6. Agency-configurable terminology/policy.
7. Scenario approval/versioning/retirement.
8. In-service and supervisor modes.

---

# 50. Final Acceptance Standard

MCPD Sentinel should ultimately provide this chain:

**Dispatch**
→ **Trainee works the call independently**
→ **The simulated world reacts**
→ **Trainee recognizes required CID/supervisor notifications**
→ **Trainee makes a disposition**
→ **Trainee completes officer-required paperwork (no blotter-entry exercise)**
→ **Trainee submits the package**
→ **FTO reconstructs every decision and reviews the paperwork**
→ **Sentinel provides evidence-based review suggestions**
→ **FTO confirms strengths/deficiencies**
→ **Targeted remediation is assigned**
→ **A different scenario tests the weak skill**
→ **FTO confirms whether improvement was demonstrated**
→ **The complete training history is retained**

The product is successful when the trainee no longer feels like they are “using a training website” and instead feels like they are **working patrol, documenting the call, and being trained by an FTO**.
