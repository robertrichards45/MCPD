# Module coverage and table policies

`module-data-map.yaml` maps all registered modules to existing Dataverse tables
and approved document-store boundaries. `table-data-policies.yaml` assigns every
table an ownership model, design classification, security profile and retention
profile. These classifications describe application handling; they are not formal
government markings or a determination that any production dataset is authorized.

The executable source validator checks both contracts alongside the schema. A
passing table-level coverage check does not mean each feature in the original
inventory is implemented. Detailed fields, workflow transitions, required keys,
relationship constraints and tenant enforcement still need validation.

## Ownership and access

This pass changes 45 organization-owned declarations to user/team ownership so
the schema can support the required assignment, report, audience and operational
team scopes. Shared non-sensitive configuration remains organization-owned.
AuditEvent stays organization-owned with restricted service/auditor privileges.

Microsoft documents [ownership-dependent access levels](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/security-concepts)
and [owner/access-team sharing](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/use-access-teams-owner-teams-collaborate-share-information).
The source correction enables scoped implementation; it does not install roles,
teams, sharing rules, secured columns or server-side authorization.

Before provisioning or publishing:

- Resolve each DepartmentProfile to the tenant's system user. A profile lookup
  does not itself grant access or replace Dataverse ownerid.
- Establish owner teams and explicit read/write grants at record creation. Apply
  equivalent grants to child rows and revoke obsolete grants on reassignment.
  Do not assume a parent lookup automatically secures or shares its children.
- Deny direct trainee access to raw ScenarioDefinition. Deliver a sanitized
  dispatch/scene projection. Secure every evaluator-only column listed in the
  policies, including world state and hidden evidence conditions, before granting
  trainee read access to runtime rows. Trainee users must not own evaluator rows
  or inherit evaluator-team privileges. Test direct API reads, exports and BI.
- Limit FTO/supervisor write privileges and validate lifecycle actions server-side.
  User/team ownership alone does not stop a trainee from finalizing their own DOR.
- Publish a minimal personnel directory projection rather than sharing complete
  personnel/contact rows department-wide.
- Do not grant organization-wide record privileges merely to implement the
  Assistant Operations workspace. System configuration and operational access
  remain separate roles. Review the existing broad BI Administrator rule in Phase 2.

There is no known deployed tenant in this project. If an existing environment has
already created these tables, assess a migration before applying this model;
these edits are not an in-place tenant migration script.

## Retention and raw-content controls

Each table references a named records family. Deployment must bind that family
to a government-approved schedule, event trigger, retention interval and hold
authority. No arbitrary day count is invented here. Automatic deletion remains
disabled until that configuration and enforcement are approved and tested.
Legal holds block disposition of both metadata and associated files. A closed,
expired or hidden record is not authorization to purge it.

The no-purge default is not permission to capture prohibited content. Scenario
transcript capture defaults off. FormDefinition save/retention controls apply to
both FormInstance payloads and FormFieldValue rows. AIRequestLog stores request
metadata/hashes, never credentials or raw prompts/outputs. Bodycam transcript
capture requires its own authorization; media approval is not AI approval.

Disposition, hold storage and enforcement are deployment work; these YAML
profiles are not a running purge or records-management service.

## Documents, media and environment configuration

All current URL columns have explicit storage mappings. SharePoint mappings use
the existing document site/library environment settings. Dataverse file storage
remains a supported alternative for approved deployments; an implementation
selecting it must define file columns, ACL and retention behavior and update the
mapping rather than placing bytes in URL fields.

`mcpd_EvidenceMediaStoreId` is an empty-by-default non-secret identifier for the
approved evidence/media store. It is not a URL containing a key and does not
enable the module or select an API/connector. Evidence/cyber approval and adapter
implementation are still required. Authenticated storage access must match record
access; a stored URL, exported link or module visibility is never a permission.

GenAI endpoint/model configuration and disabled-by-default behavior remain
unchanged. Credentials belong only in the approved connection/secret mechanism.

## Remaining model decisions

- Report/CLEO structured entities overlap; define canonical records and revision
  linkage without deleting CLEO-specific feedback or grading.
- ReferenceMaterial and SourceDocument need explicit version/grounding linkage.
- The relationship map claims 1:0..1 links not yet enforced by keys/constraints.
- Validate seed values and workflow transitions against the normalized choices.
- The current BI model has malformed quoting in several DAX expression strings;
  repair it and verify cross-file table references before analytics generation.

Phase 1 remains active. All original modules and the locked UI design remain in scope.
