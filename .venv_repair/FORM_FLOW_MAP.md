# Form Flow Map

Audit date: 2026-04-24

## Purpose

This file maps each original form to the current officer-facing flow used to gather answers and populate the original document.

## Root-Cause Summary

- The phone workflow problems were not coming from the original PDFs themselves.
- The real issues were in the live runtime file `app/static/mobile/incident-core.js`, where:
  - domestic supplemental was being chunked mechanically instead of interviewed naturally
  - statement entry mixed setup and content into one crowded screen
  - domestic radio groups were not behaving correctly
- The original-form population logic lives separately in:
  - `app/services/forms_pdf_renderer.py`
  - `app/services/mobile_incident_documents.py`

## Bespoke Mobile Interview Flows

| Original form | Mobile flow sections | Questions in order | Reused fields from incident/person data | Conditional questions | Output mapping status | Duplicate/repeating issues fixed | Remaining limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST | Guided domestic interview | Response details -> Who was involved -> Victim condition -> Victim statements -> Suspect condition -> Suspect statements -> Scene and relationship -> Prior violence and weapons -> Witnesses -> Evidence and photos -> Victim services and safety -> Medical response -> Supervisor and officer information -> Injury documentation -> Second injury documentation | Victim name, response date/time, reporting officer, injury-name defaults | `Who` only when `Other` is selected; `Where` only when `Other location` is selected; address/leave details only when those options are selected; medical detail fields only when the matching treatment option is selected; injury explanation fields only when `Other (Explain)` is selected | Partial | Removed raw 8-field chunking; moved victim/suspect statement fields into natural groups; fixed radio-group clearing bug; reduced repeated person/basic fields by prefill and reuse | Mobile draft still does not flatten back into the live XFA packet path automatically |
| OPNAV 5580 2 Voluntary Statement | Guided statement flow | Choose person -> Confirm statement details -> Enter plain-language statement -> Review formatted statement -> Capture initials/signatures -> Populate original form | Selected person name and SSN, incident location, incident date/time, statement subject fallback from incident basics/facts | More-details fields only when needed; signature capture enforced before packet readiness | Yes | Removed repeated speaker/setup fields from the content screen; separated person selection from content capture | Still uses image overlays for initials/signatures rather than cryptographic PDF signatures |
| OPNAV 5580 2 Voluntary Statement Traffic | Guided statement flow | Choose person -> Confirm statement details -> Answer traffic interview prompts -> Review formatted statement -> Capture initials/signatures -> Populate original form | Selected person name and SSN, incident location, incident date/time, incident subject fallback | Traffic prompt list only appears for traffic statement variant | Yes | Removed mixed setup/content flow and kept traffic prompts on their own content step | Same signature limitation as the standard statement |

## Original-Form Editor Flows

These forms currently use the original form editor and schema-backed fill flow instead of a custom mobile interview. That is intentional unless a dedicated officer interview is called for.

| Original form | Mobile flow sections | Questions in order | Reused fields from incident/person data | Conditional questions | Output mapping status | Duplicate/repeating issues fixed | Remaining limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5580 9 Command search authorization | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| 5580 16 PERMISSIVE AUTHORIZATION FOR SEARCH AND SEIZURE | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2708Receipt for Inmate or Detained Person | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| ENCLOSURE CHECKLIST FILLABLE | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| Field test results | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| MCPD Stat Sheet Revision 20240711 | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| NAVMC 11130 Statement of Force Use of Detention | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| OPNAV 5580 3 Military Suspects Rights | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| OPNAV 5580 4 Civilian Suspects Rights | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| Affidavit for Seach and Seizure | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| OPNAV 5580 21Field Interview Card | Original form editor | Original PDF field order | Person reuse can be manual today | Handled by original schema/form | Fixed | N/A | Better person-to-form autofill can still be added later |
| OPNAV 5580 8 TELEPHONIC THREAT COMPLAINT | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| OPNAV 5580 9 Command search authorization | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Duplicate family of ID 1 |
| OPNAV 5580 10 Affidavit for Seach and Seizure | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Duplicate family of ID 13 |
| OPNAV 5580 11 COMPLAINT OF STOLEN MOTOR VEHICLE | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| OPNAV 5580 12 DON VEHICLE REPORT | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| OPNAV 5580 16 PERMISSIVE AUTHORIZATION FOR SEARCH AND SEIZURE | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Duplicate family of ID 2 |
| OPNAV 5580 20 Field test results | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Duplicate family of ID 5 |
| OPNAV 5580 22Evidence Custody Document | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Strong candidate for later patrol interview flow |
| SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Strong candidate for later patrol interview flow |
| DD FORM 1920 ALCOHOL INCIDENT REPORT | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | Generic incident-report naming mismatch remains at product level |
| TA FIELD SKETCH NEW | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| UNSECURED BUILDING NOTICE | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| USACIL DNA Database Collection Eform v2 RE | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2341 Report of Animal Bite Potential Rabies Exposure | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2504Abandoned Vehicle Notice | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2505Abandoned Vehicle Removal Authorization | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2506Vehicle Impoundment Report | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2507Notice of Vehicle Impoundment | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |
| DD Form 2701 VWAP | Original form editor | Original PDF field order | None specialized | Handled by original schema/form | Fixed | N/A | No bespoke patrol interview |

## Duplicate / Repeating Flow Repairs

- Statement flow no longer repeats person-selection and setup details on the content screen.
- Domestic flow no longer dumps repeated generic `Other`, `Name`, and raw field-code prompts in arbitrary chunks.
- Incident/person basics are now reused in domestic and statement flows instead of being re-entered everywhere they are needed.

## Manual Review Still Needed

- Domestic supplemental still needs a real XFA save/flatten path before the mobile packet can attach that original form directly.
- Non-domestic forms still use the original editor flow rather than dedicated patrol interviews; that is functional, but some of them may deserve future mobile-specific interviews.
