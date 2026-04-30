# Mobile UX Issues

Last updated: 2026-04-30

## Root-Cause Repairs Completed

- The phone was still landing on the desktop dashboard because mobile login/dashboard routing was sending phone requests to `/dashboard`.
- The actual old homepage content lived in `app/templates/dashboard.html`, not `app/templates/mobile_home.html`.
- Mobile requests now land on `/mobile/home`, which is controlled by `app/templates/mobile_home.html`.
- The mobile home screen is now a dedicated officer screen with only:
  - `Start New Incident`
  - `Continue Incident`
  - `Laws / Orders`
  - `Quick Reference`

## Officer Flow Repairs Completed

- Statement entry is now split into smaller steps:
  - choose person
  - confirm statement details
  - capture statement content
- Domestic supplemental is no longer rendered as arbitrary 8-field chunks.
- Domestic supplemental now follows guided interview steps based on the real original form:
  - response details
  - who was involved
  - victim condition
  - victim statements
  - suspect condition
  - suspect statements
  - scene and relationship
  - prior violence and weapons
  - witnesses
  - evidence and photos
  - victim services and safety
  - medical response
  - supervisor and officer information
  - injury documentation
  - second injury documentation
- Domestic field labels are normalized on mobile so raw internal names like `VicName` and `OtherDesc` do not show up as officer-facing labels.
- Domestic conditional questions now stay hidden until the related trigger is selected.
- Domestic radio-style checkbox groups now clear correctly.
- Person entry now shows ID scanning in the main Add/Edit Person screen instead of hiding it under `More Details`.
- Live ID scanning no longer silently opens photo capture when the browser blocks camera access.
- Person entry still guarantees manual entry even when live scan input is unavailable.

## Remaining Busy Screens

- `Domestic Supplemental` is much more natural now, but it is still the densest mobile flow because the original form is large.
- `Packet Review` is functional and shorter than before, but it still summarizes the full packet and remains inherently denser than the other patrol screens.
- `Forms Used` is workable, but it still shows category metadata on each card. That is acceptable for now because it does not block the officer flow.

## Latest Repairs

- The mobile tab bar is now phase-aware while officers are inside incident intake. The active incident tab shows `Call Type`, `Basics`, `Forms`, `People`, `Facts`, `Narrative`, `Review`, or `Send` instead of a static label.
- Added a dedicated mobile `More` page so the bottom tab no longer dumps officers directly into the desktop dashboard.
- Fixed the blank `Facts Capture` screen. The mobile runtime now defines `factValueMap(state)` before `FactsCapturePage` uses it.
- The mobile home screen has been visually upgraded while preserving the strict four-action requirement.
- ID scanning remains visible in person entry, with live scanner, photo fallback, pasted barcode text, and manual entry.
- The desktop dashboard was rebuilt into an RMS/CAD-style command console with a compact header, center search, six operational action cards, and recent reports/forms lists.
- Desktop report detail now uses a split workspace so the report workflow remains on the left while law lookup, orders, and form access stay available on the right.
- The full Playwright audit crawled desktop and iPhone-sized views and captured screenshots under `mcpd-audit-results/screenshots`.

## Remaining UX Weak Points

- Some non-domestic forms still rely on the original form editor rather than fully custom patrol interviews. The safer current behavior is to preserve official form fields instead of guessing simplified interviews.
- Full live phone-camera ID scanning requires the portal to be opened over HTTPS on the phone. HTTP LAN access will show the limitation and keep manual entry/paste/photo fallback available.
- HTTP dev sessions now show an `Open Secure Scanner` action that points the officer to the HTTPS dev endpoint, so the live camera path is discoverable instead of dead-ending at the browser security warning.
- Desktop report detail now supports direct packet preview/print, download, and email actions from the report workspace.
