Forms PDF Workflow

- Officer workflow:
  - Open a form from `/forms`
  - Complete only PDF-backed fields on `/forms/<id>/fill`
  - Use preview, print, download, or email actions
  - Completed output is generated from `render_form_pdf(...)`

- Source of truth:
  - Real PDF is the source of truth when a form has a PDF file
  - Fillable PDFs use AcroForm field writes
  - Static PDFs fall back to overlay rendering
  - The same renderer path is used for preview, download, and email

- Field visibility:
  - Visible online fields come from template `ui_fields` or `field_map`
  - If no template exists and the PDF is fillable, the app infers user-fillable PDF fields
  - Non-user controls such as signature, print, submit, and reset are excluded

- Officer-facing restrictions:
  - Officers do not see template editor, PDF debug, or render diagnostics on normal form pages
  - If a form is not ready for online completion, the officer sees a clean fallback message with blank-form actions

- Maintenance workflow:
  - Restricted maintenance page: `/forms/maintenance`
  - Template editor, PDF debug, and render diagnostics remain separate from the officer flow
  - Maintenance access is limited to Website Controller, Watch Commander, and Desk Sgt

- No-retention behavior:
  - No-retention completed payloads use temporary session-backed storage
  - Temporary rendered PDFs are deleted after response delivery
  - Email flow reads the generated PDF into memory and deletes the temp file immediately
