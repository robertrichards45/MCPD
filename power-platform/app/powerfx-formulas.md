# MCPD Sentinel — Core Power Fx Formula Plan

These formulas are implementation-ready patterns for the Canvas App. Logical names may require adjustment after Dataverse creates publisher-prefixed schema names.

## App.OnStart

```powerfx
Set(gblUserEmail, Lower(User().Email));
Set(gblUserName, User().FullName);

Set(
    gblProfile,
    LookUp(
        DepartmentProfiles,
        Lower(Email) = gblUserEmail && Active = true
    )
);

ClearCollect(
    colMyRoles,
    Filter(
        RoleAssignments,
        Person.DepartmentProfile = gblProfile.DepartmentProfile &&
        Active = true &&
        (IsBlank(ExpirationDate) || ExpirationDate >= Today())
    )
);

Set(gblIsOfficer, CountIf(colMyRoles, RoleKey = 'RoleKey (RoleAssignments)'.Officer) > 0);
Set(gblIsFTO, CountIf(colMyRoles, RoleKey = 'RoleKey (RoleAssignments)'.FTO) > 0);
Set(gblIsSupervisor, CountIf(colMyRoles, RoleKey = 'RoleKey (RoleAssignments)'.Supervisor) > 0);
Set(gblIsAdmin, CountIf(colMyRoles, RoleKey = 'RoleKey (RoleAssignments)'.Administrator) > 0);

ClearCollect(
    colMyFTOAssignments,
    Filter(
        TrainingAssignments,
        Trainee.DepartmentProfile = gblProfile.DepartmentProfile ||
        PrimaryFTO.DepartmentProfile = gblProfile.DepartmentProfile ||
        Supervisor.DepartmentProfile = gblProfile.DepartmentProfile
    )
);
```

## Role-aware screen visibility

FTO navigation item:

```powerfx
gblIsFTO || gblIsSupervisor || gblIsAdmin || CountRows(colMyFTOAssignments) > 0
```

Personnel navigation item:

```powerfx
gblIsSupervisor || gblIsAdmin
```

Analytics navigation item:

```powerfx
gblIsSupervisor || gblIsAdmin
```

## My DORs

```powerfx
Filter(
    DORs,
    Trainee.DepartmentProfile = gblProfile.DepartmentProfile
)
```

## FTO assigned-trainee DOR queue

```powerfx
Filter(
    DORs,
    FTO.DepartmentProfile = gblProfile.DepartmentProfile &&
    Status <> 'DOR Status'.Approved
)
```

## Supervisor review queue

```powerfx
Filter(
    DORs,
    Supervisor.DepartmentProfile = gblProfile.DepartmentProfile &&
    Status = 'DOR Status'.SubmittedToSupervisor
)
```

## DOR rating validation

Before submission:

```powerfx
If(
    CountRows(Filter(colDORRatings, Observed = true && IsBlank(Rating))) > 0,
    Notify("Every observed category must have a rating.", NotificationType.Error),
    If(
        CountRows(Filter(colDORRatings, Rating < 1 || Rating > 7)) > 0,
        Notify("DOR ratings must be between 1 and 7.", NotificationType.Error),
        Set(gblDORReadyToSubmit, true)
    )
)
```

## Automatically identify possible remedial categories

```powerfx
ClearCollect(
    colRemedialCandidates,
    Filter(
        colDORRatings,
        Observed = true && Rating <= 3
    )
)
```

This only identifies candidates. The FTO makes the training decision.

## Trainee acknowledgment

```powerfx
Patch(
    DORs,
    gblSelectedDOR,
    {
        TraineeComments: txtTraineeComments.Text,
        TraineeAcknowledgedAt: Now(),
        Status: 'DOR Status'.TraineeAcknowledged
    }
);
Notify("DOR acknowledged.", NotificationType.Success)
```

## Original Sentinel three-layer finding display

Each report-inspector finding must display three separate fields:

```text
Automated cue: Finding.AutomatedCue
Approved source: Finding.SourceCitation
Human decision: Finding.HumanDisposition
```

Never concatenate these into a single authoritative conclusion.

## Feature flag

```powerfx
LookUp(
    AppConfigurations,
    ConfigKey = "EnableScenarioLab",
    Lower(ConfigValue)
) = "true"
```

## Current user fallback

If the signed-in user has no DepartmentProfile:

```powerfx
If(
    IsBlank(gblProfile),
    Navigate(scrAccessPending),
    Navigate(scrHome)
)
```

The app should not silently create a production profile unless that behavior is explicitly approved for the government tenant.
