# Source model validation

From the repository root, run:

```powershell
python -m pip install -r power-platform/tests/requirements.txt
python power-platform/tests/validate_schema.py
python -m unittest discover -s power-platform/tests -p "test_*.py"
```

The validator rejects duplicate YAML keys, unresolved/inline choices, missing lookup
targets, invalid ownership values, duplicate choice values, and changes to the core
FTO program/phase/acknowledgment vocabulary. It also checks exact module/table-policy
coverage, URL storage mappings, environment references, ownership consistency,
evaluator-only fields and retention safeguards. These are source checks, not proof of
Dataverse deployment, authorization, records retention, or end-to-end workflow behavior.

## Choice contract

`choice:Name` and `multichoice:Name` reference `dataverse-choices.yaml`. Existing
inline option order and spelling are preserved. Domain-specific statuses stay
separate even when two workflows currently use the same labels. Do not replace
them with the broad `RecordStatus` union, which would admit invalid transitions.

The source model expresses symbolic values. Numeric Dataverse option values must
be allocated and preserved in solution-generation assets before tenant creation;
these YAML files are not directly importable Dataverse metadata.

Previously unresolved fields now use these decisions:

| Field | Decision |
|---|---|
| RoleAssignment.RoleKey | Existing RoleKey registry; role aliases in app specs remain Phase 2 work |
| SavedWork.WorkType | ReportDraft, ReportCorrection, FormDraft, ScenarioPaperwork, Other |
| SavedWork.Status | Draft, Open, InProgress, Submitted, Completed, Cancelled, Archived; Open preserves the existing report-correction flow |
| SavedWork.AccessScope / Notice.Scope | Existing Personal, Team, Department vocabulary; this is metadata, not an authorization grant |
| FormDefinition.RetentionMode | Same vocabulary as FormInstance; retention enforcement remains separate |
| FTO phase fields | Existing I, II, III, IV registry, matching task-book seed data |
| TaskBookItem.RequiredProgramTypes | Multiselect of the existing FTO program registry |
| TrainingEvent.Status | Draft, Scheduled, InProgress, Completed, Cancelled |
| DOR.Shift | Text label for locally configured shifts; no invented fixed watch names |
| ReportRecord.ReportType | Text classification; no fixed report taxonomy is supplied in the baseline |

Primary names are implicit text columns declared by `primary_name`; the validator
does not require repeating them in `columns`. All existing tables and lookup
relationships are preserved by this normalization pass.

## Remaining Phase 1 checks

- Resolve overlapping Report/CLEO and reference/versioning concepts.
- Implement and tenant-test the declared row/column security and retention rules.
- Validate seed values, workflow transitions and all cross-file references.
- Resolve cardinality constraints and required/unique fields before provisioning.
- Preserve the disabled-by-default GenAI settings and secret-free source model.

Do not mark Phase 1 complete based only on passing this validator.
