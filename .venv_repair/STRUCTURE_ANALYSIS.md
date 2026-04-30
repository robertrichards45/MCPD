# Structure Analysis

Audit date: 2026-04-12

Scope reviewed:
- root project layout
- `app/__init__.py`
- `app/config.py`
- `app/extensions.py`
- `app/models.py`
- all route files in `app/routes`
- shared templates and major workflow templates
- `app/static/js/app.js`
- `app/static/cleo/cleo_report.js`
- handbook, forms, legal, orders, and example document assets

## High-Level Build

This project is a modular Flask application with server-rendered Jinja templates, SQLite persistence through SQLAlchemy, and a mixed front-end model:

- the main portal is rendered server-side
- role/scope state is handled in Flask session plus Flask-Login
- most workflow persistence is in SQLite
- the legacy CLEO/mock-report area uses static HTML plus browser-side JavaScript with `fetch` and `localStorage`

There is no React, Vue, Redux, or other front-end state framework in the codebase.

## Current Project Structure

### Core application

- `app/__init__.py`
  - app factory
  - schema patching on startup
  - blueprint registration
  - security headers and proxy handling
- `app/config.py`
  - environment-driven configuration
  - database path
  - upload roots
  - auth/proxy/CAC settings
- `app/extensions.py`
  - `db`
  - `login_manager`
- `app/models.py`
  - user, role, forms, reports, orders, training, stats, profile, CLEO/mock-report, and ops-module persistence
- `app/permissions.py`
  - role/scope helper logic

### Domain routes

- `auth.py`
- `dashboard.py`
- `forms.py`
- `training.py`
- `stats.py`
- `annual_ai.py`
- `admin.py`
- `cleo_api.py`
- `reports.py`
- `reconstruction.py`
- `officers.py`
- `ops_modules.py`
- `legal.py`
- `orders.py`
- `reference.py`
- `announcements.py`

### UI and static assets

- `app/templates`
  - server-rendered page templates
- `app/templates/partials/nav.html`
  - shared authenticated navigation shell
- `app/static/css/app.css`
  - shared styling system
- `app/static/js/app.js`
  - shared UI behavior
- `app/static/cleo`
  - legacy/mock-report static app
- `app/static/cleo/cleo_report.js`
  - mock-report browser state and save/load behavior

### Data and document assets

- `data/uploads/forms`
  - live form source files
- `app/data/forms_pdf_templates`
  - PDF template metadata
- `app/data/handbook`
  - handbook PDF and structured handbook data
- `app/data/legal`
  - legal corpus and tuning/logging artifacts
- `app/data/orders`
  - order source config and seed metadata
- `app/data/uploads/orders`
  - seeded order documents
- `data/uploads/reconstruction`
  - reconstruction exports

## Routing System

The app uses Flask blueprints and domain route files. `app/__init__.py` registers the full route set in the factory.

### Blueprint organization

- `auth`
  - landing, login, CAC, registration, logout, role switching, user management
- `dashboard`
  - main dashboard and legacy CLEO entry points
- `forms`
  - library, maintenance, upload, PDF debug/template tools, fill workflow, saved forms, preview/download/email, render diagnostics
- `training`
  - training roster workflows and signatures
- `stats`
  - stats home, uploads, officer stats
- `annual_ai`
  - annual training assistant
- `admin`
  - stats admin and legal admin/analytics
- `cleo_api`
  - legacy CLEO page persistence APIs and mock-report packet APIs
- `reports`
  - standard report list/detail/create/review workflow
- `reconstruction`
  - case list, case detail, attachments, measurements, packets, diagram JSON
- `officers`
  - officer directory/profile
- `ops_modules`
  - truck gate, armory, RFI, vehicle inspections, and related exports/imports
- `legal`
  - legal search, source partitions, reference view, exports, import, debug, analytics support
- `orders`
  - orders desk, ingestion, source management, document view/download/simplify
- `reference`
  - officer handbook, paperwork navigator, handbook admin, print/download/email
- `announcements`
  - notice board

### Routing observations

- The app is functionally broad and already covers a large internal-portal surface.
- Several route files are carrying too much responsibility:
  - `forms.py` extends past line `2300`
  - `ops_modules.py` extends past line `3500`
  - `legal.py` extends past line `1100`
  - `orders.py` extends past line `1800`
- `create_app()` currently performs schema mutation work directly at startup, which couples runtime boot with migration logic.

## Current UI Structure

### Shared shell

- `base.html` defines the shared page shell and loads:
  - `app.css`
  - `app.js`
- `partials/nav.html` is the primary authenticated navigation surface.

### Current authenticated navigation

Top-level navigation currently groups the site into:

- `Dashboard`
- `Navigator`
- `Forms`
- `Saved Work`
- `Reports`
- `Authority`
  - `Law Lookup`
  - `Orders Desk`
  - `Officer Handbook`
- `Operations`
  - `Inspections`
  - `Training`
  - `Notices`
  - `Stats`
  - `Profile`
  - `Assistant`
  - `Reconstruction`
- optional personnel/admin/scope controls for privileged roles

### Major workflow surfaces

- `dashboard.html`
  - main command/operations board
- `forms.html`
  - forms library
- `forms_fill.html`
  - primary officer paperwork flow
- `saved_forms.html`
  - saved work queue
- `reports_list.html`
  - standard reports plus mock reports in one center
- `incident_paperwork_guide.html`
  - handbook-backed incident workflow navigator
- `officer_handbook.html`
  - handbook PDF plus structured supplements
- `legal_lookup.html`
  - law lookup
- `orders_reference.html`
  - orders desk

### Mobile and tablet behavior

- The shared nav has a mobile toggle in `app/static/js/app.js`.
- The forms fill page is already designed with a mobile-oriented scan/autofill panel.
- The navigator/reports/forms pages are already aiming at card-based responsive layouts.
- The legacy CLEO/static pages are a separate UI system and are not structurally aligned with the modern portal shell.

## State Management

### Authentication and role state

- Flask-Login handles authenticated user state.
- Flask session carries role/scope overlays such as:
  - `acting_role`
  - `acting_watch_commander_id`
- `app.context_processor` injects effective-role and scope-aware UI state into templates.

### Persistent server-side state

Primary persisted state lives in SQLite via SQLAlchemy models:

- users and roles
- forms and saved forms
- reports and attachments
- mock reports and graded pages
- orders
- announcements
- training rosters/signatures
- stats uploads and officer stats
- officer profiles
- vehicle inspections
- truck gate and RFI data

### Forms subsystem state

- Form definitions live in the `form` table and are backed by files in `data/uploads/forms`.
- Saved/persistent form payloads live in `saved_form.field_data_json`.
- Temporary no-retention payloads live in session (`forms_temp_payloads`).
- Output generation routes all go through shared PDF rendering services.
- Form UI shape comes from:
  - hard-coded schemas
  - inferred PDF fields
  - template payload JSON in `app/data/forms_pdf_templates`

### Legacy CLEO / mock-report state

- Static CLEO pages save and load with `fetch`.
- The current report id is tracked in:
  - URL query string
  - `localStorage['cleo_report_id']`
- Form serialization is index-based in `app/static/cleo/cleo_report.js`.
- Saved mock-report page payloads persist through `/api/cleo-reports/...` routes.

### Search and filter state

- Law lookup, orders desk, forms search, and navigator flows are mostly query-string driven.
- There is no central client store for search state.

## What Exists

- A broad, already-working internal portal with real domain coverage.
- A real PDF-based forms workflow, not just document links.
- Handbook, paperwork navigator, reports center, law lookup, and orders desk already integrated into the main shell.
- A role-aware navigation and permission model.
- A working persistence model for both modern report flows and legacy/mock-report flows.
- Local corpora for legal and order search rather than open-web dependency.

## What Is Missing

- A single canonical information model for document families across:
  - handbook terminology
  - forms library titles
  - legacy CLEO assets
  - reports/mock reports
- A complete handbook-to-form mapping layer.
- Full-form completion guides for the library beyond the small current set.
- Populated example completed forms in handbook supplements.
- A unified front-end component system across modern portal pages and legacy CLEO pages.
- Stable field-key serialization for mock reports; the current index-based approach is fragile if page markup changes.
- Formal migrations; schema mutation is still being done from the app factory at runtime.

## What Needs Refactoring

### 1. Normalize the content model

- Define canonical names for:
  - forms
  - handbook concepts
  - report packet types
  - legacy CLEO page families
- Replace legacy naming drift such as `CLEOC`, `CLEO`, `Mock Reports`, and handbook-only labels that do not map cleanly to live records.

### 2. Split oversized route modules

- `forms.py`
- `ops_modules.py`
- `legal.py`
- `orders.py`

These files are carrying UI, business rules, helpers, and admin concerns together.

### 3. Separate runtime boot from migration logic

- Move schema patching out of `create_app()`.
- Replace startup `ALTER TABLE` behavior with a real migration path.

### 4. Formalize state boundaries

- Keep the modern portal server-rendered.
- Treat legacy CLEO/static pages as either:
  - a temporary compatibility layer
  - or a fully supported subsystem with stable contracts
- Replace index-based mock-report serialization with stable field ids.

### 5. Consolidate document metadata

- Forms currently derive meaning from a mix of:
  - database rows
  - filenames
  - heuristics
  - handbook aliases
  - template payloads
- This should be unified behind a canonical document metadata layer.

### 6. Tighten the information architecture

- The modern navigation is improved, but the underlying data model is still broader and messier than the UI suggests.
- Several pages already present a cleaner workflow than the underlying module boundaries actually support.

## Bottom Line

The app is already a substantial working portal, not a prototype. The main weaknesses are not lack of features; they are structural consistency problems:

- naming drift
- legacy/modern workflow overlap
- oversized modules
- mixed state patterns
- incomplete canonical mapping between handbook guidance and actual live forms

No code changes were made beyond creating this analysis file and the two companion audit documents.
