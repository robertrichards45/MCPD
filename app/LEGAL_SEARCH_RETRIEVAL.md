# Legal Search Retrieval Rebuild

This rebuild replaces the prior single-pass, rule-heavy legal lookup scorer with a staged retrieval pipeline designed for broad officer-style scenario searches across the approved corpus.

## What Changed

1. Query normalization
- Lowercases, removes punctuation noise, expands shorthand, and corrects common misspellings.
- Builds token, phrase, clause, and context views of each query.

2. Query understanding
- Detects broad concepts such as federal installation, lawful order, domestic violence, false identity, threats, drug activity, and property crime.
- Infers likely source hints such as Georgia, UCMJ, Base Orders, and Federal USC.

3. Broad candidate retrieval
- Searches across code, title, summary, elements, keywords, aliases, synonyms, narrative triggers, examples, contexts, categories, and official text.
- Uses direct overlap plus fuzzy token matching so broad wording can still surface the right records.

4. Re-ranking
- Scores entries by citation match, phrase overlap, token overlap, concept overlap, context overlap, jurisdiction fit, offense-context fit, and scenario wording similarity.
- Applies source-quality weighting and penalties for weak one-word overlaps.
- Adds a full-document relevance pass before final ranking so each result is checked against the entry body: summary, required elements, official text, context, examples, categories, and notes. Keyword aliases still help find candidates, but keyword-only matches are penalized when the body of the law/order does not support the officer's scenario.
- Adds scenario-supported adjustment so plain facts such as barred reentry, domestic pushing/grabbing, lawful-order refusal, marijuana at the gate, after-hours building entry, text threats, PX shoplifting, and barracks fighting boost the legally supported references while suppressing weak keyword-only pollution.

5. Fallback retrieval
- Automatically runs a broader second pass when the first pass is weak.
- Reuses clause-level splits for multi-event narratives.
- Adds likely core reference paths for clearly implied scenarios such as DUI refusal, federal installation trespass, lawful-order refusal, domestic battery, identity-document offenses, and related traffic/drug paths.

6. Result quality logging
- Main query log now stores a `quality` field.
- Weak/no-result/repeated reformulation searches are also written to `app/data/legal/legal_search_failures.jsonl`.

7. Regression coverage
- `app/scripts/legal_regression_check.py` now includes broader real-world officer queries.
- `app/tests/test_legal_lookup_engine.py` adds broad-query assertions and negative checks for bad outranking / wrong-statute pollution.
- `app/tests/test_legal_lookup_stress_matrix.py` verifies 500+ code/title/summary/keyword searches through both the engine and the Flask route.

## Safety / Scope

- Search remains corpus-first and local to the approved datasets already loaded by the portal.
- No open-web retrieval was added.
- Ranking and scenario expansion are internal only; officers still see a clean grouped result UI.

## File-by-File Summary

- `app/services/legal_lookup.py`
  Rebuilt the retrieval path with staged query analysis, broad candidate retrieval, full-document relevance review, reranking, fallback search, and scenario overlays.

- `app/routes/legal.py`
  Added search quality classification and failure/reformulation logging.

- `app/scripts/legal_regression_check.py`
  Expanded the regression suite with broader officer-style scenario cases.

- `app/tests/test_legal_lookup_engine.py`
  Added automated tests for broad scenario handling, federal ranking, DUI charge-path coverage, and prescription-pill filtering.

- `app/tests/test_legal_lookup_stress_matrix.py`
  Confirms broad ranking changes do not break direct citation/title/summary/keyword searches.
