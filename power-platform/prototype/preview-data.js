window.SENTINEL_DATA = {
  "modules": [
    {
      "key": "dashboard",
      "name": "Dashboard",
      "group": "Home",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "role-aware home dashboard",
        "customizable/role-specific widgets",
        "quick access",
        "recent reports",
        "saved work",
        "training visibility",
        "Watch Commander summary",
        "responsive desktop/mobile layout"
      ]
    },
    {
      "key": "incident_reporting",
      "name": "Start Report / Incident Reporting",
      "group": "Reports",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "create/edit incident reports",
        "dynamic structured fields",
        "attachments and photos",
        "device-camera capture where supported",
        "multiple involved persons",
        "multiple/co-author officers",
        "AI-assisted narrative drafting",
        "draft auto-save",
        "supervisor submission",
        "return-for-correction workflow",
        "grading/review/approval",
        "report status tracking"
      ]
    },
    {
      "key": "mobile_reporting",
      "name": "Mobile Incident Reporting",
      "group": "Reports",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "mobile drafts",
        "one-step-at-a-time guided flow",
        "incident details",
        "statute selection",
        "involved persons",
        "facts/narrative",
        "statement collection",
        "digital signature capture where approved",
        "domestic supplemental",
        "smart form suggestions",
        "narrative suggestions",
        "recommended paperwork/forms",
        "packet review/transmission",
        "supervisor review",
        "fast-capture mode",
        "critical-incident mode",
        "mobile statistics"
      ]
    },
    {
      "key": "report_inspector",
      "name": "Report Inspector",
      "group": "Reports",
      "baseline": "original_sentinel",
      "enabled_default": true,
      "capabilities": [
        "Automated completeness and consistency cues",
        "Approved source and version citations",
        "Human review and correction lifecycle"
      ]
    },
    {
      "key": "cleo",
      "name": "CLEO Structured Reporting",
      "group": "Reports",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "Incident Admin",
        "Persons",
        "Property",
        "Vehicle",
        "Offenses",
        "Narrative",
        "CCN generation",
        "Draft -> Submitted -> Returned -> Graded",
        "file upload",
        "field-level feedback",
        "grading",
        "return/resubmission",
        "report summary"
      ]
    },
    {
      "key": "accident_reconstruction",
      "name": "Accident Reconstruction",
      "group": "Reports",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "reconstruction cases",
        "interactive diagram",
        "vehicles/objects/measurements",
        "speed/damage details",
        "distance/angle tools",
        "timeline",
        "photos/evidence",
        "multi-vehicle support",
        "PDF packet export"
      ]
    },
    {
      "key": "forms",
      "name": "Forms Library",
      "group": "Forms",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "searchable forms library",
        "blank form download",
        "web-based form filling",
        "incident-data prefill",
        "saved progress",
        "PDF generation",
        "email/download/print where allowed",
        "statement compact view",
        "saved form management",
        "personal/team/department access scope",
        "official-source update tracking",
        "PDF field mapping/calibration tools",
        "render debugging/validation",
        "Call Type Paperwork Manager",
        "retention/PII controls",
        "Forms Manager"
      ]
    },
    {
      "key": "call_type_rules",
      "name": "Call Type Paperwork Manager",
      "group": "Forms",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "searchable forms library",
        "blank form download",
        "web-based form filling",
        "incident-data prefill",
        "saved progress",
        "PDF generation",
        "email/download/print where allowed",
        "statement compact view",
        "saved form management",
        "personal/team/department access scope",
        "official-source update tracking",
        "PDF field mapping/calibration tools",
        "render debugging/validation",
        "Call Type Paperwork Manager",
        "retention/PII controls",
        "Forms Manager"
      ]
    },
    {
      "key": "policy_search",
      "name": "Law Lookup / Policy Search",
      "group": "LawAndReference",
      "baseline": "both",
      "enabled_default": true,
      "capabilities": [
        "Georgia law",
        "UCMJ",
        "federal USC",
        "base orders/local references",
        "natural-language search",
        "AI query expansion where approved",
        "incident classification assistance",
        "full source text/reference",
        "export/import",
        "legal analytics",
        "query logs",
        "federal-source review/editing",
        "weak-query analysis",
        "preferred-state setting"
      ]
    },
    {
      "key": "orders",
      "name": "Orders & Memoranda",
      "group": "LawAndReference",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "browse/search",
        "source metadata",
        "download",
        "AI simplification",
        "bookmarks/favorites",
        "audience/topic tags",
        "source/version management",
        "source ingestion",
        "supersession tracking",
        "metadata extraction/confidence",
        "help/reference interface"
      ]
    },
    {
      "key": "handbook",
      "name": "Officer Handbook",
      "group": "LawAndReference",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "Officer Handbook",
        "PDF/email/print/download",
        "content/version management",
        "Incident Paperwork Guide",
        "call-type paperwork navigator",
        "guide administration"
      ]
    },
    {
      "key": "paperwork_guide",
      "name": "Incident Paperwork Guide",
      "group": "LawAndReference",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "Officer Handbook",
        "PDF/email/print/download",
        "content/version management",
        "Incident Paperwork Guide",
        "call-type paperwork navigator",
        "guide administration"
      ]
    },
    {
      "key": "training",
      "name": "Training Management",
      "group": "Training",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "roster upload",
        "roster distribution",
        "digital signatures",
        "completion tracking",
        "search",
        "qualification tracker",
        "readiness/compliance",
        "training record log",
        "documentation upload",
        "export",
        "roster print/download"
      ]
    },
    {
      "key": "qualifications",
      "name": "Qualification / Readiness Tracker",
      "group": "Training",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "roster upload",
        "roster distribution",
        "digital signatures",
        "completion tracking",
        "search",
        "qualification tracker",
        "readiness/compliance",
        "training record log",
        "documentation upload",
        "export",
        "roster print/download"
      ]
    },
    {
      "key": "fto",
      "name": "FTO Center",
      "group": "Training",
      "baseline": "original_sentinel",
      "enabled_default": true,
      "capabilities": [
        "Standard 8-week and accelerated 4-week programs",
        "31 DOR categories with 1–7 / N-O scale",
        "Digital task book",
        "Weekly and phase evaluations",
        "Remedial training and re-evaluation",
        "Trainee acknowledgment and supervisor review"
      ]
    },
    {
      "key": "scenario_lab",
      "name": "Scenario Lab",
      "group": "Training",
      "baseline": "original_sentinel",
      "enabled_default": true,
      "capabilities": [
        "Dispatch and response",
        "Investigation and persistent world state",
        "Notifications and evidence",
        "End-of-call paperwork",
        "FTO review and remediation",
        "Hidden evaluator state"
      ]
    },
    {
      "key": "bodycam",
      "name": "Bodycam Footage Management",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "deployment_gate": "evidence_and_cyber_approval",
      "capabilities": [
        "footage metadata",
        "playback/timeline",
        "download where authorized",
        "report attachment linkage",
        "narrative creator",
        "5-W Builder",
        "search/filter",
        "mobile access",
        "transcript support where approved"
      ]
    },
    {
      "key": "bolo",
      "name": "BOLO",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "person/vehicle/property BOLO",
        "photos",
        "detail/edit",
        "located status",
        "cancel/close",
        "search/filter"
      ]
    },
    {
      "key": "watch_commander",
      "name": "Watch Commander / Digital Lieutenant",
      "group": "Operations",
      "baseline": "both",
      "enabled_default": true,
      "capabilities": [
        "live/controlled shift overview",
        "shift creation/editing",
        "officer assignments",
        "active roster",
        "report review/approval queue",
        "incident packet status",
        "training/forms oversight",
        "activity blotter",
        "pending approvals",
        "shift briefings",
        "briefing acknowledgment",
        "notifications",
        "original Sentinel Digital Lieutenant decision support",
        "turnover brief",
        "decision log",
        "data freshness / STALE — VERIFY"
      ]
    },
    {
      "key": "assistant_operations",
      "name": "Assistant Operations",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "command due-out tracker",
        "training tasks",
        "inspections",
        "suspense items",
        "projects",
        "assignment to Lt/Sgt/Watch Commander",
        "status/comments/completion tracking",
        "department-level oversight"
      ]
    },
    {
      "key": "armory",
      "name": "Armory",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "asset inventory",
        "weapon/equipment assignment",
        "check-out/check-in",
        "identity/PIN/CAC controls where approved",
        "officer cards",
        "bulk import/export"
      ]
    },
    {
      "key": "rfi",
      "name": "RFI",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "firearm/ammunition tracking",
        "officer RFI profiles",
        "command-level defaults",
        "appointment letters",
        "transactions/export"
      ]
    },
    {
      "key": "truck_gate",
      "name": "Truck Gate",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "vehicle entry/exit",
        "daily log workbook",
        "companies/drivers/vehicles",
        "imports with validation",
        "QR labels/scanning"
      ]
    },
    {
      "key": "vehicle_inspections",
      "name": "Vehicle Inspections",
      "group": "Operations",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "digital inspection forms",
        "PDF overlay/calibration",
        "electronic signature",
        "correction/return workflow",
        "CSV/JSON/ZIP export",
        "batch print"
      ]
    },
    {
      "key": "personnel",
      "name": "Personnel",
      "group": "Personnel",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "searchable officer directory",
        "profile editing",
        "profile photos",
        "emergency contacts",
        "exports",
        "installation view",
        "role assignment",
        "supervisor assignment",
        "pending approval"
      ]
    },
    {
      "key": "performance",
      "name": "Performance Evaluation",
      "group": "Personnel",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "evaluation element definitions",
        "personal performance history",
        "performance statistics",
        "annual submission",
        "supervisor approve/reject",
        "team overview",
        "year-end/reset workflow"
      ]
    },
    {
      "key": "stats",
      "name": "Statistics & Activity",
      "group": "Analytics",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "officer activity upload",
        "officer dashboard",
        "configurable categories",
        "targets",
        "history/trends",
        "export"
      ]
    },
    {
      "key": "analytics",
      "name": "Department Analytics",
      "group": "Analytics",
      "baseline": "original_sentinel",
      "enabled_default": true,
      "capabilities": [
        "Training readiness",
        "Report quality",
        "FTO progress",
        "Operations and personnel",
        "Role-scoped analytics"
      ]
    },
    {
      "key": "announcements",
      "name": "Announcements",
      "group": "Home",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "create/publish",
        "pin",
        "visibility toggle",
        "archive"
      ]
    },
    {
      "key": "ai_assistant",
      "name": "AI Assistant & Tools",
      "group": "More",
      "baseline": "original_portal",
      "enabled_default": true,
      "deployment_gate": "approved_ai_configuration",
      "capabilities": [
        "text assistant",
        "voice input/output where approved",
        "counseling document drafting",
        "awards recommendation drafting",
        "annual training assistant",
        "legal query expansion",
        "narrative drafting",
        "order simplification",
        "smart form suggestions",
        "learning submission/approval",
        "officer file management",
        "original Sentinel grounding rules and human-review boundary"
      ]
    },
    {
      "key": "data_exchange",
      "name": "Data Export & Import",
      "group": "Administration",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "CSV exports/imports",
        "PDF exports/imports",
        "JSON exports/imports",
        "ZIP bundles",
        "Excel workbooks",
        "module-specific migration/archival tools"
      ]
    },
    {
      "key": "administration",
      "name": "Administration",
      "group": "Administration",
      "baseline": "both",
      "enabled_default": true,
      "capabilities": [
        "Entra/Microsoft identity in the Power Platform implementation",
        "Dataverse role/security model",
        "restricted administration",
        "Site Owner / Builder-equivalent controls",
        "legal corpus administration",
        "forms administration",
        "analytics administration",
        "audit/accountability",
        "tenant/environment configuration",
        "data-retention flags",
        "secure government deployment design"
      ]
    },
    {
      "key": "builder",
      "name": "Builder / System Controller",
      "group": "Administration",
      "baseline": "original_portal",
      "enabled_default": true,
      "capabilities": [
        "Entra/Microsoft identity in the Power Platform implementation",
        "Dataverse role/security model",
        "restricted administration",
        "Site Owner / Builder-equivalent controls",
        "legal corpus administration",
        "forms administration",
        "analytics administration",
        "audit/accountability",
        "tenant/environment configuration",
        "data-retention flags",
        "secure government deployment design"
      ]
    }
  ],
  "categories": [
    {
      "CategoryNumber": "1",
      "CategoryGroup": "Appearance",
      "CategoryName": "General Appearance",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "2",
      "CategoryGroup": "Attitude",
      "CategoryName": "Acceptance of Feedback",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "3",
      "CategoryGroup": "Attitude",
      "CategoryName": "Attitude Toward the Job",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "4",
      "CategoryGroup": "Knowledge",
      "CategoryName": "Department Policies and Procedures",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "5",
      "CategoryGroup": "Knowledge",
      "CategoryName": "Criminal Laws",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "6",
      "CategoryGroup": "Knowledge",
      "CategoryName": "Base/Department Regulations",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "7",
      "CategoryGroup": "Knowledge",
      "CategoryName": "Motor Vehicle Laws",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "8",
      "CategoryGroup": "Knowledge",
      "CategoryName": "Criminal Process",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "9",
      "CategoryGroup": "Performance",
      "CategoryName": "Driving Skills - Normal Conditions",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "10",
      "CategoryGroup": "Performance",
      "CategoryName": "Driving Skills - Moderate and High Stress Conditions",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "11",
      "CategoryGroup": "Performance",
      "CategoryName": "Response Time to Calls / Orientation",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "12",
      "CategoryGroup": "Performance",
      "CategoryName": "Routine Forms - Accuracy/Completeness",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "13",
      "CategoryGroup": "Performance",
      "CategoryName": "Report Writing - Organization/Detail",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "14",
      "CategoryGroup": "Performance",
      "CategoryName": "Report Writing - Grammar/Spelling/Neatness",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "15",
      "CategoryGroup": "Performance",
      "CategoryName": "Report Writing - Appropriate Time Used",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "16",
      "CategoryGroup": "Performance",
      "CategoryName": "Field Performance - Non-Stress Conditions",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "17",
      "CategoryGroup": "Performance",
      "CategoryName": "Field Performance - Stress Conditions",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "18",
      "CategoryGroup": "Performance",
      "CategoryName": "Investigative Skills",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "19",
      "CategoryGroup": "Performance",
      "CategoryName": "Interview/Interrogation Skills",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "20",
      "CategoryGroup": "Performance",
      "CategoryName": "Self-Initiated Field Activity",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "21",
      "CategoryGroup": "Performance",
      "CategoryName": "Officer Safety - General",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "22",
      "CategoryGroup": "Performance",
      "CategoryName": "Officer Safety - Suspects/Prisoners",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "23",
      "CategoryGroup": "Performance",
      "CategoryName": "Control of Conflict - Voice/Command",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "24",
      "CategoryGroup": "Performance",
      "CategoryName": "Control of Conflict - Physical Skill",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "25",
      "CategoryGroup": "Performance",
      "CategoryName": "Problem Solving/Decision Making",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "26",
      "CategoryGroup": "Performance",
      "CategoryName": "Radio - Appropriate Use of Codes/Procedures",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "27",
      "CategoryGroup": "Performance",
      "CategoryName": "Radio - Listens and Comprehends",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "28",
      "CategoryGroup": "Performance",
      "CategoryName": "Radio - Articulation of Transmissions",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "29",
      "CategoryGroup": "Relationships",
      "CategoryName": "With Citizens - General",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "30",
      "CategoryGroup": "Relationships",
      "CategoryName": "With Other Ethnic/Cultural/Social Groups",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    },
    {
      "CategoryNumber": "31",
      "CategoryGroup": "Relationships",
      "CategoryName": "With Other PMO/MCPD Members",
      "ScaleMin": "1",
      "ScaleAcceptable": "4",
      "ScaleMax": "7",
      "AllowNotObserved": "true"
    }
  ],
  "anchors": [
    {
      "CategoryNumber": "1",
      "Rating1_Unacceptable": "Appearance reflects poor uniform/equipment care, grooming, or compliance with appearance requirements.",
      "Rating4_Acceptable": "Neat and clean; uniform/equipment are properly worn, clean, serviceable, and within grooming requirements.",
      "Rating7_Superior": "Consistently exemplary appearance, equipment readiness, and command bearing.",
      "SourceAppendix": "A-3"
    },
    {
      "CategoryNumber": "2",
      "Rating1_Unacceptable": "Rationalizes errors, argues about feedback, rejects criticism, or treats feedback as personal.",
      "Rating4_Acceptable": "Accepts criticism positively and applies it to improve performance and prevent recurrence.",
      "Rating7_Superior": "Actively seeks feedback and uses it to improve performance without argument or blame.",
      "SourceAppendix": "A-3"
    },
    {
      "CategoryNumber": "3",
      "Rating1_Unacceptable": "Shows little dedication, treats the position as merely a job, or misuses authority/ego.",
      "Rating4_Acceptable": "Shows active interest in the police career and job responsibilities.",
      "Rating7_Superior": "Demonstrates exceptional professional interest, initiative, learning, responsibility, and concern for the law.",
      "SourceAppendix": "A-3"
    },
    {
      "CategoryNumber": "4",
      "Rating1_Unacceptable": "When tested, demonstrates very limited policy/procedure knowledge; in the field cannot apply common department rules.",
      "Rating4_Acceptable": "When tested, demonstrates acceptable knowledge and can apply commonly encountered department policies/procedures.",
      "Rating7_Superior": "Demonstrates excellent working knowledge and applies department policies/procedures, including less-common situations.",
      "SourceAppendix": "A-4"
    },
    {
      "CategoryNumber": "5",
      "Rating1_Unacceptable": "When tested, demonstrates very limited criminal-law knowledge; in the field does not recognize basic violations.",
      "Rating4_Acceptable": "When tested, demonstrates acceptable knowledge and recognizes/applies commonly encountered criminal law.",
      "Rating7_Superior": "Demonstrates outstanding criminal-law knowledge and applies it accurately to normal and unusual situations.",
      "SourceAppendix": "A-4"
    },
    {
      "CategoryNumber": "6",
      "Rating1_Unacceptable": "When tested, demonstrates very limited base/department-regulation knowledge and cannot recognize common violations.",
      "Rating4_Acceptable": "When tested, demonstrates acceptable knowledge and recognizes/applies commonly encountered regulations.",
      "Rating7_Superior": "Demonstrates outstanding regulation knowledge and applies it accurately to normal and unusual situations.",
      "SourceAppendix": "A-5"
    },
    {
      "CategoryNumber": "7",
      "Rating1_Unacceptable": "Does not know commonly used motor-vehicle-law sections or recognize violations.",
      "Rating4_Acceptable": "Knows commonly used sections, applies them appropriately, and can locate less-familiar law in reference material.",
      "Rating7_Superior": "Shows outstanding motor-vehicle-law knowledge, including less-common sections, and applies it effectively.",
      "SourceAppendix": "A-5"
    },
    {
      "CategoryNumber": "8",
      "Rating1_Unacceptable": "Violates procedural requirements, mishandles search/arrest procedure, or does not recognize legal procedural limits.",
      "Rating4_Acceptable": "Follows required procedures and conducts common searches/seizures within legal guidelines.",
      "Rating7_Superior": "Follows procedure accurately and demonstrates advanced, reliable knowledge of criminal process, searches, evidence, and rights.",
      "SourceAppendix": "A-5/A-6"
    },
    {
      "CategoryNumber": "9",
      "Rating1_Unacceptable": "Violates traffic rules, has preventable driving errors/accidents, poor control, or weak defensive-driving habits.",
      "Rating4_Acceptable": "Obeys traffic laws, maintains control, performs maneuvers competently, and drives defensively.",
      "Rating7_Superior": "Sets an exemplary driving standard with excellent control, anticipation, reaction, and defensive-driving skill.",
      "SourceAppendix": "A-6"
    },
    {
      "CategoryNumber": "10",
      "Rating1_Unacceptable": "Handles stressful/emergency driving poorly, uses warning equipment improperly, selects unsafe speed, or loses control.",
      "Rating4_Acceptable": "Maintains control, evaluates conditions properly, and obeys applicable traffic requirements under stress.",
      "Rating7_Superior": "Shows excellent stressful-driving judgment and control; anticipates conditions and uses emergency equipment/speed appropriately.",
      "SourceAppendix": "A-6"
    },
    {
      "CategoryNumber": "11",
      "Rating1_Unacceptable": "Becomes lost, lacks location awareness, cannot relate map/street information, or takes excessive time to arrive.",
      "Rating4_Acceptable": "Maintains location awareness, properly uses maps, and relates locations to destination.",
      "Rating7_Superior": "Remembers routes and relative locations, uses shortcuts appropriately, and navigates with exceptional orientation.",
      "SourceAppendix": "A-6"
    },
    {
      "CategoryNumber": "12",
      "Rating1_Unacceptable": "Does not know which routine form is required or completes forms inaccurately/incompletely.",
      "Rating4_Acceptable": "Selects common forms correctly and completes them accurately within reasonable time.",
      "Rating7_Superior": "Selects and completes even less-common/complex forms accurately and efficiently.",
      "SourceAppendix": "A-7"
    },
    {
      "CategoryNumber": "13",
      "Rating1_Unacceptable": "Report is disorganized, inaccurate, or omits pertinent details.",
      "Rating4_Acceptable": "Report is organized logically, accurate, and contains pertinent details.",
      "Rating7_Superior": "Report provides a complete, detailed, well-organized account from beginning to end.",
      "SourceAppendix": "A-7"
    },
    {
      "CategoryNumber": "14",
      "Rating1_Unacceptable": "Report contains poor spelling/grammar or is difficult to read.",
      "Rating4_Acceptable": "Report is legible with acceptable grammar/spelling and only rare minor errors.",
      "Rating7_Superior": "Report is very neat and legible with no meaningful spelling or grammatical errors.",
      "SourceAppendix": "A-7"
    },
    {
      "CategoryNumber": "15",
      "Rating1_Unacceptable": "Takes excessive time to complete reports compared with a competent officer.",
      "Rating4_Acceptable": "Completes reports in a reasonable amount of time for the task.",
      "Rating7_Superior": "Completes reports very efficiently at a skilled-veteran pace without sacrificing quality.",
      "SourceAppendix": "A-7"
    },
    {
      "CategoryNumber": "16",
      "Rating1_Unacceptable": "Becomes confused by routine non-stress tasks, fails to act, or takes inappropriate action.",
      "Rating4_Acceptable": "Properly assesses routine situations, selects appropriate action, and performs safely.",
      "Rating7_Superior": "Recognizes unusual/complex elements early and handles non-stress situations with excellent judgment and effectiveness.",
      "SourceAppendix": "A-8"
    },
    {
      "CategoryNumber": "17",
      "Rating1_Unacceptable": "Becomes emotional, panicked, ineffective, overreactive, or unable to function in stressful conditions.",
      "Rating4_Acceptable": "Remains calm and self-controlled in most stressful situations and selects appropriate action.",
      "Rating7_Superior": "Maintains exceptional composure under stress and can help restore control when others become ineffective.",
      "SourceAppendix": "A-8"
    },
    {
      "CategoryNumber": "18",
      "Rating1_Unacceptable": "Fails to conduct a basic investigation, overlooks readily available evidence, or does not pursue obvious investigative avenues.",
      "Rating4_Acceptable": "Uses proper investigative procedures, accurately identifies the nature of routine incidents, and properly collects/documents evidence.",
      "Rating7_Superior": "Conducts thorough investigations, recognizes less-obvious evidence connections, and demonstrates evidence-technician-level care.",
      "SourceAppendix": "A-8"
    },
    {
      "CategoryNumber": "19",
      "Rating1_Unacceptable": "Uses poor questioning, fails to establish rapport, misses important information, or loses control of the interview/interrogation.",
      "Rating4_Acceptable": "Uses generally proper questioning, establishes appropriate rapport, and obtains needed information in routine matters.",
      "Rating7_Superior": "Consistently uses effective questioning, rapport, and control even with difficult victims, witnesses, or suspects.",
      "SourceAppendix": "A-8"
    },
    {
      "CategoryNumber": "20",
      "Rating1_Unacceptable": "Avoids or fails to recognize police activity, does not follow up, or shows little initiative.",
      "Rating4_Acceptable": "Recognizes police-related activity, develops cases from observed activity, and demonstrates good initiative.",
      "Rating7_Superior": "Actively recognizes opportunities, initiates appropriate activity with little FTO assistance, and reaches proper dispositions.",
      "SourceAppendix": "A-9"
    },
    {
      "CategoryNumber": "21",
      "Rating1_Unacceptable": "Creates officer-safety risks through poor positioning, weapon/control practices, awareness, or accepted safety procedure.",
      "Rating4_Acceptable": "Follows accepted officer-safety procedures and demonstrates them reliably.",
      "Rating7_Superior": "Anticipates danger, keeps partners informed, avoids overconfidence, and consistently models safe officer behavior.",
      "SourceAppendix": "A-9"
    },
    {
      "CategoryNumber": "22",
      "Rating1_Unacceptable": "Uses unsafe search/control practices with suspects or prisoners or fails to maintain a position of advantage.",
      "Rating4_Acceptable": "Uses accepted safety procedures when dealing with suspects and prisoners.",
      "Rating7_Superior": "Anticipates danger, maintains tactical advantage, stays alert, and prevents opportunities for danger from developing.",
      "SourceAppendix": "A-9"
    },
    {
      "CategoryNumber": "23",
      "Rating1_Unacceptable": "Voice/command presence is ineffective, offensive, weak, inappropriate, or escalates the situation.",
      "Rating4_Acceptable": "Uses calm, clear, authoritative verbal control and appropriate word choice.",
      "Rating7_Superior": "Controls situations exceptionally through tone, inflection, word choice, and command bearing, restoring order when others cannot.",
      "SourceAppendix": "A-10"
    },
    {
      "CategoryNumber": "24",
      "Rating1_Unacceptable": "Uses too much force or cannot apply enough force/control for the situation; poor restraint skill.",
      "Rating4_Acceptable": "Obtains and maintains control using an appropriate level of force and restraint technique.",
      "Rating7_Superior": "Demonstrates excellent restraint skill and judgment, selecting and applying the right level of force for the situation.",
      "SourceAppendix": "A-10"
    },
    {
      "CategoryNumber": "25",
      "Rating1_Unacceptable": "Acts without sound reasoning, is indecisive/naive, or cannot identify and select reasonable options.",
      "Rating4_Acceptable": "Reasons through routine problems and reaches acceptable decisions using available information.",
      "Rating7_Superior": "Anticipates outcomes, reasons through complex problems, makes sound independent decisions, and accepts responsibility.",
      "SourceAppendix": "A-10"
    },
    {
      "CategoryNumber": "26",
      "Rating1_Unacceptable": "Uses police radio procedures/codes improperly, violates policy, or is unsure of basic radio protocol.",
      "Rating4_Acceptable": "Uses acceptable radio procedures and demonstrates good working knowledge of common codes/language.",
      "Rating7_Superior": "Consistently follows radio procedure and demonstrates superior knowledge of codes, language, and police-radio operation.",
      "SourceAppendix": "A-10"
    },
    {
      "CategoryNumber": "27",
      "Rating1_Unacceptable": "Misses call sign or directed traffic, needs repeated transmissions, or fails to comprehend radio information.",
      "Rating4_Acceptable": "Tracks own transmissions and maintains general awareness of radio traffic in nearby patrol areas.",
      "Rating7_Superior": "Maintains broad radio awareness, including surrounding areas/frequencies, and uses prior transmissions effectively.",
      "SourceAppendix": "A-11"
    },
    {
      "CategoryNumber": "28",
      "Rating1_Unacceptable": "Transmissions are poorly planned, incorrectly modulated, incomplete, cut off, or use poor microphone/procedure technique.",
      "Rating4_Acceptable": "Transmits clearly, concisely, completely, and with proper radio procedure.",
      "Rating7_Superior": "Communicates calmly and completely even under stress; transmissions are well planned and rarely need repetition.",
      "SourceAppendix": "A-11"
    },
    {
      "CategoryNumber": "29",
      "Rating1_Unacceptable": "Is abrupt, arrogant, overbearing, uncommunicative, biased, or fails to provide appropriate public service.",
      "Rating4_Acceptable": "Is courteous, friendly, empathetic, professional, unbiased, and communicates effectively with citizens.",
      "Rating7_Superior": "Is exceptionally comfortable and effective with citizens, uses strong verbal/non-verbal skills, and remains objective in all contacts.",
      "SourceAppendix": "A-11"
    },
    {
      "CategoryNumber": "30",
      "Rating1_Unacceptable": "Displays hostility, stereotyping, prejudice, bias, or different treatment toward ethnic/cultural/social groups.",
      "Rating4_Acceptable": "Is at ease with people from different groups and serves them objectively and respectfully.",
      "Rating7_Superior": "Understands cultural differences and applies that understanding objectively and effectively to resolve problems.",
      "SourceAppendix": "A-11"
    },
    {
      "CategoryNumber": "31",
      "Rating1_Unacceptable": "Is antagonistic or uncooperative with peers/supervisors, gossips, resents control, or behaves as a lone ranger.",
      "Rating4_Acceptable": "Respects the chain of command, accepts organizational roles, works well with peers/FTOs, and functions as a group member.",
      "Rating7_Superior": "Works comfortably with all department members, understands supervisory roles, supports the organization, and actively assists others.",
      "SourceAppendix": "A-12"
    }
  ],
  "tasks": [
    {
      "ProgramPhase": "I",
      "TaskOrder": "1",
      "TaskName": "Record field notes",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "2",
      "TaskName": "Secure a crime scene",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "3",
      "TaskName": "Determine offense(s) based on incident",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "4",
      "TaskName": "Operate an emergency vehicle",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "5",
      "TaskName": "Employ interpersonal communications skills",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "6",
      "TaskName": "Execute protective measures against blood-borne pathogens",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "7",
      "TaskName": "Respond to calls for service (non-criminal)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "8",
      "TaskName": "Complete an abandoned vehicle notice",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "9",
      "TaskName": "Complete an incident/complaint report using basic fundamentals of report writing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "10",
      "TaskName": "Complete an Armed Forces Traffic Citation (DD Form 1408)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "11",
      "TaskName": "Complete a voluntary statement",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "12",
      "TaskName": "Discuss ethical behavior for law enforcement",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "13",
      "TaskName": "Identify aspects of community policing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "14",
      "TaskName": "Identify jurisdictional areas on assigned installation",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "15",
      "TaskName": "Conduct building checks",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "16",
      "TaskName": "Respond to alarms",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "17",
      "TaskName": "Perform an escort",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "18",
      "TaskName": "Explain the Victim/Witness Assistance Program",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "19",
      "TaskName": "Conduct traffic control",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "20",
      "TaskName": "Conduct Entry/Access Control operation",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "I",
      "TaskOrder": "21",
      "TaskName": "Establish liaison with installation resources",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "1",
      "TaskName": "Record field notes",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "2",
      "TaskName": "Write an incident/complaint report using basic fundamentals of report writing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "3",
      "TaskName": "Determine elements of proof for a crime",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "4",
      "TaskName": "Enforce traffic regulations",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "5",
      "TaskName": "Employ interpersonal communications skills",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "6",
      "TaskName": "Perform a personal search",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "7",
      "TaskName": "Apprehend a suspect",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "8",
      "TaskName": "Conduct an unknown risk vehicle stop",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "9",
      "TaskName": "Conduct an interview",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "10",
      "TaskName": "Respond to calls for service (non-criminal)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "11",
      "TaskName": "Complete a log book entry",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "12",
      "TaskName": "Use crime information systems",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "13",
      "TaskName": "Complete an evidence/property custody receipt",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "14",
      "TaskName": "Complete a complaint of stolen vehicle report",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "15",
      "TaskName": "Complete an evidence tag",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "16",
      "TaskName": "Complete an Armed Forces Traffic Citation (DD Form 1408)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "17",
      "TaskName": "Complete a permissive authorization for search and seizure form",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "18",
      "TaskName": "Complete a voluntary statement",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "19",
      "TaskName": "Identify aspects of intelligence-led policing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "20",
      "TaskName": "Conduct a building and area search",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "21",
      "TaskName": "Conduct a vehicle search",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "22",
      "TaskName": "Use the communications network",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "23",
      "TaskName": "Identify evidence room procedures",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "24",
      "TaskName": "Identify controlled substances",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "II",
      "TaskOrder": "25",
      "TaskName": "Conduct field interviews/frisks",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "1",
      "TaskName": "Record field notes",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "2",
      "TaskName": "Write an incident/complaint report using basic fundamentals of report writing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "3",
      "TaskName": "Determine offense(s) based on incident",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "4",
      "TaskName": "Conduct a high risk (felony) vehicle stop",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "5",
      "TaskName": "Employ interpersonal communications skills",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "6",
      "TaskName": "Advise a suspect of rights",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "7",
      "TaskName": "Conduct an interrogation",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "8",
      "TaskName": "Respond to calls for service (non-criminal)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "9",
      "TaskName": "Respond to a juvenile-related incident",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "10",
      "TaskName": "Complete a US District Court Violation (DD Form 1805)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "11",
      "TaskName": "Transport a suspect",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "12",
      "TaskName": "Complete a receipt for prisoner or detained person",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "13",
      "TaskName": "Process a DUI",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "14",
      "TaskName": "Respond to a domestic incident",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "15",
      "TaskName": "Complete an Armed Forces Traffic Citation (DD Form 1408)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "16",
      "TaskName": "Complete an affidavit/command authorization for search and seizure form",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "17",
      "TaskName": "Record investigative notes",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "18",
      "TaskName": "Interview a witness and complete a voluntary statement form",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "19",
      "TaskName": "Identify aspects of community policing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "20",
      "TaskName": "Respond to an Active Shooter threat",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "21",
      "TaskName": "Respond to explosive threats",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "III",
      "TaskOrder": "22",
      "TaskName": "Respond to sexual assault",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "1",
      "TaskName": "Record field notes",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "2",
      "TaskName": "Write an incident/complaint report using basic fundamentals of report writing",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "3",
      "TaskName": "Determine offense(s) based on incident",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "4",
      "TaskName": "Conduct a high risk (felony) vehicle stop",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "5",
      "TaskName": "Employ interpersonal communications skills",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "6",
      "TaskName": "Respond to calls for service (non-criminal)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "7",
      "TaskName": "Conduct a vehicle patrol",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "IV",
      "TaskOrder": "8",
      "TaskName": "Complete an Armed Forces Traffic Citation (DD Form 1408)",
      "PhaseSpecific": "true",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "1",
      "TaskName": "Employ empty hand defensive tactics",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "2",
      "TaskName": "Employ an impact baton",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "3",
      "TaskName": "Employ restraint devices",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "4",
      "TaskName": "Employ oleoresin capsicum",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "5",
      "TaskName": "Identify characteristics/effects of drugs/alcohol",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "6",
      "TaskName": "Respond to crime against person(s)",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "7",
      "TaskName": "Conduct a seizure",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "8",
      "TaskName": "Use appropriate force",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "9",
      "TaskName": "Respond to a medical incident",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "10",
      "TaskName": "Respond to property crimes",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "11",
      "TaskName": "Detain a suspect",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "12",
      "TaskName": "Complete a statement of force form",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "ANY",
      "TaskOrder": "13",
      "TaskName": "Complete a telephonic threat complaint form",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "OPTIONAL",
      "TaskOrder": "1",
      "TaskName": "Perform one-man cardiopulmonary resuscitation (CPR)",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "OPTIONAL",
      "TaskOrder": "2",
      "TaskName": "Operate a breathalyzer",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "OPTIONAL",
      "TaskOrder": "3",
      "TaskName": "Complete a desk journal entry",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "OPTIONAL",
      "TaskOrder": "4",
      "TaskName": "Operate a preliminary breath analyzer",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "OPTIONAL",
      "TaskOrder": "5",
      "TaskName": "Maintain breathalyzer equipment",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    },
    {
      "ProgramPhase": "OPTIONAL",
      "TaskOrder": "6",
      "TaskName": "Conduct a limited traffic accident investigation",
      "PhaseSpecific": "false",
      "SourceStatus": "verified"
    }
  ],
  "accountCapabilities": [
    "Microsoft/Entra sign-in in the Power Platform version",
    "CAC/PIV-compatible government identity path where supported by the tenant",
    "role-based access control",
    "pending-account approval",
    "multiple roles per user",
    "role/context switching where needed",
    "Watch Commander scope",
    "officer profile data",
    "emergency contacts",
    "account recovery/reset workflow appropriate to Microsoft identity"
  ]
};
