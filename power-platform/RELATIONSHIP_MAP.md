# MCPD Sentinel — Dataverse Relationship Map

## Identity and organization

- DepartmentProfile 1:N RoleAssignment
- DepartmentProfile 1:N EmergencyContact
- DepartmentProfile N:1 DepartmentProfile via Supervisor
- DepartmentProfile 1:N DashboardPreference
- DepartmentProfile 1:N ActionItem

## Reports

- ReportRecord 1:N ReportPerson
- ReportRecord 1:N ReportVehicle
- ReportRecord 1:N ReportProperty
- ReportRecord 1:N ReportOffense
- ReportRecord 1:N ReportCoAuthor
- ReportRecord 1:N ReportAttachment
- ReportRecord 1:N ReportFinding
- ReportRecord 1:N FormInstance
- ReportRecord 1:N BodycamMedia
- ReportRecord 1:0..1 CLEOReport
- ReportRecord 1:0..1 AccidentCase
- ReportRecord N:1 ReportRecord via ParentRevision

## Forms

- FormDefinition 1:N FormInstance
- FormInstance 1:N FormFieldValue
- CallTypeRule provides configuration consumed by ReportRecord/FormInstance/ScenarioPaperwork

## Reference sources

- SourceDocument 1:N SourcePassage
- SourceDocument 1:N SourceTag
- SourceDocument 1:N SourceFavorite
- SourceDocument N:1 SourceDocument via Supersedes
- ReportFinding N:1 SourceDocument / SourcePassage
- ReportOffense N:1 SourceDocument when a controlled source is linked

## Training / FTO

- TrainingEvent 1:N TrainingAttendance
- TrainingEvent 1:N TrainingRoster
- TrainingRoster 1:N TrainingSignature
- QualificationDefinition 1:N QualificationRecord
- DepartmentProfile 1:N QualificationRecord

- TrainingAssignment 1:N DOR
- TrainingAssignment 1:N TaskBookProgress
- TrainingAssignment 1:N RemedialTraining
- TrainingAssignment 1:N WeeklyEvaluation
- TrainingAssignment 1:N PhaseEvaluation
- TrainingAssignment 1:N ScenarioRun
- DOR 1:N DORRating
- DOR 1:N RemedialTraining
- DORRatingCategory is organization-level configuration referenced by CategoryNumber/CategoryKey

## Scenario engine

- ScenarioDefinition 1:N ScenarioRun
- ScenarioRun 1:N ScenarioAction
- ScenarioRun 1:N ScenarioEvidence
- ScenarioRun 1:N ScenarioNotification
- ScenarioRun 1:N ScenarioPaperwork
- ScenarioRun 1:N CompetencyObservation
- ScenarioPaperwork N:1 FormDefinition
- ScenarioPaperwork N:1 SavedWork

## Watch / command

- DepartmentProfile 1:N WatchRosterEntry
- DepartmentProfile 1:N OperationalVehicle via AssignedTo
- DepartmentProfile 1:N WatchDecisionLog via Supervisor
- DepartmentProfile 1:N TurnoverBrief via CreatedBy
- DepartmentProfile 1:N AssistantOpsTask via AssignedTo / AssignedBy

## Personnel / performance

- DepartmentProfile 1:N PerformanceSubmission
- PerformanceSubmission 1:N PerformanceRating
- PerformanceElement 1:N PerformanceRating

## Accident reconstruction

- AccidentCase 1:N AccidentObject
- AccidentCase 1:N AccidentMeasurement
- AccidentMeasurement N:1 AccidentObject via StartObject / EndObject

## Armory / RFI

- ArmoryAsset 1:N ArmoryTransaction
- DepartmentProfile 1:N ArmoryTransaction
- DepartmentProfile 1:0..1 RFIProfile
- RFIProfile 1:N RFITransaction
- RFIAsset 1:N RFITransaction
- RFIProfile 1:N RFIAppointmentLetter

## Truck gate

- TruckGateCompany 1:N TruckGateDriver
- TruckGateCompany 1:N TruckGateVehicle
- TruckGateCompany 1:N TruckGateEntry
- TruckGateDriver 1:N TruckGateEntry
- TruckGateVehicle 1:N TruckGateEntry

## Vehicle inspections

- VehicleInspection 1:N VehicleInspectionItem
- DepartmentProfile 1:N VehicleInspection via Inspector

## CLEO

- CLEOReport 1:N CLEOPerson
- CLEOReport 1:N CLEOProperty
- CLEOReport 1:N CLEOVehicle
- CLEOReport 1:N CLEOOffense
- CLEOReport 1:N CLEOFieldFeedback

## Statistics

- ActivityCategory 1:N ActivityEntry
- ActivityCategory 1:N ActivityTarget
- DepartmentProfile 1:N ActivityEntry
- DepartmentProfile 1:N ActivityTarget

## AI / learning / administration

- DepartmentProfile 1:N AIRequestLog
- DepartmentProfile 1:N LearningSubmission
- DepartmentProfile 1:N DataExchangeJob
- ReferenceMaterial is organization-owned and version controlled by application workflow
