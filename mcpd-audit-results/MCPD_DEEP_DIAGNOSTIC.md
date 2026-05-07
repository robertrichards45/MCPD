# MCPD Portal Deep Diagnostic

Date: 2026-05-05

## Executive Summary

The Flask application imports successfully and registers 359 routes. Focused stabilization tests for forms, Law Lookup, assistant fallback, and the route matrix pass.

The highest-impact issues found in this pass were:

- The AI assistant frontend was falling into browser speech before the OpenAI TTS path could run, which explains robotic voice behavior even when `OPENAI_API_KEY` is present.
- The voice speed selector only affected browser speech, not OpenAI TTS audio, so changing speed could appear to do nothing.
- Law Lookup correctly recognized controlled-substance conduct, but federal installation context could tie the drug result and sort above it for `"weed in vehicle at the gate"`.

## App Startup / Route Health

Checked with:

```powershell
app\.venv\Scripts\python.exe -c "from app import create_app; app=create_app(); print(len(app.url_map._rules))"
```

Result:

- App imports successfully.
- Registered route count: 359.
- Assistant API routes are present:
  - `POST /api/assistant/ask`
  - `POST /api/assistant/speak`
  - `GET /api/assistant/voices`
  - `GET /api/assistant/status`
- Forms routes are present, including fill, preview, print/download, saved forms, and temp no-retention flows.
- Law Lookup routes are present, including `/legal/search`, Georgia, Federal, UCMJ, Base Orders, reference view, and reference download.

## Forms Diagnostic

Findings:

- Form filling is PDF-backed and not just generic hardcoded fields.
- `forms_fill.html` renders `field_*` inputs from schema data.
- Existing logic removes UI fields whose mapped PDF fields are missing.
- Signature fields have dedicated display/input handling.
- Preview, Print, Download, Email, Save Draft, Save Completed, Blank Preview, Blank Download, Back to Forms, and Saved Forms actions are wired through the form workflow template and routes.
- No-retention forms store temporary payloads only for preview/download/email flows.
- Normal officer tests confirm debug/template tools are not exposed in officer view.

Tests proving forms behavior:

```powershell
app\.venv\Scripts\python.exe -m pytest app\tests\test_forms_workflow.py app\tests\test_forms_visibility.py -q
```

Included in focused suite result: pass.

Remaining form risks:

- I did not manually verify every individual PDF visually in a browser during this pass.
- Full end-to-end SMTP email delivery depends on production mail settings.
- Browser/device scanner behavior still depends on mobile camera/browser support.

## Law Lookup Diagnostic

Law Lookup is not only keyword matching. The engine builds a query analysis, concept tags, source hints, full-document relevance, scenario triggers, phrase aliases, and result overlays. It also has AI expansion configured through the legal route when narrative queries are enabled.

AI/legal config observed locally:

- `LEGAL_AI_EXPANSION_ENABLED=True`
- `OPENAI_API_KEY` visible to local app: yes
- Chat model: `gpt-4.1-mini`
- TTS model: `tts-1`

Plain-language spot checks after fix:

- `"pooping in the street"` returns `OCGA 16-11-39` and `OCGA 16-6-8`; no shoplifting/PX order surfaced.
- `"trespassing on a federal installation"` returns `18 USC 1382` first.
- `"subject came back on base after being barred"` returns `18 USC 1382` first.
- `"weed in vehicle at the gate"` now returns controlled-substance results first: `OCGA 16-13-75`, `Article 112a`, `OCGA 16-13-30`.
- `"husband pushed wife and took her phone"` returns battery/domestic violence paths first.
- `"Marine refused lawful order"` returns `Article 92` first.

Fix applied:

- Reduced federal installation-entry ranking when the scenario describes controlled-substance conduct without actual trespass, barment, reentry, refusal-to-leave, or unauthorized-entry facts.
- Added regression coverage for `"weed in vehicle at the gate"`.

Remaining Law Lookup risks:

- AI expansion depends on the production Railway service actually seeing `OPENAI_API_KEY`.
- Some broad query logs show historical examples where `18 USC 1382` appears as a secondary match due to base/context overlap. That is acceptable as related context, but should continue to be monitored so it does not become a top unrelated result.

## AI Assistant / Voice Diagnostic

Findings:

- Assistant routes are registered.
- The server reads `OPENAI_API_KEY`, `MCPD_OPENAI_API_KEY`, or `OPENAI_KEY`.
- `/api/assistant/speak` uses OpenAI TTS when available and returns MP3 audio.
- The frontend previously started browser speech before attempting `/api/assistant/speak`; this caused robotic speech and made the OpenAI TTS path effectively unreachable.
- Voice speed settings previously affected browser speech only, not OpenAI TTS.

Fix applied:

- Frontend now sends summarized speech text to `/api/assistant/speak`.
- Browser speech is now only fallback when server TTS fails.
- OpenAI TTS now accepts a speed parameter.
- Voice speed options now map to calmer values:
  - Normal: `0.92`
  - Fast: `1.05`
  - Very Fast: `1.18`
- Cache-busted assistant scripts in `base.html`.

Remaining AI/voice risks:

- A live OpenAI TTS call was not made in tests to avoid spending API calls.
- If production still sounds robotic, the production server is likely not reaching `/api/assistant/speak` successfully or Railway is missing/overriding the OpenAI key.
- Browser speech voices are device-dependent and can still sound robotic if OpenAI TTS fails.

## Static / Frontend Checks

Checked:

```powershell
node --check app\static\js\assistant.js
node --check app\static\js\voice_assistant.js
```

Result:

- No JavaScript syntax errors in assistant scripts.
- Static files load locally through Flask test client:
  - `/static/js/assistant.js`
  - `/static/js/voice_assistant.js`
  - `/static/css/app.css`

## Test Results

Focused stabilization suite:

```powershell
app\.venv\Scripts\python.exe -m pytest app\tests\test_forms_workflow.py app\tests\test_forms_visibility.py app\tests\test_legal_lookup_engine.py app\tests\test_assistant_fallback.py app\tests\test_stability_route_matrix.py -q
```

Result:

- `55 passed in 40.98s`

Compile check:

```powershell
app\.venv\Scripts\python.exe -m compileall app
```

Result:

- Completed without syntax errors.

Full suite:

```powershell
app\.venv\Scripts\python.exe -m pytest -q
```

Result:

- Timed out after 5 minutes in this environment.
- This is not recorded as a pass.

## Deployment Notes

- Production must use Railway Postgres for account persistence.
- `OPENAI_API_KEY` must be on the web service variables, not only on a database service.
- If voice falls back to robotic browser speech, check server response for `POST /api/assistant/speak` and confirm Railway can see `OPENAI_API_KEY`.
- Do not commit runtime legal query logs, local SQLite databases, or `.env` files.
