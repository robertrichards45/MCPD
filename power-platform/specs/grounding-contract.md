# MCPD Sentinel Grounding Contract

## Core rule

Sentinel must fail closed when it cannot ground a substantive policy/reference claim in a current approved source supplied to the reasoning step.

## Three separate layers

1. **Automated cue** — what application logic or a model noticed.
2. **Approved source** — a current approved passage supplied by Sentinel.
3. **Authorized human judgment** — whether the source applies and what action is appropriate.

These layers must remain visibly separate in the user interface and data model.

## Approved source lifecycle

- Draft
- Approved
- Retired

Only **Approved** documents may be used as authoritative grounding in normal officer-facing decision support.

Draft and retired material may be available to specifically authorized research/administrative views but must be clearly labeled and must not silently support an authoritative answer.

## Model boundary

A model may:
- summarize supplied approved passages;
- explain why a configured cue may relate to a supplied passage;
- interpret natural-language trainee actions into structured scenario actions;
- provide non-authoritative coaching when the mode permits it.

A model may not:
- invent policy text, law, facts, evidence, or scenario truth;
- determine guilt;
- determine probable cause;
- declare final legal sufficiency;
- issue final policy-compliance determinations;
- issue final FTO ratings;
- make discipline decisions;
- replace supervisor/FTO approval.

## Citation validation

Every substantive policy/reference claim from an AI step must identify one or more source IDs that were actually supplied to that step.

Reject/withhold an AI output when:
- it cites an unknown source ID;
- it cites a Draft or Retired source as approved authority;
- it makes a substantive policy claim with no source;
- the source version is no longer current when the workflow requires current authority.

## Data minimization

Do not send raw report narratives, real case data, sensitive personal data, or full trainee transcripts to an external model merely because a model is available.

The government deployment must follow the tenant's approved AI, privacy, records, and cybersecurity rules.
