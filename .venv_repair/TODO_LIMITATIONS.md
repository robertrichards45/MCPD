# TODO / Limitations

Last updated: 2026-04-30

## Domestic Supplemental

- The mobile domestic supplemental flow now represents the original questions in a guided order, but it still stores work as a mobile draft.
- That mobile draft is not yet written back into a saved live form record automatically.
- The original domestic form is an XFA package, and the mobile packet path still blocks delivery when it would require a non-faithful fallback export.
- Browser-safe XFA output now includes every detected field in an aligned sectioned packet with render certification, but a true Adobe dynamic XFA page-art flatten still requires Adobe/AEM tooling or a newer non-XFA official PDF source.

## ID / License Scan

- Scan support is currently partial.
- The repaired path now supports:
  - live camera barcode scanning through a bundled ZXing PDF417 reader
  - pasted/raw AAMVA barcode text
  - photo fallback only when the officer explicitly taps `Photo Fallback`
- It maps scan results into:
  - name
  - DOB
  - address
  - ID number
  - state
- Every scanned field remains editable before save.
- The workflow never blocks if scan parsing fails.
- Live camera scanning on a phone requires HTTPS, camera permission, browser media access, and a readable PDF417 barcode in view. HTTP over a LAN IP cannot open live camera scanning in modern mobile browsers.
- The app now states this limitation directly and provides a dedicated `Open Secure Scanner` launcher for HTTP dev sessions, instead of silently falling back to photo capture.
- Manual correction is still required when the barcode is damaged or partially read.
- Manual entry is the guaranteed reliable fallback.

## Law Lookup

- Law Lookup now uses a scenario interpretation layer before ranking results. It extracts conduct, location/base context, threats, property, drugs, military-order facts, domestic context, and jurisdiction clues from the whole officer narrative.
- Regression coverage now includes long/plain-language officer scenarios plus 500+ direct code/title/summary/keyword route checks.
- The search remains limited to the structured corpus loaded in the portal. If Georgia, Federal USC, UCMJ, base-order, punishment, or local-policy source data is incomplete, results must continue to say so instead of fabricating citations or penalties.

## Voluntary Statements

- The mobile statement flow now uses the real original OPNAV forms and stamps initials/signatures into the actual statement blocks.
- Those signatures are image placements, not cryptographic PDF signatures.

## Packet Delivery

- Packet send still depends on SMTP being configured correctly.
- Packet validation now blocks clearly on missing narrative approval, missing people, missing required signatures/initials, and incomplete selected forms.
- Domestic supplemental remains the main packet-delivery blocker because of the XFA limitation above.

## Desktop Report Workspace

- Desktop reports now use a saved RMS-style workflow with report type, parties, facts, narrative, blotter, paperwork, and notes.
- Facts/narrative are persisted on the report record and submit is blocked until those required items exist.
- The desktop report workspace includes a right-side authority panel for law/forms/orders access while the report remains open.
- The built-in narrative/blotter generator is intentionally conservative. It restructures officer-entered facts for review, but it does not invent evidence, statements, charges, or disposition.
- Desktop report workspace now has direct packet `Preview / Print`, `Download`, and `Email Packet` actions. Email uses SMTP when configured and shows a mailto fallback if SMTP is unavailable.

## Form Coverage

- The original form mapping layer is broadly repaired, but most forms still use the original form editor instead of a dedicated patrol-specific interview flow.
- That is functionally correct, but some high-use forms may still deserve future mobile-specific interviews.
- Desktop online fill now preserves extracted PDF/XFA field order and uses PDF tooltip/caption labels when available instead of alphabetizing raw technical field names.
- Browser downloads/previews for dynamic XFA forms now use a portal-generated compatible PDF so the browser no longer shows the Adobe `Please wait...` shell.
- The compatible XFA render now uses a clean sectioned official-question layout instead of unreliable XFA coordinates and adds a render certification block. This fixes the visible alignment problem in browser-generated PDFs, but it is still not the same as a true Adobe XFA flatten of the original page art.
- DLA/NFOL currently states that digital forms are being moved to DSO/Navy Digital Storefront. When those current copies are available, replace any old Adobe-wait source PDFs with the newest official usable copies and rerun form mapping verification.
- Forms Manager now supports official source URL tracking and direct official PDF update checks. DSO storefront/login pages are detected as gated and will not be applied as form replacements.
- Scheduled form updates are available through `scripts/check_form_source_updates.py --apply`, but only for forms with auto-update enabled and a direct official PDF URL.
- Some original PDFs do not expose meaningful captions for every field. The worst remaining label-review items are DD Form 2504, DD Form 2505, DD Form 2506, DD Form 2507, and DD Form 2701, where Adobe/XFA metadata still exposes generic names like `TextField2` for some inputs.
- Those forms should be manually reviewed in Forms Manager / Template Editor and given curated UI labels where the source PDF does not provide usable label text.

## Technical Follow-Up

- App/test references to `datetime.utcnow()` were replaced with timezone-based UTC helpers during the 2026-04-30 repair pass.
- `pypdf` / `cryptography` ARC4 warnings are third-party dependency noise and are filtered in `pytest.ini`; update those libraries when compatible newer versions are available.
- The full Playwright audit now writes `mcpd-audit-results/MCPD_SITE_AUDIT.md`, `mcpd-audit-results/MCPD_FIX_PLAN.md`, and screenshots for desktop plus iPhone-sized passes.
- Very long mobile pages can exceed browser full-page screenshot limits; the audit saves a viewport fallback screenshot and treats that as a warning, not a site failure.

## Form Interviews

- All active forms still route through the official form editor / renderer so source fields are preserved.
- Dedicated patrol interviews currently exist for high-risk mobile flows such as Domestic Supplemental and Voluntary Statements.
- Future work: build dedicated custom interviews for the highest-use non-domestic forms one at a time, using the form audit as the source of truth. Do not replace official field coverage with simplified approximations.
