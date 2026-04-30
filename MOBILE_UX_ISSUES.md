# Mobile UX Issues

Last updated: 2026-04-24

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
- Person entry still guarantees manual entry even when scan input is unavailable.

## Remaining Busy Screens

- `Domestic Supplemental` is much more natural now, but it is still the densest mobile flow because the original form is large.
- `Packet Review` is functional and shorter than before, but it still summarizes the full packet and remains inherently denser than the other patrol screens.
- `Forms Used` is workable, but it still shows category metadata on each card. That is acceptable for now because it does not block the officer flow.

## Remaining UX Weak Points

- The bottom tab bar is still static instead of phase-aware.
- Non-domestic forms still rely on the original form editor rather than custom patrol interviews.
- Full live phone-camera ID scanning is still not available; the workflow relies on barcode text paste or manual entry.
