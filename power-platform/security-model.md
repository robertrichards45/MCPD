# MCPD Sentinel Security Model

The app is shared department-wide, but users do not receive department-wide access simply because they can open the app.

## Identity

Use Microsoft Entra ID for authentication. Do not reproduce the legacy username/password model in the government build.

Each signed-in user is mapped to a DepartmentProfile record.

## Application roles

### Patrol Officer
- Own profile
- Own saved work
- Own reports
- Own qualifications/training
- FTO records where they are the trainee
- Common reference tools

### Field Training Officer
Everything a Patrol Officer can access, plus:
- Assigned trainees
- DOR creation/edit for assigned trainees
- Task-book progress for assigned trainees
- Weekly/phase evaluations for assigned trainees
- Remedial training assigned to their trainees
- FTO evaluator views

### Desk Sergeant
- Team-level operational review as configured
- Supervisor review queues
- Training/FTO visibility where assigned
- No unrestricted system configuration by default

### Watch Commander
- Shift/team records
- Supervisor approvals
- Assigned subordinate profiles
- FTO progress for supervised personnel
- Team analytics

### FTO Coordinator
- All FTO assignments
- FTO task books
- DOR/evaluation/remedial records
- FTO program analytics
- FTO configuration
- Program completion records

### Training Manager
- Department training assignments
- Training completion/readiness
- Qualification records
- Training analytics

### Forms Manager
- Form definitions
- Form metadata
- Call Type Paperwork Manager
- Does not automatically receive access to officer case content

### Report Reviewer
- Submitted reports routed for review
- Review comments and disposition
- Does not automatically receive site administration

### Website/System Controller
- Application configuration
- User/role administration
- Feature configuration
- Department-wide operational access only where explicitly required

## Security implementation

Use a combination of:
- Dataverse security roles
- owner/team ownership
- manager/team relationships
- explicit FTO/Trainee assignment relationships
- app-side visibility filtering for usability
- Dataverse privileges as the actual security boundary

Do not rely on Power Apps filtering alone to protect records.

## Department-wide sharing

One MCPD Sentinel app is shared with the department. The signed-in user's Entra identity determines their profile, role assignments, and authorized records.

## Development-tenant restriction

Use fake names and synthetic records in the personal development tenant. No production records are to be migrated from the personal tenant into the government tenant.
