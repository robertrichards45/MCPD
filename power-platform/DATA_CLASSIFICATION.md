# MCPD Sentinel — Data Classification / Storage Guidance

This is a design classification for development and migration planning. Final government records, privacy, CUI/CJI, evidence, and retention decisions require command/cybersecurity/records approval.

| Data family | Primary storage target | Ownership model | Development rule | Notes |
|---|---|---|---|---|
| User profile / roles | Dataverse | Organization + role scopes | Synthetic only | Entra identity is authoritative for authentication |
| Reports / structured incident data | Dataverse | User/team | Synthetic only | Sensitive operational content; government policy controls production |
| Report files/photos | SharePoint or approved Dataverse file storage | Report/team scoped | Synthetic only | Malware scanning/retention requirements must be approved |
| Saved forms / form metadata | Dataverse | User/team | Synthetic only | Output PDFs may be stored in approved SharePoint library |
| Policy/orders/manual metadata | Dataverse | Organization | Public/synthetic approved test content | Full documents may live in SharePoint |
| FTO/DOR/task book | Dataverse | Assignment/team scoped | Synthetic only | Personnel/training records |
| Scenario definitions | Dataverse | Organization | Synthetic training content | No real case facts |
| Scenario transcripts/actions | Dataverse with retention controls | Assignment scoped | Synthetic only | Retention defaults minimized |
| Training/qualifications | Dataverse | User/team | Synthetic only | Supporting docs may live in SharePoint |
| BOLO | Dataverse + approved image storage | Organization/team | Synthetic only | Production may contain sensitive law-enforcement data |
| Watch Commander operational data | Dataverse | Team/organization | Synthetic only | Freshness/verification metadata required |
| Assistant Operations due-outs | Dataverse | Organization | Synthetic only | Command/administrative records |
| Armory/RFI | Dataverse | Restricted role | Synthetic only | Inventory/security controls |
| Truck Gate | Dataverse | Restricted role | Synthetic only | May contain visitor/company/vehicle PII |
| Vehicle Inspections | Dataverse + output docs | User/team | Synthetic only | Signature requirements tenant-specific |
| Bodycam/media | Approved evidence/media system or approved SharePoint only if authorized | Restricted | Do not use real evidence in dev | Production enablement gated by evidence/cyber approval |
| AI request metadata | Dataverse | Organization | No sensitive raw prompts in dev | Prefer hashes/source IDs/minimal metadata |
| Analytics | Power BI over Dataverse | RLS | Synthetic only | RLS must mirror operational scope |
| Audit events | Dataverse / platform audit | Organization restricted | Synthetic | Immutability/retention policy to be confirmed |
| Imports/exports | Dataverse job metadata + approved file staging | Administrator | Synthetic only | Record who requested, what format, when, and result |
