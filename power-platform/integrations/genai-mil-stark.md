# GenAI.mil / STARK Integration Plan

## Why this exists

The MCPD Sentinel government deployment should use the Department of the Navy / DoD-approved GenAI.mil capability when API access is available and authorized.

The owner identified the GenAI.mil STARK API-key page:

`https://genai.mil/stark/user-ui/keys`

Do not store or commit any actual API key in GitHub, Power Fx, Dataverse records, source files, or screenshots.

## Current public-source context

Official DON guidance designates GenAI.mil as the enterprise generative-AI platform for DON users and states that it is authorized up to IL5/CUI, subject to platform policy. Public DON guidance in January 2026 described API access as an expected capability during FY26. The authenticated STARK key page indicates that API-key functionality is now available to at least some authorized users.

## Intended Sentinel architecture

Preferred path:

Power Apps
  -> Power Automate or approved custom connector/API layer
  -> GenAI.mil STARK endpoint
  -> Model response
  -> Sentinel UI

Do not call the GenAI.mil endpoint directly from a Canvas App if that would expose the key or bypass approved connection controls.

## Configuration

Environment variables:

- `mcpd_GenAIEnabled`
- `mcpd_GenAIBaseUrl`
- `mcpd_GenAIModel`
- `mcpd_GenAITimeoutSeconds`
- `mcpd_GenAIMaxOutputTokens`

Secrets:

- API key must be held in an approved secret/connection mechanism.
- Never place the API key in an environment variable that is readable by ordinary app users.
- Prefer an approved custom connector secret, Azure Key Vault/approved secret store, managed connection, or government-approved intermediary service.

## Required information from the authenticated GenAI.mil/STARK page or docs

Before implementation, capture **without exposing the secret**:

1. API base URL / endpoint.
2. Authentication header format.
3. Available model/deployment names.
4. Request schema.
5. Response schema.
6. Streaming support, if any.
7. File/RAG API support, if any.
8. Rate limits / quotas.
9. Allowed data categories and restrictions.
10. Network-access requirements (NIPR-only, tenant allowlisting, etc.).

## Sentinel AI use cases

Allowed design targets, subject to command/cyber policy:

- Report narrative drafting assistance
- Report Inspector explanation/summarization
- Approved-source grounded policy/reference assistance
- Law Lookup query expansion
- Order/PDI plain-language summaries
- Smart form suggestions
- FTO coaching in coaching/remedial mode
- Training assistant
- Counseling and awards draft assistance
- General authenticated Sentinel assistant

## Human-judgment boundary

AI may draft, summarize, retrieve, explain, or coach.

AI must not independently make the final determination for:
- probable cause
- guilt
- enforcement action
- final policy compliance
- final FTO rating
- discipline
- final report approval
- command decision

## Data handling

Do not assume that every kind of production data is permitted merely because the platform is IL5/CUI-capable.

The government deployment must still follow GenAI.mil usage rules, DON/USMC policy, privacy rules, records rules, evidence rules, and local cybersecurity approval.

In particular, PHI/PII restrictions and any API-specific limitations must be checked against current official guidance before sending production records.

## Fallback behavior

Sentinel must remain usable if GenAI is disabled or temporarily unavailable.

Deterministic/core features must continue to work:
- reporting forms
- workflow routing
- FTO/DOR records
- task book
- Watch Commander records
- policy/source search where non-AI search is available
- forms
- training
- operations modules

When AI is unavailable, show a clear message rather than silently failing.
