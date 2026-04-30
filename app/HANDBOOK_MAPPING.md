# Handbook Mapping

Audit date: 2026-04-24

Scope reviewed:
- `app/data/handbook/officer_handbook_source.pdf`
- `app/data/handbook/officer_handbook.json`
- `app/data/handbook/officer_handbook_generated_backup.json`
- `app/data/handbook/officer_handbook_additions.json`
- `app/routes/reference.py`
- `app/templates/officer_handbook.html`
- `app/templates/incident_paperwork_guide.html`
- `data/uploads/forms`
- `app/static/cleo`

## Current Implementation Status

- Narrative generation remains aligned to handbook-style report-writing guidance through the reviewed-draft flow in `app/services/mobile_incident_documents.py`.
- Voluntary statement generation remains aligned to handbook-style statement formatting and continues to populate the real original OPNAV statement PDFs.
- The mobile domestic supplemental flow now follows a guided interview built from the real original XFA question inventory instead of a flat field dump.
- The biggest remaining handbook-related gap is still the domestic XFA delivery path, which needs true write/flatten support for a fully faithful mobile packet export.

## Handbook Files

| File | Role in app | Notes |
| --- | --- | --- |
| `app/data/handbook/officer_handbook_source.pdf` | Authoritative handbook PDF shown and downloaded in the app | Current embedded handbook source |
| `app/data/handbook/officer_handbook.json` | Legacy handbook JSON payload | Still present, but the route logic now also relies on backup/additions payloads |
| `app/data/handbook/officer_handbook_generated_backup.json` | Structured backup used for handbook-backed supplemental content | Contains the real scenario and form-guide data currently driving the navigator |
| `app/data/handbook/officer_handbook_additions.json` | Supplemental handbook additions | Present but lightly populated |

## Handbook Section Inventory

From `officer_handbook_generated_backup.json`:

| Section ID | Title | Key content |
| --- | --- | --- |
| `introduction` | Section 1 - Introduction | Purpose, responsibilities, how to use the guide |
| `report-writing` | Section 2 - Report Writing Basics | Narrative structure, objectivity, common mistakes |
| `forms-overview` | Section 3 - Forms Overview | High-level form purposes |
| `scenario-guides` | Section 4 - Scenario-Based Paperwork Guide | `12` incident scenarios |
| `form-guides` | Section 5 - Form Completion Guides | Only `2` detailed form guides |
| `appendix-blank-forms` | Appendix A - Blank Forms | `8` handbook form names |

From `officer_handbook_additions.json`:

| Section ID | Title | Current population |
| --- | --- | --- |
| `form-completion-guide` | Form Completion Guide (Supplemental) | One short usage topic only |
| `scenario-paperwork-guide` | Scenario-Based Paperwork Guide (Supplemental) | Empty scenario list |
| `example-completed-forms` | Example Completed Forms (Supplemental) | Empty topic list |

## Handbook Form Names To Portal Form Matches

| Handbook concept | Closest portal form(s) | Match quality | Notes |
| --- | --- | --- | --- |
| `MCPD Stat Sheet` | `MCPD Stat Sheet Revision 20240711` | Strong | This is the clearest 1:1 match |
| `Incident Report` | `DD FORM 1920 ALCOHOL INCIDENT REPORT` | Weak | No generic incident report row exists |
| `Witness Statement` | `OPNAV 5580 2 Voluntary Statement`, `OPNAV 5580 2 Voluntary Statement Traffic` | Partial | Closest statement-style forms, but naming does not match handbook language |
| `Evidence / Property Forms` | `OPNAV 5580 22Evidence Custody Document` | Partial | Evidence exists; a distinct property form does not |
| `Vehicle Impound Form` | `DD Form 2506Vehicle Impoundment Report` | Strong | Clear operational match |
| `Use of Force Report` | `NAVMC 11130 Statement of Force Use of Detention` | Partial | Same workflow family, but naming differs |
| `Supplemental Report` | `NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST` | Weak | Only a scenario-specific supplemental form is present |
| `Field Interview documentation` | `OPNAV 5580 21Field Interview Card` | Strong | Closest 1:1 match |
| `Citation/notice documentation` | `UNSECURED BUILDING NOTICE` plus legacy DD-1408 reference artifacts | Weak | No dedicated DD-1408 form record is in the live form table |
| `Property Inventory` | none exact; closest is `OPNAV 5580 22Evidence Custody Document` | Weak | Missing as a canonical portal form title |
| `Juvenile-specific processing documents` | none identified as dedicated form rows | Missing | Handbook requirement is not matched by a dedicated library item |

## Scenario-To-Form Mapping

| Scenario | Handbook paperwork | Closest portal forms | Gap notes |
| --- | --- | --- | --- |
| Domestic Disturbance | Incident Report; Witness Statement(s); Use of Force Report; Evidence Form | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 2 Voluntary Statement`; `NAVMC 11130 Statement of Force Use of Detention`; `OPNAV 5580 22Evidence Custody Document`; `NAVMAC 11337 ... DOMESTIC VIOLENCE ...` | Strong domestic supplement exists, but generic incident/property naming is missing |
| Shoplifting | Incident Report; Property/Evidence Form; Witness Statement(s) | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 22Evidence Custody Document`; `OPNAV 5580 2 Voluntary Statement` | No clean property form title |
| Traffic Accident | Incident/Accident Report; Witness Statement(s); Vehicle Impound Form | `SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT`; `OPNAV 5580 2 Voluntary Statement Traffic`; `DD Form 2506Vehicle Impoundment Report`; `TA FIELD SKETCH NEW` | Best-matched scenario in current form library |
| Suspicious Person | Incident Report; Field Interview documentation; Witness Statement(s) if needed | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 21Field Interview Card`; `OPNAV 5580 2 Voluntary Statement` | Generic incident report still weak |
| Theft | Incident Report; Property Form; Evidence Form | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 22Evidence Custody Document` | Distinct property form missing |
| Assault | Incident Report; Witness Statement(s); Evidence Form | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 2 Voluntary Statement`; `OPNAV 5580 22Evidence Custody Document` | Reasonable nearest matches only |
| Drug Possession | Incident Report; Evidence Form; Property Form | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 22Evidence Custody Document`; `Field test results`; `OPNAV 5580 20 Field test results`; `USACIL DNA Database Collection Eform v2 RE` | Scenario is partly supported by evidence/testing forms |
| Lost Property | Incident Report; Property Form | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 22Evidence Custody Document` | No exact property form |
| Found Property | Incident Report; Property Form; Evidence Form | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 22Evidence Custody Document` | Same naming gap as lost property |
| Vehicle Impound | Vehicle Impound Form; Incident Report; Property Inventory | `DD Form 2506Vehicle Impoundment Report`; `DD Form 2504Abandoned Vehicle Notice`; `DD Form 2505Abandoned Vehicle Removal Authorization`; `DD Form 2507Notice of Vehicle Impoundment` | Impound family is strong; incident/property naming still weak |
| Juvenile Incident | Incident Report; Juvenile-specific processing documents; Witness/Guardian statements | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 2 Voluntary Statement` | Juvenile-specific form family is missing |
| Trespass After Warning | Incident Report; Witness Statement(s); Citation/notice documentation | `DD FORM 1920 ALCOHOL INCIDENT REPORT`; `OPNAV 5580 2 Voluntary Statement`; `UNSECURED BUILDING NOTICE` | No dedicated DD-1408 live form row even though legacy CLEO artifacts exist |

## Example And Reference Documents Found

### Legacy CLEO / Mock Report HTML pages

Static legacy report pages found under `app/static/cleo` (`22` HTML files):

- `admin-summary.html`
- `dd-1408.html`
- `desk-journal.html`
- `enclosure.html`
- `incident-admin.html`
- `index.html`
- `journal-report.html`
- `narcotics.html`
- `narrative.html`
- `narritive.html`
- `offenses-2.html`
- `offenses.html`
- `organization.html`
- `persons-2.html`
- `persons.html`
- `property.html`
- `ta-main-2.html`
- `ta-main.html`
- `ta-person-2.html`
- `ta-person.html`
- `vehicle.html`
- `violation-1408.html`

### Legacy CLEO / Mock Report PDF reference pages

Reference PDFs found under `app/static/cleo/pdfs` (`13` files):

- `1408 VIOLATION NOTICE.pdf`
- `ENCLOSURE CHECKLIST- FILLABLE.pdf`
- `involved orginization.pdf`
- `involved persons.pdf`
- `involved property.pdf`
- `main page.pdf`
- `narcotics.pdf`
- `narritive.pdf`
- `offenses.pdf`
- `TA MAIN.pdf`
- `TA PERSON FOR TRAFFICE INCIDENT.pdf`
- `traffic ticket (DD Form 1408).pdf`
- `Vehicle information.pdf`

### Other reference or example-like document assets

- `data/uploads/reconstruction/1/exports/reconstruction-case-1-packet.pdf`
- `app/generated-test-ephemeral.pdf`
- `app/generated/truck_gate_logs/2026/March/2026-03-02/truck-gate-2026-03-02.xlsx`
- `app/generated/truck_gate_logs/2026/March/2026-03-03/truck-gate-2026-03-03.xlsx`
- Seed order documents under `app/data/uploads/orders/*.txt`

## What Exists

- The handbook page already combines:
  - the authoritative PDF
  - a structured backup JSON
  - form appendix links into the form library
  - navigator routing into paperwork workflows
- The incident navigator already uses handbook-backed scenarios plus form-reference matching logic from `app/routes/reference.py`.
- The portal already has enough form coverage to support many real workflows, especially:
  - traffic accident
  - search/seizure
  - impound
  - evidence/custody
  - rights advisement
  - field interview

## What Is Missing

- No canonical 1:1 mapping exists between handbook form names and live portal forms.
- `example-completed-forms` is effectively empty right now.
- The handbook only has `2` true form guides, so most listed forms have no detailed completion guide.
- Several scenario-required form concepts are not represented as exact portal form titles.
- Legacy CLEO example assets still carry older naming and are only partially reflected in the modern library.

## What Needs Refactoring

- Create a canonical handbook-to-form registry instead of relying on text normalization and closest-match search.
- Normalize naming across:
  - handbook terminology
  - form database titles
  - legacy CLEO assets
  - modern UI labels
- Decide which legacy CLEO PDFs/HTML pages are still reference-only and which should be promoted into first-class portal workflows.
- Populate real example-completed-form content or remove that section until it is ready.
