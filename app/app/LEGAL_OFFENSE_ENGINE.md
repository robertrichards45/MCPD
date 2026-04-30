# MCPD Legal Offense Engine

## What this engine now does
- Supports multi-source offense lookup across:
  - `GEORGIA`
  - `UCMJ`
  - `BASE_ORDER`
  - `FEDERAL_USC`
- Uses hybrid matching:
  - normalization + typo correction
  - synonym/alias/phrase expansion
  - intent phrase routing
  - narrative overlap scoring
  - element/category/token scoring
  - clause-by-clause multi-event query merging
- Returns ranked results with:
  - confidence score
  - certainty bucket (`strong`, `probable`, `possible`)
  - matched terms
  - why-this-matched reasons
  - safety warnings when confidence/data quality is low

## Structured record fields supported
In addition to existing fields (`code`, `title`, `summary`, `elements`, punishments), entries can now carry:
- offense metadata (`offense_id`, `source_type`, `category`, `subcategory`, `severity`)
- search enrichment (`aliases`, `synonyms`, `narrative_triggers`, `conduct_verbs`, `examples`)
- context fields (`victim_context`, `property_context`, `injury_context`, `location_context`, `military_context`)
- legal relationships (`lesser_included_offenses`, `alternative_offenses`, `jurisdiction_conditions`)
- provenance/versioning (`source_version`, `source_reference`, `last_updated`, `enrichment_derived`)

## Automated ingestion pipeline
Service: `app/services/legal_ingestion.py`

Capabilities:
- Bulk ingest uploads for:
  - `.json`, `.csv`, `.xlsx`, `.xlsm`
  - `.txt`, `.md`
  - `.pdf` (if `pypdf` is installed)
  - `.docx` (if `python-docx` is installed)
- Auto-normalizes records into structured offense entries.
- Auto-detects source by citation (`OCGA`, `Article`, `MCLBAO`) when scope is `ALL`.
- Optional AI enrichment for aliases/synonyms/examples/category hints.

AI safety rules in pipeline:
- AI enrichment is supplemental only.
- No AI-generated citation or punishment is treated as authoritative source text.

## Admin workflows
Page: `Admin -> Legal Corpus`

Available actions:
- Import corpus file (direct structured import)
- Automated source ingestion (bulk parse and normalize)
- Reindex corpus
- Run legal QA regression suite

## Corpus files
- `app/data/legal/georgia_codes.json`
- `app/data/legal/ucmj_articles.json`
- `app/data/legal/base_orders.json`
- `app/data/legal/federal_usc_codes.json`

## Regression testing
Script: `app/scripts/legal_regression_check.py`

Run:
```powershell
python scripts\legal_regression_check.py
```

The suite includes narrative, typo, slang, domestic, threat/theft/drug/traffic/UCMJ/base-order style cases and is intended for continuous relevance validation.
