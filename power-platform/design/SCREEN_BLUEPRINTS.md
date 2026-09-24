# MCPD Sentinel — Screen Blueprints

These blueprints translate the approved concept image into Power Apps implementation targets.

## 1. Login / Welcome

Full-screen dark photographic/graphic background when an approved image is available.

Centered/left-middle sign-in panel:
- MCPD Sentinel
- department/installation subtitle
- **Sign in with Microsoft**
- "Authorized personnel only"

No username/password form in the government build.

## 2. Main Dashboard

Top row:
- Welcome + date
- role badge

Metric cards:
- My Open Tasks
- Pending Reviews
- Overdue Training
- Active FTO Trainees (role-dependent)

Second row:
- Recent Activity
- Department/Personal Status
- Quick Actions

Quick actions change by role.

## 3. Reports

Header:
- Reports
- New Report
- tabs: My Drafts / Submitted / Reviewed / Report Inspector

Call/report-type cards in a compact grid.

Recent reports table below.

## 4. Report Inspector

Header + Run Inspection button.

Summary cards:
- completeness cues
- approved-source matches
- review cues
- packet requirements

Tabs:
- Findings
- Approved Sources
- Packet
- Final Review

Every finding visually separates:
- Automated Cue
- Approved Source
- Human Judgment

## 5. FTO Center

Tabs:
- My Progress / Assigned Trainees
- Task Book
- DORs
- Evaluations
- Remediation
- Resources

Trainee view:
- phase
- week
- progress bar
- phase task counts
- recent evaluations
- primary FTO

FTO view:
- assigned trainees
- DOR drafts
- remediation due
- scenario reviews
- phase-review due-outs

## 6. Daily Observation Report

Top selectors:
- Trainee
- Date
- Phase
- Week
- Shift

Tabs:
- Evaluation Categories
- Task Book Items
- Comments
- Final Review

Rating section:
- grouped by Appearance / Attitude / Knowledge / Performance / Relationships
- 1–7 + N/O on each row
- expandable 1/4/7 anchor help

Bottom sections:
- most satisfactory performance
- least satisfactory performance
- category documentation
- additional narrative
- remedial minutes
- Submit to Trainee

## 7. Patrol Scenario Simulator

No quiz appearance.

Desktop layout:
- large Scene panel
- Radio/CAD panel
- Field Notebook
- Evidence/Resources panel
- natural-language Officer Action panel
- timeline

Header shows only what a trainee should know:
- dispatch time
- call location
- current simulated time/status

It does **not** show:
- difficulty/rubric during evaluation
- score
- hidden facts
- competency completion

## 8. Watch Commander / Digital Lieutenant

Tabs:
- Shift Overview
- Personnel
- Posts & Vehicles
- Events
- Turnover Brief
- Decision Log

Top metric cards:
- on duty
- absent/off duty
- leave
- training

Main cards:
- post assignments
- active events
- due-outs
- FTO remediation
- returned reports

Stale data gets prominent "STALE — VERIFY".

## 9. Analytics / Command View

Tabs:
- Training
- Reports
- FTO Program
- Operations
- Personnel

Top metrics with trend indicators.

Charts:
- report volume/type
- report correction trends
- FTO phase completion
- DOR rating trends
- training readiness
- overdue items

All Power BI data must respect row-level security and role scope.
