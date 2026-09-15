# Mobile usability audit — September 15, 2026

Baseline: main at `0f747e2eb043a5bf668e29c5aee1ec2386d3bc2a`.

## Scope and method

Reviewed shared CSS, templates, navigation and client scripts, and inspected the
current public mclbpd.com landing/login UI. Authenticated UI was exercised against
the same application locally with isolated synthetic accounts and data; no live
operational records were changed. Browser regressions enumerate their exact routes
in `tests/responsive_checks.py`, plus seeded detail routes in
`tests/responsive_server.py`.

Coverage includes dashboards, FTO Center/programs/DORs, Scenario Lab (Virtual
Patrol), Virtual Shift, evaluator/review/instructor screens, notebook, scenario
paperwork and training forms, reports, both accident workflows, forms and Call
Type Paperwork management, training, law/orders/handbook, admin/accounts/profile,
BOLO, announcements, performance, and the mobile incident packet workflow.
Known retired/alias routes are checked against their intended destinations.

## Corrections

- Removed desktop sidebar width reservations from narrow page shells. Content
  no longer collapses into a tiny strip or gets clipped inside its container.
- Made the header wrap safely and measured its height to keep content below it.
  Increased controls to phone-sized targets and form text to 16px; allowed long
  labels and card contents to wrap.
- Added a drawer close button, keyboard containment, Escape/focus restoration,
  and inert closed navigation. Kept the drawer vertically scrollable and stopped
  the assistant from covering it.
- Fixed Mobile Home's vertically squeezed Menu/brand and moved the draft reminder
  below the officer name. Preserved bottom-dock behavior when editing fields.
- Corrected unreadable light-card headings and outline buttons, plus Law Lookup's
  dark-theme hero contrast and stretched search button.
- Kept adaptive tables within their containers; removed nested scroll behavior
  and made overflowing regions reachable with the keyboard.
- Changed accident tools to a compact grid, constrained the vehicle picker to the
  phone viewport, added dialog focus handling, and aligned the canvas/object layer
  during zoom and pointer placement.
- Restored existing role-scoped dashboard attention queues in a collapsed section;
  the simplified dashboard had stopped rendering them despite still computing them.
- Removed duplicate main-content IDs and irrelevant map instructions on pages
  without a map. Bumped changed asset URLs to refresh browser caches.

## Regression coverage

`python -m pytest -q tests/test_responsive_browser.py` starts a loopback-only server
with its own temporary SQLite database and synthetic signed sessions. Chromium
checks widths 320, 390, 768 and 1020px, short landscape 844×390, and the desktop
1440×900 sidebar/four-column dashboard. It checks document and descendant overflow,
clipped controls/text, tiny targets, form font size, excessive button height,
populated drafts, drawer/dialog behavior, keyboard table scrolling, diagram zoom,
and primary patrol-control ordering. Failed route checks retain screenshots.

The full existing Portal CI workflow remains enabled, with a separate responsive
browser job. JavaScript syntax checks include the affected scripts. Existing
obsolete asset-date/location assertions were aligned with the current behavior;
location tests still enforce the approved traffic/gate catalogs. External AI keys
are explicitly empty in CI so deterministic fixtures do not make live AI calls.

## Limits

- Chromium viewport tests are not physical iPhone/Safari or Android hardware tests.
  Native keyboards, dictation/microphone latency, GPS permissions and camera behavior
  still require device verification.
- Seeded authenticated data does not represent every production data combination.
  The separately restricted private credit tool returns 403 for the test account;
  its access controls were preserved, and its authenticated UI was not browser-tested.
- Wide tables and diagrams may deliberately scroll inside their own regions.
  Official printable/PDF layouts retain their document dimensions.
- Deployment status is verified separately for the final commit. This work makes
  no claim about changing mclbpd.com DNS or domain routing.
