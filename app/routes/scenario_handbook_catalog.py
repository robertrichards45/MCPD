"""Handbook-grounded synthetic Scenario Lab content.

These are training scenarios, not policy or legal conclusions. The integrated
Officer Handbook is used to identify realistic call types, report products,
evidence issues, and decision problems. Current law, signed orders, and command
policy remain controlling.
"""

HANDBOOK_NEXT = {
    'S006': 'S007', 'S007': 'S008', 'S008': 'S009', 'S009': 'S010',
    'S010': 'S011', 'S011': 'S012', 'S012': 'S013', 'S013': 'S014',
    'S014': 'S001',
}

HANDBOOK_SCENARIOS = {
    'S007': {
        'title': 'Traffic Accident — Changing Scene',
        'difficulty': 'Intermediate',
        'category': 'Traffic / Crash Investigation',
        'phase': 'Phase II / III practice',
        'dispatch': 'Respond to a vehicle crash aboard the installation. Injury status and roadway conditions are still being developed.',
        'objective': 'Practice traffic and scene safety, medical triage, driver/vehicle identification, evidence preservation, witness development, diagramming, enforcement articulation, and vehicle disposition.',
        'stages': [
            {'name': 'Arrival', 'prompt': 'Handle the scene using only what is presently observable or reported.', 'reveal': 'The vehicles and roadway are now available for closer inspection. Driver accounts do not fully agree.'},
            {'name': 'Scene Development', 'prompt': 'Continue the investigation and preserve information that may change or disappear.', 'reveal': 'Physical roadway evidence and vehicle damage provide additional information, but they do not by themselves establish fault.'},
            {'name': 'Reconciliation', 'prompt': 'Resolve material conflicts and decide what additional records, statements, measurements, photographs, or resources are needed.', 'reveal': 'The investigation now contains enough developed facts for a reasoned crash sequence and disposition, with any unresolved conflict clearly identified.'},
            {'name': 'Disposition', 'prompt': 'Complete the scene disposition, notifications, enforcement decision if any, and post-call documentation.', 'reveal': 'The live scene is ready to clear when all people, vehicles, evidence, and follow-up tasks have a documented disposition.'},
        ],
    },
    'S008': {
        'title': 'Wanted Person — Warrant Confirmation',
        'difficulty': 'Intermediate',
        'category': 'Warrants / Custody',
        'phase': 'Phase II / III practice',
        'dispatch': 'A records return indicates a possible wanted-person hit. The warrant and extradition status have not yet been confirmed.',
        'objective': 'Practice identity verification, safe temporary detention when lawful, warrant confirmation, extradition limits, rights/search decisions, custody transfer, and release when the holding agency will not extradite.',
        'stages': [
            {'name': 'Hit Received', 'prompt': 'Respond to the possible warrant hit without assuming that an unconfirmed return is the final custody decision.', 'reveal': 'The subject identity can be compared with the return and the entering agency can be contacted for confirmation.'},
            {'name': 'Confirmation', 'prompt': 'Develop the information needed before transport, release, or transfer.', 'reveal': 'The entering agency provides warrant details, safety information, and an extradition instruction specific to this run.'},
            {'name': 'Custody Decision', 'prompt': 'Apply the confirmed information to the person, property, questioning, search, and custody status.', 'reveal': 'The appropriate disposition now depends on the confirmed extradition instruction rather than the existence of the initial hit alone.'},
            {'name': 'Transfer / Release', 'prompt': 'Complete the final transfer or release process and document the agency, time, official, property, and disposition.', 'reveal': 'The wanted-person event is ready for post-call documentation after the custody or release instruction is completed.'},
        ],
    },
    'S009': {
        'title': 'Domestic Abuse — Conflicting Accounts',
        'difficulty': 'Advanced',
        'category': 'Domestic / Victim Response',
        'phase': 'Phase II / III practice',
        'dispatch': 'Respond to a domestic disturbance. The caller reports an argument and possible physical contact; injury and aggressor facts are not yet established.',
        'objective': 'Practice scene control, separation, medical assessment, firsthand statements, injury/scene documentation, protective-order and history checks, legal articulation, victim resources, CID/FAP/command coordination, and rights issues.',
        'stages': [
            {'name': 'Arrival', 'prompt': 'Stabilize the scene and determine immediate safety and medical needs.', 'reveal': 'The involved parties give different accounts. Their physical and emotional condition can now be documented separately.'},
            {'name': 'Separate Accounts', 'prompt': 'Develop each account and identify direct observations, spontaneous statements, injuries, witnesses, children, and other relevant facts.', 'reveal': 'A material conflict remains about who initiated the physical contact and whether any conduct was defensive.'},
            {'name': 'Corroboration', 'prompt': 'Use available evidence, records, witnesses, and lawful questioning to resolve or document the conflict without forcing a conclusion.', 'reveal': 'The evidence supports a fact-based disposition, but the simulator does not decide guilt for the officer.'},
            {'name': 'Disposition', 'prompt': 'Complete safety planning, victim information, notifications, custody/release decisions, evidence, and documentation required by the facts.', 'reveal': 'The domestic call is ready for post-call paperwork and FTO review.'},
        ],
    },
    'S010': {
        'title': 'DUI / Impairment Investigation',
        'difficulty': 'Advanced',
        'category': 'Traffic / DUI',
        'phase': 'Phase III practice',
        'dispatch': 'Investigate a driver after observed driving behavior or a gate/incident contact raises an impairment concern.',
        'objective': 'Practice objective driving and impairment observations, medical alternatives, field-sobriety decision making, probable-cause articulation, rights timing, current implied-consent process, chemical-test/refusal documentation, and vehicle disposition.',
        'stages': [
            {'name': 'Driving / Initial Contact', 'prompt': 'Document the reason for contact and separate objective observations from conclusions.', 'reveal': 'The driver provides an explanation that may involve alcohol, medication, fatigue, a medical issue, or another run-specific factor.'},
            {'name': 'Impairment Investigation', 'prompt': 'Decide what additional observations, questions, medical screening, or standardized testing are appropriate.', 'reveal': 'The driver response to testing and any limitations are now part of the run; do not invent missing test clues.'},
            {'name': 'Arrest / No-Arrest Decision', 'prompt': 'State whether the developed facts establish the lawful basis for your next action and identify the point at which that basis is reached.', 'reveal': 'If an arrest path is supported, the current approved implied-consent process and test/refusal documentation become relevant.'},
            {'name': 'Processing / Disposition', 'prompt': 'Complete test/refusal documentation, citations or notices, tow/impound decisions, custody/release, and the report timeline as applicable.', 'reveal': 'The DUI investigation is ready for post-call paperwork. Current legal thresholds and warning language must be verified from controlling authority.'},
        ],
    },
    'S011': {
        'title': 'Unsecured Building — Possible Forced Entry',
        'difficulty': 'Intermediate',
        'category': 'Patrol / Physical Security',
        'phase': 'Phase I / II practice',
        'dispatch': 'During patrol, an installation building is found unsecured. It is not yet known whether this is a routine securing problem or an incident.',
        'objective': 'Practice approach safety, exterior assessment, forced-entry indicators, backup/resource decisions, keyholder coordination, photographs when needed, scene protection, building disposition, and escalation from routine service to a reportable incident.',
        'stages': [
            {'name': 'Discovery', 'prompt': 'Handle the unsecured building without assuming it is either harmless or a burglary.', 'reveal': 'The entry point can be examined for damage, tampering, alarm information, and other observable indicators.'},
            {'name': 'Assessment', 'prompt': 'Develop enough facts to decide whether this remains a routine unsecured-building response or has become a criminal/security incident.', 'reveal': 'A keyholder or facility representative can be coordinated, but the timing and condition vary by run.'},
            {'name': 'Building / Evidence', 'prompt': 'Protect the scene, preserve transient evidence, and coordinate any lawful interior/security response appropriate to the developed facts.', 'reveal': 'The building condition is now sufficiently developed for a routine-security or incident disposition.'},
            {'name': 'Disposition', 'prompt': 'Document who secured the building, notifications, photographs/evidence, and whether a CCN or additional command screening was triggered.', 'reveal': 'The unsecured-building call is ready for post-call documentation.'},
        ],
    },
    'S012': {
        'title': 'Found Property — Custody and Ownership',
        'difficulty': 'Basic / Intermediate',
        'category': 'Property / Evidence',
        'phase': 'Phase I / II practice',
        'dispatch': 'Respond to found or surrendered property aboard the installation. Ownership and evidentiary significance are not yet known.',
        'objective': 'Practice exact recovery-location documentation, item description, ownership verification, lawful examination limits, custody transfer, evidence/property documentation, special notifications, and final release or safekeeping.',
        'stages': [
            {'name': 'Recovery', 'prompt': 'Take control of the property while preserving where, how, and by whom it was found.', 'reveal': 'The item can now be described and checked for external identifying information without assuming ownership.'},
            {'name': 'Identify / Classify', 'prompt': 'Determine whether the property is ordinary found property, evidence, sensitive property, or otherwise requires special handling.', 'reveal': 'Ownership information may be verifiable, unavailable, or conflicting depending on this run.'},
            {'name': 'Custody', 'prompt': 'Maintain an accurate custody trail and decide whether any search, opening, testing, or special handling has lawful authority.', 'reveal': 'The property now has a documented custody and ownership status.'},
            {'name': 'Disposition', 'prompt': 'Complete safekeeping, evidence submission, owner release, notifications, and paperwork based on what was actually established.', 'reveal': 'The property call is ready for post-call documentation.'},
        ],
    },
    'S013': {
        'title': 'Odor / Suspected Controlled Substance — Search Authority',
        'difficulty': 'Advanced',
        'category': 'Search / Evidence',
        'phase': 'Phase II / III practice',
        'dispatch': 'Investigate a reported odor or suspected controlled-substance issue. The source, substance, and lawful search authority are not established at dispatch.',
        'objective': 'Practice corroboration, current-law research, consent and scope, refusal/withdrawal, rights timing, evidence handling, search documentation, and disposition when no contraband is found.',
        'stages': [
            {'name': 'Initial Observation', 'prompt': 'Develop objective facts and identify the possible source without treating an odor allegation as a completed offense.', 'reveal': 'The source may involve a person, vehicle, room, or another location and additional corroboration varies by run.'},
            {'name': 'Authority Decision', 'prompt': 'Identify what lawful authority, if any, permits further search or seizure and what facts support it.', 'reveal': 'If consent is requested, the subject response and scope are run-specific. Consent may be refused or limited.'},
            {'name': 'Search / No Search', 'prompt': 'Stay within the lawful scope and document what is or is not found. Reassess if consent changes or facts fail to corroborate the suspicion.', 'reveal': 'The run may produce evidence, no contraband, or an unrelated lawful explanation.'},
            {'name': 'Disposition', 'prompt': 'Complete evidence handling, rights, tow/search documentation, notifications, and release/enforcement decision as supported by the facts.', 'reveal': 'The controlled-substance/search-authority call is ready for post-call documentation.'},
        ],
    },
    'S014': {
        'title': 'UAS / Drone Sighting — Command Reporting',
        'difficulty': 'Advanced',
        'category': 'Security / Command Reporting',
        'phase': 'Phase II / III practice',
        'dispatch': 'A small unmanned aircraft has been reported over or near an installation area. Operator identity, intent, and mission/security impact are unknown.',
        'objective': 'Practice safe observation, time/location/description documentation, operator/witness development, video preservation, command notification, security/mission-impact assessment, SITREP/UAS and OPREP screening, and evidence handoff without improvised counter-UAS action.',
        'stages': [
            {'name': 'Sighting', 'prompt': 'Respond, observe safely, and communicate the information needed to start the incident record.', 'reveal': 'The UAS movement, duration, location, and possible operator information develop differently in each run.'},
            {'name': 'Search / Documentation', 'prompt': 'Preserve observations and available video while coordinating resources and attempting to identify witnesses or an operator lawfully.', 'reveal': 'The sighting may end, repeat, or develop a possible operator/location; mission or security impact remains a separate question.'},
            {'name': 'Command Screening', 'prompt': 'Assess notifications and required command products based on the developed security/mission facts and current orders.', 'reveal': 'The event now contains enough information for Watch Commander/command screening and the appropriate UAS reporting products.'},
            {'name': 'Disposition', 'prompt': 'Complete notifications, evidence/video preservation, operator or witness disposition, and all required incident/command reporting products.', 'reveal': 'The UAS event is ready for post-call documentation and command review.'},
        ],
    },
}

HANDBOOK_VARIANTS = {
    'S007': {
        'crash_type': ('POV versus POV', 'government vehicle versus POV', 'single vehicle versus fixed object'),
        'injury': ('no injury initially reported', 'one driver reports neck pain', 'one occupant requests EMS evaluation'),
        'road': ('controlled intersection', 'parking-lot travel lane', 'two-lane installation roadway', 'low-light roadway near a gate'),
        'scene_evidence': ('debris and a possible point of impact', 'short tire marks and displaced debris', 'fluid trail near final rest', 'little useful roadway evidence'),
        'witness': ('independent witness available', 'drivers give conflicting accounts', 'no independent witness identified', 'camera coverage may exist'),
    },
    'S008': {
        'hit_source': ('GCIC return', 'NCIC return', 'outside-agency confirmation request'),
        'identity': ('identity matches cleanly', 'middle-name discrepancy requires clarification', 'date-of-birth match but address differs'),
        'extradition': ('full extradition confirmed', 'agency declines extradition from this location', 'limited extradition requires clarification'),
        'caution': ('no special caution returned', 'officer-use-caution flag returned', 'medical information is provided by the subject'),
    },
    'S009': {
        'relationship': ('married spouses', 'former dating partners', 'cohabitating partners', 'military member and civilian spouse'),
        'injury': ('no visible injury', 'minor visible redness', 'reported pain with no obvious injury', 'visible injury requiring EMS assessment'),
        'witness': ('neighbor heard but did not see the event', 'child was present but not a reliable interview source', 'adult witness saw part of the contact', 'no independent witness'),
        'protective_order': ('no order reported', 'one party claims an order exists', 'dispatch can verify an active protective-order record'),
        'conflict': ('both claim the other initiated contact', 'one claims self-defense', 'accounts differ on whether physical contact occurred'),
    },
    'S010': {
        'contact_basis': ('weaving within lane', 'stop-sign violation', 'gate officer reports possible impairment', 'minor crash with possible impairment indicators'),
        'presentation': ('odor and bloodshot eyes reported', 'slowed speech and poor balance', 'fatigue and medication are claimed', 'possible medical condition complicates assessment'),
        'testing': ('driver agrees to appropriate standardized testing', 'driver reports a physical limitation', 'driver refuses field testing', 'testing begins but must be discontinued for a medical reason'),
        'implied_response': ('agrees to the designated state test', 'refuses the designated state test', 'asks questions before giving an answer'),
    },
    'S011': {
        'entry': ('unlocked exterior door', 'door not fully latched', 'damaged latch with possible pry marks', 'door open with no obvious damage'),
        'alarm': ('no alarm information', 'alarm system shows a recent event', 'alarm appears normal', 'dispatch reports repeated door alarm activity'),
        'keyholder': ('keyholder is nearby', 'keyholder has a delayed response', 'facility duty representative is initially unreachable'),
        'interior_indicator': ('nothing unusual visible from outside', 'property appears disturbed through a window', 'lighting is on unexpectedly', 'no additional indicator is visible'),
    },
    'S012': {
        'item': ('backpack containing a laptop and charger', 'wallet with identification and cards', 'government identification card and keys', 'USB storage device with no owner label', 'sealed package with an owner name'),
        'recovery': ('parking area', 'facility lobby', 'barracks common area', 'roadside near a building'),
        'ownership': ('owner can be verified through identifying information', 'multiple people claim the item', 'owner is not immediately located', 'facility records may identify the owner'),
        'condition': ('apparently intact', 'wet and soiled', 'scratched but functional-looking', 'contents or condition cannot be verified without opening it'),
    },
    'S013': {
        'source': ('occupied vehicle', 'barracks room doorway', 'individual in a common area', 'parked vehicle after a lawful contact'),
        'initial_fact': ('odor reported by another officer', 'odor personally detected by the responding officer', 'staff reports suspected marijuana odor but cannot identify the source', 'possible odor is mixed with another strong smell'),
        'consent': ('consent is granted with a limited scope', 'consent is refused', 'consent is initially granted and later withdrawn', 'no consent is requested until other facts are developed'),
        'outcome': ('no contraband is found', 'suspected plant material is located', 'an unrelated lawful item explains part of the report', 'evidence significance remains uncertain pending verification'),
    },
    'S014': {
        'sighting': ('brief transit across the area', 'hovering near a facility', 'repeated passes over the same area', 'drone is seen and then quickly lost from view'),
        'operator': ('no operator visible', 'possible operator seen in a public area', 'witness points toward a possible launch area', 'operator identity remains unknown'),
        'video': ('officer can document the sighting', 'facility camera may have captured part of the event', 'witness has phone video', 'no useful video is immediately available'),
        'impact': ('no mission impact established yet', 'activity pauses briefly while the event is assessed', 'security personnel report concern near a controlled area', 'safety impact is uncertain'),
    },
}

HANDBOOK_CAST = {
    'S007': {
        'scene': 'Installation roadway / crash scene',
        'visual': ['Traffic and secondary-collision exposure', 'Vehicle final-rest positions may change if moved', 'Roadway evidence and injuries vary by run'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('injury|ems', 'The initial injury report is not final; verify it on scene.'), ('tow|traffic', 'Tow and additional traffic resources have not been requested unless you request them.')]},
            {'id': 'driver1', 'name': 'Driver One', 'role': 'Driver', 'from': 0, 'facts': [('what happened|describe', 'I can tell you my sequence, but the other driver may disagree.'), ('injury|hurt', 'Ask me directly whether I am injured or want medical evaluation.')]},
            {'id': 'driver2', 'name': 'Driver Two', 'role': 'Driver', 'from': 0, 'facts': [('what happened|describe', 'I have my own account of the collision.'), ('vehicle|damage', 'I can identify what damage I noticed after the crash.')]},
            {'id': 'crash_witness', 'name': 'Independent Witness', 'role': 'Witness', 'from': 1, 'facts': [('see|witness|happened', 'If I was present for this run, I will tell you only what I actually observed.')]},
        ],
    },
    'S008': {
        'scene': 'Controlled contact / warrant verification',
        'visual': ['Possible wanted-person return', 'Identity and extradition must be confirmed', 'Custody outcome is not predetermined'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('warrant|hit|want', 'A possible wanted-person return exists; confirmation with the entering agency is still required.'), ('extradition|confirm', 'I can contact the entering agency when you request confirmation.')]},
            {'id': 'wanted_subject', 'name': 'Subject', 'role': 'Subject', 'from': 0, 'facts': [('identity|name|dob', 'I will provide identifying information when asked.'), ('warrant|know', 'I may or may not know about the warrant; ask me specifically.')]},
            {'id': 'agency', 'name': 'Entering Agency', 'role': 'Phone / Radio Contact', 'from': 1, 'facts': [('confirm|warrant|number|extradition', 'I can provide the run-specific confirmation, extradition instruction, and agency contact information.')]},
        ],
    },
    'S009': {
        'scene': 'Residence / domestic disturbance scene',
        'visual': ['Separate involved parties when practical', 'Injury and emotional state must be observed, not assumed', 'Witness and protective-order information varies'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('protective order|history|records', 'I can run available records when you provide the identities and request the check.'), ('ems|medical', 'EMS can be started if requested or if the developed injury requires it.')]},
            {'id': 'party1', 'name': 'Party One', 'role': 'Involved Person', 'from': 0, 'facts': [('what happened|account', 'I will give my account separately if you ask me.'), ('injury|hurt', 'Ask what I feel and document what you actually observe.')]},
            {'id': 'party2', 'name': 'Party Two', 'role': 'Involved Person', 'from': 0, 'facts': [('what happened|account', 'My account does not necessarily match the other person’s.'), ('self defense|defend', 'If self-defense is part of my account, I will explain the facts I claim support it.')]},
            {'id': 'domestic_witness', 'name': 'Potential Witness', 'role': 'Witness', 'from': 1, 'facts': [('see|hear|witness', 'I can distinguish what I saw from what I only heard.')]},
        ],
    },
    'S010': {
        'scene': 'Installation roadway / DUI investigation',
        'visual': ['Driving basis must be documented before impairment conclusions', 'Medical limitations can affect testing', 'Current implied-consent process may become relevant'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('records|license|vehicle', 'I can run driver and vehicle information when requested.'), ('backup|unit', 'No cover unit is assigned unless requested.')]},
            {'id': 'dui_driver', 'name': 'Driver', 'role': 'Driver', 'from': 0, 'facts': [('drink|alcohol|medication|sleep|medical', 'My explanation is specific to this run; ask one fact at a time.'), ('test|field sobriety|limitation', 'I may cooperate, refuse, or report a limitation depending on this run.')]},
        ],
    },
    'S011': {
        'scene': 'Exterior of unsecured installation building',
        'visual': ['Unsecured does not automatically mean forced entry', 'Entry-point condition can change when secured', 'Keyholder/alarm information may be needed'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('alarm|keyholder|facility', 'I can check available alarm and contact information when you request it.'), ('backup|unit', 'Additional units are available by request.')]},
            {'id': 'keyholder', 'name': 'Facility Representative', 'role': 'Keyholder / Reporting Contact', 'from': 1, 'facts': [('secure|door|normal', 'I can explain how the building is normally secured and whether the condition is expected.'), ('missing|property|inside', 'I can help identify whether anything appears disturbed or missing once the scene can lawfully be assessed.')]},
        ],
    },
    'S012': {
        'scene': 'Found / surrendered property location',
        'visual': ['Exact recovery location matters', 'Property should be described before custody changes', 'Ownership may require records or identifying information'],
        'cast': [
            {'id': 'finder', 'name': 'Finder / Reporting Person', 'role': 'Reporting Party', 'from': 0, 'facts': [('where|found|when', 'I can tell you exactly where and when I found it.'), ('touch|move|open', 'I can tell you whether I moved, opened, or handled it before police arrived.')]},
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('owner|serial|records', 'I can assist with available records when you provide identifying information.')]},
            {'id': 'claimant', 'name': 'Possible Owner', 'role': 'Claimant', 'from': 2, 'facts': [('describe|owner|prove', 'I can describe the item and provide ownership information if I am the claimant in this run.')]},
        ],
    },
    'S013': {
        'scene': 'Vehicle / room / common-area contact',
        'visual': ['Reported odor source is not automatically proven', 'Search authority and scope must be articulated', 'Consent can be refused, limited, or withdrawn'],
        'cast': [
            {'id': 'reporting_officer', 'name': 'Reporting Officer / Staff', 'role': 'Reporting Source', 'from': 0, 'facts': [('odor|source|where', 'I will tell you what I personally detected or what was merely reported, depending on the run.')]},
            {'id': 'search_subject', 'name': 'Subject', 'role': 'Subject', 'from': 0, 'facts': [('consent|search|permission', 'My consent response and any limits are specific to this run.'), ('what|odor|marijuana', 'I can give an explanation, but it does not by itself establish the facts.')]},
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('records|wants', 'No records check has been run unless you request one.')]},
        ],
    },
    'S014': {
        'scene': 'Installation UAS / drone sighting',
        'visual': ['Time, location, direction, description, and duration are per-run facts', 'Operator may never be located', 'Video and security/mission impact must be preserved separately'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [('notify|watch commander|command', 'I can log and relay notifications when you provide the developing facts.'), ('operator|unit', 'No operator has been confirmed from dispatch information.')]},
            {'id': 'uas_witness', 'name': 'Witness', 'role': 'Witness', 'from': 0, 'facts': [('see|drone|direction|time', 'I can tell you what I personally observed, including direction and duration if I remember it.'), ('video|phone', 'Whether I have useful video depends on this run.')]},
            {'id': 'possible_operator', 'name': 'Possible Operator', 'role': 'Person of Interest', 'from': 2, 'facts': [('drone|operate|owner', 'If I am actually connected to the aircraft in this run, develop that through facts rather than assuming it.')]},
        ],
    },
}
