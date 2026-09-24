# MCPD Sentinel — Full Original Portal Feature Inventory

## Scope decision

The rebuild scope is now **everything that existed in the original MCPD Portal before the later design/removal changes**, plus the original MCPD Sentinel/FTO work and the uploaded FTO manual requirements.

The current live website is not the functional baseline. Later removals do not remove features from this rebuild unless the owner explicitly asks to remove them again.

## Original portal capabilities to preserve

### 1. Authentication & Account Management
- Microsoft/Entra sign-in in the Power Platform version
- CAC/PIV-compatible government identity path where supported by the tenant
- role-based access control
- pending-account approval
- multiple roles per user
- role/context switching where needed
- Watch Commander scope
- officer profile data
- emergency contacts
- account recovery/reset workflow appropriate to Microsoft identity

### 2. Dashboard
- role-aware home dashboard
- customizable/role-specific widgets
- quick access
- recent reports
- saved work
- training visibility
- Watch Commander summary
- responsive desktop/mobile layout

### 3. Incident Reporting — Desktop
- create/edit incident reports
- dynamic structured fields
- attachments and photos
- device-camera capture where supported
- multiple involved persons
- multiple/co-author officers
- AI-assisted narrative drafting
- draft auto-save
- supervisor submission
- return-for-correction workflow
- grading/review/approval
- report status tracking

### 4. Mobile Incident Reporting
- mobile drafts
- one-step-at-a-time guided flow
- incident details
- statute selection
- involved persons
- facts/narrative
- statement collection
- digital signature capture where approved
- domestic supplemental
- smart form suggestions
- narrative suggestions
- recommended paperwork/forms
- packet review/transmission
- supervisor review
- fast-capture mode
- critical-incident mode
- mobile statistics

### 5. Forms Library & Management
- searchable forms library
- blank form download
- web-based form filling
- incident-data prefill
- saved progress
- PDF generation
- email/download/print where allowed
- statement compact view
- saved form management
- personal/team/department access scope
- official-source update tracking
- PDF field mapping/calibration tools
- render debugging/validation
- Call Type Paperwork Manager
- retention/PII controls
- Forms Manager

### 6. Legal Reference System
- Georgia law
- UCMJ
- federal USC
- base orders/local references
- natural-language search
- AI query expansion where approved
- incident classification assistance
- full source text/reference
- export/import
- legal analytics
- query logs
- federal-source review/editing
- weak-query analysis
- preferred-state setting

### 7. Orders & Memoranda
- browse/search
- source metadata
- download
- AI simplification
- bookmarks/favorites
- audience/topic tags
- source/version management
- source ingestion
- supersession tracking
- metadata extraction/confidence
- help/reference interface

### 8. Training Management
- roster upload
- roster distribution
- digital signatures
- completion tracking
- search
- qualification tracker
- readiness/compliance
- training record log
- documentation upload
- export
- roster print/download

### 9. Bodycam Footage Management
- footage metadata
- playback/timeline
- download where authorized
- report attachment linkage
- narrative creator
- 5-W Builder
- search/filter
- mobile access
- transcript support where approved

**Operational note:** inclusion in the rebuild does not mean browser-captured/video/transcript material is approved as official evidence. Government cybersecurity, records, evidence, and command approval remain required.

### 10. BOLO System
- person/vehicle/property BOLO
- photos
- detail/edit
- located status
- cancel/close
- search/filter

### 11. Personnel Management
- searchable officer directory
- profile editing
- profile photos
- emergency contacts
- exports
- installation view
- role assignment
- supervisor assignment
- pending approval

### 12. Performance Evaluation
- evaluation element definitions
- personal performance history
- performance statistics
- annual submission
- supervisor approve/reject
- team overview
- year-end/reset workflow

### 13. Accident Reconstruction
- reconstruction cases
- interactive diagram
- vehicles/objects/measurements
- speed/damage details
- distance/angle tools
- timeline
- photos/evidence
- multi-vehicle support
- PDF packet export

### 14. Operational Modules
#### Armory
- asset inventory
- weapon/equipment assignment
- check-out/check-in
- identity/PIN/CAC controls where approved
- officer cards
- bulk import/export

#### RFI
- firearm/ammunition tracking
- officer RFI profiles
- command-level defaults
- appointment letters
- transactions/export

#### Truck Gate
- vehicle entry/exit
- daily log workbook
- companies/drivers/vehicles
- imports with validation
- QR labels/scanning

#### Vehicle Inspections
- digital inspection forms
- PDF overlay/calibration
- electronic signature
- correction/return workflow
- CSV/JSON/ZIP export
- batch print

### 15. CLEO Structured Reporting
- Incident Admin
- Persons
- Property
- Vehicle
- Offenses
- Narrative
- CCN generation
- Draft -> Submitted -> Returned -> Graded
- file upload
- field-level feedback
- grading
- return/resubmission
- report summary

### 16. Statistics & Activity Tracking
- officer activity upload
- officer dashboard
- configurable categories
- targets
- history/trends
- export

### 17. Announcements
- create/publish
- pin
- visibility toggle
- archive

### 18. Watch Commander Tools
- live/controlled shift overview
- shift creation/editing
- officer assignments
- active roster
- report review/approval queue
- incident packet status
- training/forms oversight
- activity blotter
- pending approvals
- shift briefings
- briefing acknowledgment
- notifications
- original Sentinel Digital Lieutenant decision support
- turnover brief
- decision log
- data freshness / STALE — VERIFY

### Assistant Operations
- command due-out tracker
- training tasks
- inspections
- suspense items
- projects
- assignment to Lt/Sgt/Watch Commander
- status/comments/completion tracking
- department-level oversight

### 19. AI Assistant & Tools
- text assistant
- voice input/output where approved
- counseling document drafting
- awards recommendation drafting
- annual training assistant
- legal query expansion
- narrative drafting
- order simplification
- smart form suggestions
- learning submission/approval
- officer file management
- original Sentinel grounding rules and human-review boundary

### 20. Reference Materials
- Officer Handbook
- PDF/email/print/download
- content/version management
- Incident Paperwork Guide
- call-type paperwork navigator
- guide administration

### 21. Data Export & Import
- CSV exports/imports
- PDF exports/imports
- JSON exports/imports
- ZIP bundles
- Excel workbooks
- module-specific migration/archival tools

### 22. Security / Administration / Builder
- Entra/Microsoft identity in the Power Platform implementation
- Dataverse role/security model
- restricted administration
- Site Owner / Builder-equivalent controls
- legal corpus administration
- forms administration
- analytics administration
- audit/accountability
- tenant/environment configuration
- data-retention flags
- secure government deployment design

## Original Sentinel additions preserved

The portal inventory above is combined with the original Sentinel functions:
- Action Center
- Report Inspector
- approved-source grounding
- FTO Instructor & Evaluator
- standard 8-week / accelerated 4-week FTO programs
- DORs
- digital task book
- remedial training/re-evaluation
- Scenario Lab / patrol simulation
- Watch Commander / Digital Lieutenant
- role-aware department analytics

## Visual rule

Preserve **all original functionality**, but render it in the approved dark-blue MCPD Sentinel design instead of copying the later live-site appearance.
