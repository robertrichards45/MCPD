# Form Audit

Audit date: 2026-04-30

## Scope

- Original form assets under `data/uploads/forms`
- Live form renderer in `app/services/forms_pdf_renderer.py`
- Mobile packet document generation in `app/services/mobile_incident_documents.py`
- Live mobile runtime in `app/static/mobile/incident-core.js`
- Form catalog generation in `app/services/mobile_form_catalog.py`

## Current Truth

- Active original forms in the live library: `33`
- Core renderer mapping status: repaired
- Voluntary statement original PDF population: repaired
- Domestic supplemental mobile interview flow: repaired to represent the original questions in a guided sequence
- Domestic supplemental mobile packet delivery: still blocked by true XFA write/flatten limitations
- Desktop online fill order/labels: repaired to follow extracted PDF/XFA field order and PDF tooltip/caption labels where available
- Dynamic XFA browser compatibility: repaired so blank preview/download uses a portal-compatible sectioned PDF instead of the Adobe `Please wait...` shell or unreliable XFA coordinate placement

## Root-Cause Findings

- The biggest original-form population defects were in the renderer layer:
  - exact field-name collisions were mapping to the wrong targets
  - malformed checkbox widgets could fail on `/AP` lookup
  - some forms needed a manual widget-value fallback
  - desktop fill screens were preserving field coverage but could still feel wrong because inferred fields were sorted alphabetically instead of source-PDF order
  - some AcroForm labels were falling back to raw technical field names even when the PDF exposed better tooltip text
- The biggest mobile form-flow defects were in the runtime layer:
  - domestic supplemental was being dumped into arbitrary 8-field chunks instead of a guided interview
  - statement entry mixed person selection, statement metadata, and content capture on one screen
  - domestic radio-style checkbox groups were not clearing correctly because the runtime passed the wrong object into the radio-group helper

## Per-Form Status

| ID | Form name | All original questions represented | All original fields mapped | Output populates original form correctly | Missing items | Broken items | Repair status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5580 9 Command search authorization | Yes | Yes | Yes | None | None | Fixed |
| 2 | 5580 16 PERMISSIVE AUTHORIZATION FOR SEARCH AND SEIZURE | Yes | Yes | Yes | None | None | Fixed |
| 3 | DD Form 2708Receipt for Inmate or Detained Person | Yes | Yes | Yes | None | None | Fixed |
| 4 | ENCLOSURE CHECKLIST FILLABLE | Yes | Yes | Yes | None | None | Fixed |
| 5 | Field test results | Yes | Yes | Yes | None | None | Fixed |
| 6 | MCPD Stat Sheet Revision 20240711 | Yes | Yes | Yes | None | None | Fixed |
| 7 | NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST | Yes | Yes | Compatible sectioned output | None in guided mobile flow | Exact Adobe XFA page-art flatten still unavailable; browser output now aligned as sectioned official-question packet | Partially fixed |
| 8 | NAVMC 11130 Statement of Force Use of Detention | Yes | Yes | Compatible sectioned output | None | Exact Adobe XFA page-art flatten still unavailable; browser output now aligned as sectioned official-question packet | Partially fixed |
| 9 | OPNAV 5580 3 Military Suspects Rights | Yes | Yes | Yes | None | None | Fixed |
| 10 | OPNAV 5580 4 Civilian Suspects Rights | Yes | Yes | Yes | None | None | Fixed |
| 11 | OPNAV 5580 2 Voluntary Statement | Yes | Yes | Yes | None | None | Fixed |
| 12 | OPNAV 5580 2 Voluntary Statement Traffic | Yes | Yes | Yes | None | None | Fixed |
| 13 | Affidavit for Seach and Seizure | Yes | Yes | Yes | None | None | Fixed |
| 14 | OPNAV 5580 21Field Interview Card | Yes | Yes | Yes | None | None | Fixed |
| 15 | OPNAV 5580 8 TELEPHONIC THREAT COMPLAINT | Yes | Yes | Yes | None | None | Fixed |
| 16 | OPNAV 5580 9 Command search authorization | Yes | Yes | Yes | None | None | Fixed |
| 17 | OPNAV 5580 10 Affidavit for Seach and Seizure | Yes | Yes | Yes | None | None | Fixed |
| 18 | OPNAV 5580 11 COMPLAINT OF STOLEN MOTOR VEHICLE | Yes | Yes | Yes | None | None | Fixed |
| 19 | OPNAV 5580 12 DON VEHICLE REPORT | Yes | Yes | Yes | None | None | Fixed |
| 20 | OPNAV 5580 16 PERMISSIVE AUTHORIZATION FOR SEARCH AND SEIZURE | Yes | Yes | Yes | None | None | Fixed |
| 21 | OPNAV 5580 20 Field test results | Yes | Yes | Yes | None | None | Fixed |
| 22 | OPNAV 5580 22Evidence Custody Document | Yes | Yes | Yes | None | None | Fixed |
| 23 | SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT | Yes | Yes | Yes | None | None | Fixed |
| 24 | DD FORM 1920 ALCOHOL INCIDENT REPORT | Yes | Yes | Yes | None | None | Fixed |
| 25 | TA FIELD SKETCH NEW | Yes | Yes | Yes | None | None | Fixed |
| 26 | UNSECURED BUILDING NOTICE | Yes | Yes | Yes | None | None | Fixed |
| 27 | USACIL DNA Database Collection Eform v2 RE | Yes | Yes | Compatible sectioned output | None | Exact Adobe XFA page-art flatten still unavailable; browser output now aligned as sectioned official-question packet | Partially fixed |
| 28 | DD Form 2341 Report of Animal Bite Potential Rabies Exposure | Yes | Yes | Yes | None | None | Fixed |
| 29 | DD Form 2504Abandoned Vehicle Notice | Yes | Yes | Compatible sectioned output | Source XFA exposes generic labels like `TextField2`; needs DSO/DLA replacement or manual labels | Exact Adobe XFA page-art flatten still unavailable; browser output now aligned as sectioned official-question packet | Partially fixed |
| 30 | DD Form 2505Abandoned Vehicle Removal Authorization | Yes | Yes | Compatible sectioned output | Source XFA exposes generic labels like `TextField2`; needs DSO/DLA replacement or manual labels | Exact Adobe XFA page-art flatten still unavailable; browser output now aligned as sectioned official-question packet | Partially fixed |
| 31 | DD Form 2506Vehicle Impoundment Report | Yes | Yes | Yes | None | None | Fixed |
| 32 | DD Form 2507Notice of Vehicle Impoundment | Yes | Yes | Yes | None | None | Fixed |
| 33 | DD Form 2701 VWAP | Yes | Yes | Yes | None | None | Fixed |

## Repairs Made In This Pass

- Repaired desktop online fill generation so inferred fields follow the original PDF/XFA field order instead of alphabetical order.
- Repaired AcroForm field extraction to use tooltip/alternate labels and widget positions when available.
- Cleaned long statement-line labels into readable row labels such as `Statement Row 1`.
- Filtered PDF/XFA control fields such as `SaveButton`, `CurrentPage`, `PageCount`, and reset controls so they no longer appear as officer input fields.
- Repaired dynamic XFA blank preview/download behavior by generating a browser-compatible sectioned PDF instead of serving the raw Adobe XFA shell or drawing fields with unreliable dynamic XFA coordinates.
- Repaired original PDF field targeting so exact names win before normalized fuzzy matching.
- Added a manual widget-value fallback for malformed fillable widgets that were failing on checkbox/write operations.
- Kept voluntary statement output on the real OPNAV originals and continued placing initials/signatures onto the actual statement blocks.
- Rebuilt the domestic supplemental phone flow around real original questions instead of raw field chunks.
- Fixed domestic radio-group behavior so mutually exclusive checkbox groups now clear correctly.

## Remaining Manual Review

- Some PDFs do not expose meaningful field captions for every input. DD Form 2504, DD Form 2505, DD Form 2506, DD Form 2507, and DD Form 2701 still need manual Template Editor review for generic labels exposed by the source PDFs.
- Domestic supplemental still needs a true XFA write/flatten pipeline before the mobile packet path can deliver that original form directly without blocking.
- Current DLA/NFOL guidance says digital forms are moving to the DSO/Navy Digital Storefront. Any newly available official copies should be used to replace old Adobe-wait shells before final field-placement certification.
- A final visual human review of the domestic supplemental XFA output path is still required once true flatten support exists.
