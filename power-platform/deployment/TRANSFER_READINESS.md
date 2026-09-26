# MCPD Sentinel transfer readiness

This package is ready for government-tenant provisioning when the receiving team supplies tenant-owned connections, security groups, approved source documents, retention settings, and an approved GenAI/STARK endpoint. No government credentials or production records belong in this repository.

## Handoff sequence

1. Checkout `power-platform-rebuild` and record the commit supplied with the handoff.
2. Run the validation commands in `tests/README.md` and attach the results to the change record.
3. Provision an approved Power Platform environment with Dataverse, Power Apps, Power Automate, and (if enabled) Power BI.
4. Create/import the managed `MCPDSentinel` solution using the government release process.
5. Populate environment variables from `deployment/environment-values.template.json`; keep the filled file in the approved secret/configuration store, never in Git.
6. Reconnect SharePoint, Office 365 Users, Outlook, and any approved GenAI/STARK connector using government-owned connection references.
7. Create the Dataverse teams/security roles from `security-model.md` and assign approved Entra groups.
8. Import only approved government reference content and synthetic smoke-test records.
9. Run the validation section of `GOVERNMENT_IMPORT_CHECKLIST.md`, including row-level security and audit checks.
10. Obtain authority to operate, records-management, privacy, and operational owner sign-off before publishing.

## GenAI/STARK handoff

The application must call the approved service through `mcpd_GenAIBaseUrl`, `mcpd_GenAIModel`, timeout, and output-token settings. Keep `mcpd_GenAIEnabled=false` until the receiving team has approved the endpoint, identity, data boundary, prompt/response logging policy, and human-review controls. AI outputs remain draft cues; authorized personnel retain final decisions.

## Release evidence

Attach the solution version, source commit, solution-checker report, test results, connection-reference map, environment-variable values location, security-role assignment record, backup/export record, and signed go-live checklist.
