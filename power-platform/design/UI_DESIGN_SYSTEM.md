# MCPD Sentinel — Approved Visual Design System

## Status

The dark MCPD Sentinel concept shown to the owner on 24 Sep 2026 is the approved visual target.

Future Power Apps screens should look and feel like that concept unless the owner requests a change.

## Visual identity

- Dark navy / near-black application shell.
- Bright blue primary action color.
- Thin blue/steel borders rather than heavy card outlines.
- High-information-density desktop layout without looking cluttered.
- Left navigation rail on desktop.
- Compact top command/search bar.
- Role and user identity visible in the upper-right.
- White primary typography with subdued blue-gray secondary text.
- Status chips use semantic color only as a supplement to text.
- Cards use subtle elevation and border separation.
- Rounded corners are moderate; avoid oversized consumer-app pill styling.
- Police/USMC branding is professional and restrained.

## Approved screen feel

The following screens should visually match the approved concept:

1. Login / Welcome
2. Main role-based Dashboard
3. Reports
4. Report Inspector
5. FTO Center — trainee/FTO views
6. Daily Observation Report
7. Patrol Scenario Simulator
8. Watch Commander / Digital Lieutenant
9. Analytics / Command view

## Desktop shell

### Top bar
- Height target: 60–68 px equivalent.
- Left: MCPD Sentinel wordmark.
- Center: global search when applicable.
- Right: signed-in user, rank/title, role, account menu.

### Sidebar
- Width target: 210–240 px.
- Fixed on desktop.
- Icons + labels.
- Current module receives a blue active treatment.
- Role-inaccessible items are hidden, not disabled.
- Keep original Sentinel navigation simple.

### Content
- Maximum useful width should expand for dashboard/analytics pages.
- Standard page gutters: 20–28 px.
- 12-column responsive grid concept.
- Cards commonly use 2, 3, or 4-column layouts.

## Mobile/tablet

- Sidebar collapses into a drawer.
- Top search can collapse to an icon or move below the header.
- Dashboard cards become 1–2 columns.
- DOR rating rows become stacked category cards.
- Scenario simulator keeps Radio, Scene, Notes, and Action controls reachable without horizontal scrolling.
- Touch targets must be comfortable on government tablets.

## Color tokens

Exact implementation values may be adjusted to meet government accessibility requirements, but use these as the visual baseline:

- App background: #06111D
- Shell/nav background: #081725
- Card background: #0C1B2A
- Raised card: #102235
- Border: #1D3A52
- Primary blue: #147DFF
- Primary hover: #3592FF
- Text primary: #F4F8FC
- Text secondary: #98AABD
- Muted text: #6E8297
- Success: #2BC66D
- Warning: #F2B84B
- Danger: #F05B63
- Info: #37A7FF

## Typography

Use a Microsoft-available system family in the Power App.

Preferred:
- Segoe UI
- Arial fallback

Hierarchy:
- App/page title: 26–30
- Section title: 18–22
- Card metric: 24–34
- Standard body: 14–16
- Metadata: 12–13

## Interaction patterns

- Primary action: solid blue button.
- Secondary action: dark button with blue border.
- Destructive action: danger treatment plus confirmation.
- Tabs: contained horizontal tabs with clear active state.
- Search: persistent at top of data-heavy modules.
- Tables: dark rows, subtle separators, sticky header where possible.
- Filters: compact chips/dropdowns above results.
- Empty state: plain-language explanation and one useful next action.

## Status language

Prefer explicit text:
- Draft
- Submitted
- Reviewed
- Returned
- Approved
- Overdue
- Active
- Completed
- STALE — VERIFY

Never communicate a critical state by color alone.

## Product-specific rules

### Report Inspector
Findings use a clear three-part visual:
1. Automated cue
2. Approved source
3. Human judgment

### DOR
The 1–7 scale must fit on one row on desktop. "N/O" is a distinct control. Low ratings must not be visually hidden.

### Scenario Simulator
The trainee's screen feels operational, not like a quiz. No score meters or hidden rubric information during an evaluation.

### Watch Commander
Data freshness is visually prominent. Stale controlled data must show "STALE — VERIFY".

### Analytics
Metrics use large values, short labels, and drill-down charts. Avoid decorative charts with no operational value.

## Branding rule

The design may use authorized department/USMC marks only after the government owner confirms approved assets and usage. Development prototypes may use a neutral shield placeholder.
