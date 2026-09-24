# MCPD Sentinel Acceptance Tests

## Identity and role access

1. Officer can sign in and reaches Home/Action Center.
2. Officer cannot open Administrator configuration by direct navigation.
3. FTO can access only assigned trainees.
4. FTO cannot finalize an unrelated trainee DOR.
5. Supervisor can review records within configured scope.
6. Administrator can configure system/reference records.
7. App-side hiding is not the only boundary; Dataverse permissions block unauthorized record access.

## Report Inspector

1. Entering a narrative does not persist the raw narrative when retention is disabled.
2. Review history stores a narrative hash and finding metadata.
3. A Draft source is never shown as approved authority.
4. A Retired source is never silently used as current authority.
5. Findings display Automated Cue, Approved Source, and Human Judgment separately.
6. Returning a report creates an Action Center correction item.
7. Resubmission creates a new revision with lineage.
8. Sentinel cannot close a review merely because automated findings are zero.

## FTO program

1. Standard and accelerated assignments load the correct program type.
2. Task Book displays tasks by phase.
3. DOR displays all active standardized rating categories.
4. Observed rating must be 1–7.
5. Not Observed category can be submitted without a numeric rating.
6. Low rating can create/remind an FTO of remedial training but cannot auto-impose a final FTO decision.
7. FTO submits DOR to trainee.
8. Trainee acknowledgment records receipt and optional comment.
9. UI states acknowledgment is not agreement.
10. Acknowledgment routes DOR to supervisor.
11. Supervisor can approve or return.
12. Material DOR edit after acknowledgment resets prior acknowledgment/review.
13. Phase completion cannot bypass blocking remediation.
14. Program completion creates a completion record/audit event.

## Scenario engine

1. Trainee cannot see hidden evaluator state during Evaluation mode.
2. Natural-language action becomes a structured action.
3. Scenario world state—not the AI interpreter—controls what is true.
4. NPC does not reveal unknown/hidden facts.
5. Time progression can change witness/resource/evidence availability when scenario rules define it.
6. Evidence tracks discovery/preservation/collection independently.
7. CID/supervisor notification requirements can be tracked separately from whether they were completed.
8. End Call presents required paperwork from the authoritative rules matrix.
9. Scenario score creates at most a draft evaluation aid.
10. Human FTO finalizes ratings/remediation.
11. Transcript retention defaults off.

## Watch Commander

1. Watch roster uses dated roster records.
2. Posts/vehicles/events show last verified time.
3. Records older than configured threshold display STALE - VERIFY.
4. Saved decision log freezes its source context and integrity hash.
5. Finalized turnover brief is not normally editable.
6. Turnover brief includes freshness markers.
7. Decision support is visibly non-authoritative.

## Government portability

1. Personal tenant URL is absent from app formulas after import.
2. Personal email addresses are absent from flows.
3. Government connection references can be rebound without editing every flow.
4. Government environment variables can be changed without editing every screen.
5. Synthetic development data can be excluded from production.
6. Power BI row-level security is tested under Officer/FTO/Supervisor/Admin identities.
