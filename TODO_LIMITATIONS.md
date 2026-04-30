# TODO / Limitations

Last updated: 2026-04-30

## Domestic Supplemental

- The mobile domestic supplemental flow now represents the original questions in a guided order, but it still stores work as a mobile draft.
- That mobile draft is not yet written back into a saved live form record automatically.
- The original domestic form is an XFA package, and the mobile packet path still blocks delivery when it would require a non-faithful fallback export.
- A true XFA write/flatten implementation is still required for fully faithful mobile packet delivery of the domestic original form.

## ID / License Scan

- Scan support is currently partial.
- The repaired path now supports:
  - live camera barcode scanning through a bundled ZXing PDF417 reader
  - pasted/raw AAMVA barcode text
- It maps scan results into:
  - name
  - DOB
  - address
  - ID number
  - state
- Every scanned field remains editable before save.
- The workflow never blocks if scan parsing fails.
- Live camera scanning still depends on camera permission, browser media access, and a readable barcode in view; manual correction is still required when the barcode is damaged or partially read.
- Manual entry is the guaranteed reliable fallback.

## Voluntary Statements

- The mobile statement flow now uses the real original OPNAV forms and stamps initials/signatures into the actual statement blocks.
- Those signatures are image placements, not cryptographic PDF signatures.

## Packet Delivery

- Packet send still depends on SMTP being configured correctly.
- Packet validation now blocks clearly on missing narrative approval, missing people, missing required signatures/initials, and incomplete selected forms.
- Domestic supplemental remains the main packet-delivery blocker because of the XFA limitation above.

## Form Coverage

- The original form mapping layer is broadly repaired, but most forms still use the original form editor instead of a dedicated patrol-specific interview flow.
- That is functionally correct, but some high-use forms may still deserve future mobile-specific interviews.
- Desktop online fill now preserves extracted PDF/XFA field order and uses PDF tooltip/caption labels when available instead of alphabetizing raw technical field names.
- Browser downloads/previews for dynamic XFA forms now use a portal-generated compatible PDF so the browser no longer shows the Adobe `Please wait...` shell.
- The compatible XFA render now uses a clean sectioned official-question layout instead of unreliable XFA coordinates. This fixes the visible alignment problem in browser-generated PDFs, but it is still not the same as a true Adobe XFA flatten of the original page art.
- DLA/NFOL currently states that digital forms are being moved to DSO/Navy Digital Storefront. When those current copies are available, replace any old Adobe-wait source PDFs with the newest official usable copies and rerun form mapping verification.
- Forms Manager now supports official source URL tracking and direct official PDF update checks. DSO storefront/login pages are detected as gated and will not be applied as form replacements.
- Scheduled form updates are available through `scripts/check_form_source_updates.py --apply`, but only for forms with auto-update enabled and a direct official PDF URL.
- Some original PDFs do not expose meaningful captions for every field. The worst remaining label-review items are DD Form 2504, DD Form 2505, DD Form 2506, DD Form 2507, and DD Form 2701, where Adobe/XFA metadata still exposes generic names like `TextField2` for some inputs.
- Those forms should be manually reviewed in Forms Manager / Template Editor and given curated UI labels where the source PDF does not provide usable label text.

## Technical Follow-Up

- `datetime.utcnow()` deprecation warnings still appear in the Python app/test path.
- `pypdf` / `cryptography` ARC4 deprecation warnings still appear during tests.
