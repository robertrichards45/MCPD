# MCPD Sentinel — Government Import Checklist

## Before export from development

- Use synthetic data only.
- Confirm no personal-tenant user IDs are embedded in formulas or flows.
- Confirm all tenant-specific values use environment variables.
- Confirm SharePoint document locations use connection references/environment variables.
- Confirm no personal email addresses remain in notification actions.
- Run solution checker.
- Export an unmanaged development backup.
- Export a managed production solution.
- Record solution version and source commit.

## Government tenant import

1. Create or select the approved government Power Platform environment.
2. Confirm Dataverse is available.
3. Confirm required connectors are permitted.
4. Import the managed MCPD Sentinel solution.
5. Supply government values for all environment variables.
6. Rebind connection references to government connections.
7. Configure SharePoint document libraries if enabled.
8. Create/assign Dataverse teams and security roles.
9. Share the Canvas App with the approved department group.
10. Configure Power BI workspace/report access if Power BI is enabled.
11. Import only approved government configuration/reference content.
12. Do not migrate synthetic development data unless explicitly needed for testing.

## Validation

- Officer can see only own/private authorized work.
- FTO can see assigned trainees but not unrelated trainee records.
- Supervisor can see assigned team/scope.
- Administrator can configure the system.
- DOR submission -> acknowledgment -> supervisor review works.
- Remedial training routing works.
- Report return/resubmission lineage works.
- Scenario review separates trainee and evaluator views.
- Power BI row-level security behaves correctly.
- SharePoint document links resolve inside government tenant.
- Audit events are generated for required workflow transitions.

## Go-live

- Remove synthetic test accounts/records.
- Confirm production security groups.
- Confirm records-retention and privacy settings.
- Confirm command-approved source documents.
- Confirm backup/export procedure.
- Publish production app version.
