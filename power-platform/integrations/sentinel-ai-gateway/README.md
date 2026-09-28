# Sentinel AI gateway

`SentinelAI` is the single logical provider alias. Modules submit `{task, input, context}` and receive a normalized `{task, text, humanReview}` result. `tasks.json` is the task registry; `gateway.mjs` is a tested, secret-free reference implementation of the shared dispatch boundary. It is **not loaded by the Canvas App**. The development solution currently has no custom connector or connection reference, so live AI calls remain pending.

The only provider invocation in the reference implementation is in `gateway.mjs`. An approved tenant adapter must translate the `ChatCompletion` request/response to the government connector's verified operation signature in **one place**. No module may embed provider URLs, credentials, model names, or operation-specific response parsing. One `mcpd_SentinelAI` connection reference, bound once to the approved government connection and surfaced in Power Apps as `SentinelAI`, serves all modules. An approved alternative provider requires changing the adapter/binding, not the module task contract.

| Task | Module / status in exported development app |
| --- | --- |
| `GeneralChat` | Ask Sentinel: local synthetic response behind `btnAIGateway`; no provider call. |
| `NarrativeCreate`, `NarrativeImprove` | Narrative Assistant: local concatenation behind `btnNarrAIGateway`; not connected. |
| `NarrativeEvaluate` | No provider-backed evaluator found. |
| `ReportInspect` | Report Inspector UI exists; no provider call. |
| `ScenarioGenerate` | Scenario Creator / Lab provider workflow not present. |
| `TrainingAssist` | Training UI exists; no provider-backed assistant found. |
| `LawExplain` | Knowledge Search / Law Lookup provider workflow not present. |

This inventory is based on the existing solution export (`MCPDSentinelDevelopment` 1.0.0.0, September 27, 2026), which has five screens, one Canvas App, 35 tables, zero cloud flows, and no connection references. The exported app contains two independent placeholder gateway buttons. Do not mistake this contract for completion of the live refactor.

## Power Apps binding sequence

1. Obtain the approved custom connector's exact connector ID, `ChatCompletion` action name, input schema, output schema, and connection ownership policy. Keep secrets only in the approved connection or secret store.
2. Add the existing approved custom connector to the `MCPD Sentinel Development` solution as one connection reference named `mcpd_SentinelAI`; give the app's data source the alias `SentinelAI`. Confirm the import dialog permits binding that reference to the existing government MCPD Sentinel GenAI connection once.
3. Implement one shared Canvas gateway component or approved server-side gateway. The component's action/`OnReset` receives a request record, validates `Task`, applies source and human-review requirements, calls `SentinelAI.ChatCompletion` once, normalizes the response, and returns error/result state. Microsoft's documented component `OnReset` can be invoked with `Reset(ComponentInstance)`; choose the final mechanism in Studio after testing its version and connector operation schema.
4. Replace Ask Sentinel's `btnAIGateway` and Narrative Assistant's `btnNarrAIGateway` placeholder bodies with calls through the shared gateway instance. Future modules use the same task contract and connection reference. Keep the existing deterministic fallback when AI is unavailable.
5. Test each task with synthetic data; verify direct source/citation handling for legal and report-inspection tasks, no fabricated facts or final judgments, one provider call per submitted task, and no prompts/outputs or secrets written to ordinary configuration records.
6. Re-export the solution and inspect the exported source. A repository/solution-wide search for provider calls must find only the shared gateway implementation. Then validate import and one-time binding in an approved environment.

For `LawExplain`, an authoritative retrieved source must be present before the model is called. For `ReportInspect`, approved-source context is required. The gateway's `humanReview` marker is an instruction to the consuming UI; Dataverse permissions and human approval remain separate controls. General chat may answer general questions without inventing a departmental source. The reference gateway rejects unsupported tasks and unusable responses before they reach a module.

Run `node --test integrations/sentinel-ai-gateway/gateway.test.mjs` from `power-platform/`. This verifies the shared request path with a synthetic provider, not a live government or development connector.
