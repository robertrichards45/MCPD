import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

bp = Blueprint('scenario_lab', __name__, url_prefix='/scenario-lab')
SESSION_KEY = 'sentinel_scenario_lab_v2'

# Scenario Lab is synthetic training only. It does not write official DOR
# ratings, make advancement decisions, or certify trainee performance.
SCENARIOS = {
    'S001': {
        'title': 'Disorderly Person Refusing to Leave',
        'difficulty': 'Intermediate',
        'category': 'Calls for Service',
        'phase': 'Phase II / III practice',
        'dispatch': 'Unit 214, respond to Building 7130 for a disorderly individual refusing to leave.',
        'objective': 'Practice scene approach, de-escalation, investigation, legal articulation, and disposition.',
        'stages': [
            {'name': 'Arrival', 'prompt': 'You are arriving at Building 7130. What do you do first?', 'reveal': 'A staff member meets you outside and says the subject is still inside, is yelling, and has refused multiple requests to leave. No weapon has been reported.'},
            {'name': 'Initial Contact', 'prompt': 'You now have the staff member’s initial information. How do you approach and handle first contact?', 'reveal': 'The subject is argumentative but keeps his hands visible. He says he has a right to remain because he was invited earlier. Staff says the invitation was revoked after the disturbance began.'},
            {'name': 'Investigation', 'prompt': 'What facts do you need to establish before deciding what action is appropriate?', 'reveal': 'A second employee says they personally heard the subject being told to leave. Video is available. The subject begins to calm down and says he will leave if the officer explains what happens next.'},
            {'name': 'Disposition', 'prompt': 'Describe your disposition, notifications, and documentation based only on the facts developed.', 'reveal': 'Scenario complete. The instructor should review whether the trainee developed the facts, used appropriate communication and safety practices, and clearly articulated the final disposition.'},
        ],
    },
    'S002': {
        'title': 'Suspicious Vehicle at Main Gate',
        'difficulty': 'Basic',
        'category': 'Access Control',
        'phase': 'Phase I / II practice',
        'dispatch': 'Main Gate requests patrol assistance with a driver who cannot provide valid installation access credentials and is becoming argumentative.',
        'objective': 'Practice officer safety, identification, access-control decision making, communication, and documentation.',
        'stages': [
            {'name': 'Response', 'prompt': 'What information and safety considerations do you address before and upon arrival?', 'reveal': 'Gate personnel advise the vehicle is stopped in the inspection area. The driver has a state license but no valid installation credential and says he is meeting a contractor.'},
            {'name': 'Contact', 'prompt': 'How do you conduct the contact and what do you need to verify?', 'reveal': 'The driver becomes calmer when the process is explained. The named contractor exists, but no sponsor is immediately available at the gate.'},
            {'name': 'Verification', 'prompt': 'What additional checks, coordination, or questions are appropriate before deciding access?', 'reveal': 'The contractor confirms the meeting but advises the driver was not pre-cleared for access. No other suspicious indicators are developed.'},
            {'name': 'Disposition', 'prompt': 'What is your final action and what do you document?', 'reveal': 'Scenario complete. Review access-control procedure, communication, officer safety, and documentation decisions with the FTO.'},
        ],
    },
    'S003': {
        'title': 'Damage to Government Property',
        'difficulty': 'Intermediate',
        'category': 'Investigation',
        'phase': 'Phase II / III practice',
        'dispatch': 'Respond to a report of a contractor vehicle striking government property near a facility parking area.',
        'objective': 'Practice witness development, damage documentation, evidence collection, and articulation of willful, negligent, or accidental facts without guessing.',
        'stages': [
            {'name': 'Scene', 'prompt': 'What do you do on arrival and what do you preserve or document first?', 'reveal': 'A small government-owned light pole is visibly damaged. A white contractor pickup is nearby. No one is injured.'},
            {'name': 'Witnesses', 'prompt': 'Who do you identify or interview, and what facts are you trying to establish?', 'reveal': 'A facility employee says another worker told her the truck struck the pole earlier. She did not witness the collision herself.'},
            {'name': 'Evidence', 'prompt': 'What evidence or corroboration do you seek before drawing conclusions?', 'reveal': 'The pickup has fresh damage consistent with contact. A worker says he saw the truck back into the pole. The driver is available and says he did not realize contact occurred.'},
            {'name': 'Disposition', 'prompt': 'Explain how you document the incident and distinguish observed facts from conclusions.', 'reveal': 'Scenario complete. The FTO should review investigative steps, evidence handling, articulation, reporting, and whether the trainee avoided unsupported conclusions.'},
        ],
    },
    'S004': {
        'title': 'Larceny / Shoplifting Report',
        'difficulty': 'Intermediate',
        'category': 'Investigation',
        'phase': 'Phase II / III practice',
        'dispatch': 'Respond to a reported theft where staff have identified a possible subject and recovered property may be involved.',
        'objective': 'Practice interviews, statements, property/value documentation, evidence handling, and screening/notification considerations.',
        'stages': [
            {'name': 'Initial Response', 'prompt': 'What do you do first and who do you separate or identify?', 'reveal': 'Store staff has a subject waiting in an office. Merchandise is on a table. A loss-prevention employee says they observed concealment.'},
            {'name': 'Investigation', 'prompt': 'What questions and evidence are important before deciding enforcement action?', 'reveal': 'Loss prevention can provide a written statement and video. The merchandise has a documented retail value and was recovered before leaving the facility.'},
            {'name': 'Legal / Policy Review', 'prompt': 'What facts, notifications, and policy requirements do you verify before disposition?', 'reveal': 'The subject denies intent to steal and says the item was placed in a bag while carrying other property. Video must be reviewed to resolve important factual details.'},
            {'name': 'Disposition', 'prompt': 'Describe your disposition and complete report/paperwork considerations without assuming facts not established.', 'reveal': 'Scenario complete. Review fact development, statements, evidence, legal articulation, paperwork, and required screening with the FTO.'},
        ],
    },
    'S005': {
        'title': 'Traffic Stop - Escalating Driver',
        'difficulty': 'Advanced',
        'category': 'Traffic Enforcement',
        'phase': 'Phase II / III practice',
        'dispatch': 'Conduct a traffic stop after observing a moving violation. The driver becomes increasingly argumentative after contact.',
        'objective': 'Practice radio procedures, positioning, officer safety, legal authority, communication, enforcement decision making, and report articulation.',
        'stages': [
            {'name': 'Initiation', 'prompt': 'Describe how you initiate the stop and what information you communicate.', 'reveal': 'The vehicle stops in a safe location. The driver remains seated but immediately begins yelling that the stop is unlawful.'},
            {'name': 'Contact', 'prompt': 'How do you manage officer safety and communication while obtaining required information?', 'reveal': 'The driver provides a license and registration but repeatedly reaches toward the center console after being asked to keep hands visible.'},
            {'name': 'Decision Point', 'prompt': 'What do you do next, and what facts support your decisions?', 'reveal': 'The driver complies after a clear direction. No weapon or contraband is observed. Records checks return without a wanted status.'},
            {'name': 'Disposition', 'prompt': 'Describe the enforcement decision, communication, and documentation.', 'reveal': 'Scenario complete. The FTO should review radio procedure, safety, conflict control, legal articulation, judgment, and professionalism.'},
        ],
    },
    'S006': {
        'title': 'Medical Assist with Conflicting Information',
        'difficulty': 'Basic',
        'category': 'Calls for Service',
        'phase': 'Phase I / II practice',
        'dispatch': 'Respond to a workplace medical assist. Coworkers provide conflicting information about what happened before the patient became ill.',
        'objective': 'Practice scene organization, witness separation, fact collection, medical-assist documentation, and disposition.',
        'stages': [
            {'name': 'Arrival', 'prompt': 'What are your immediate priorities on arrival?', 'reveal': 'EMS is en route. The patient is conscious but confused. One coworker says the patient fell; another says the patient sat down before becoming ill.'},
            {'name': 'Scene Organization', 'prompt': 'How do you organize the scene and gather reliable information without interfering with medical care?', 'reveal': 'The patient denies being struck. One coworker admits they did not actually see the beginning of the incident.'},
            {'name': 'Clarification', 'prompt': 'What facts still need clarification and what documentation do you obtain?', 'reveal': 'A witness who saw the full event says the patient became dizzy, sat down, and then slid to the floor. No assault or workplace accident hazard is identified.'},
            {'name': 'Disposition', 'prompt': 'Describe your final documentation and disposition.', 'reveal': 'Scenario complete. Review witness assessment, scene organization, documentation, and disposition with the FTO.'},
        ],
    },
}

# Coaching areas are aligned to concepts in the Standard Evaluation Guidelines.
# The application intentionally does not auto-assign the official 1/4/7 DOR values.
PRACTICE_AREAS = [
    ('Investigative Skills', ['identify', 'interview', 'witness', 'statement', 'evidence', 'video', 'photo', 'photograph', 'ask', 'verify']),
    ('Interview / Interrogation Skills', ['ask', 'question', 'interview', 'separate', 'statement', 'rapport', 'clarify']),
    ('Officer Safety: General', ['cover', 'distance', 'hands', 'position', 'backup', 'weapon', 'approach', 'visibility']),
    ('Problem Solving / Decision Making', ['assess', 'plan', 'priority', 'risk', 'options', 'de-escalat', 'supervisor', 'decide']),
    ('Radio / Communications', ['radio', 'dispatch', 'status', 'location', 'backup', 'traffic', 'transmit', 'clear']),
    ('With Citizens: General', ['calm', 'explain', 'professional', 'respect', 'listen', 'de-escalat', 'courteous']),
    ('Legal / Policy Articulation', ['reasonable suspicion', 'probable cause', 'authority', 'consent', 'detain', 'arrest', 'citation', 'policy', 'procedure', 'order']),
    ('Report Writing / Documentation', ['report', 'document', 'ccn', 'blotter', 'photograph', 'evidence', 'statement', 'disposition']),
]

# Each decision point has a stage-specific rubric. A trainee must demonstrate a
# minimum number of concepts before the scenario reveals additional facts. This
# prevents generic or obviously poor answers from being treated as successful.
SCENARIO_RUBRICS = {
    'S001': [
        {'minimum': 3, 'criteria': [
            ('Radio / arrival status', ('dispatch', 'radio', 'on scene', 'location', 'status'), 'Include what you communicate to dispatch as you arrive.'),
            ('Scene safety / positioning', ('distance', 'position', 'cover', 'hands', 'approach', 'safely', 'threat', 'risk'), 'Explain how you assess the scene and position yourself before contact.'),
            ('Reporting-party contact', ('staff', 'reporting', 'complainant', 'employee', 'witness', 'contact'), 'Identify who you need to contact first and what initial information you need.'),
            ('Backup / resources', ('backup', 'additional unit', 'another unit', 'assistance'), 'Consider whether additional resources are needed based on the call information.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Officer safety', ('hands', 'distance', 'position', 'cover', 'safety'), 'Describe the safety considerations you maintain during first contact.'),
            ('Professional communication', ('calm', 'professional', 'explain', 'listen', 'de-escalat', 'rapport'), 'Describe how you communicate to lower tension while maintaining control.'),
            ('Subject account', ('ask', 'question', 'subject', 'his side', 'account', 'what occurred'), 'Develop the subject’s account instead of relying on only one side.'),
            ('Authority / leave issue', ('leave', 'revoked', 'authority', 'trespass', 'order', 'invitation'), 'Identify the authority/factual issue that must be clarified before enforcement.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Firsthand witnesses', ('witness', 'firsthand', 'personally heard', 'separate', 'interview'), 'Establish who personally observed or heard the relevant conduct.'),
            ('Corroboration', ('video', 'camera', 'evidence', 'corroborat', 'review'), 'Identify available evidence that can corroborate or contradict accounts.'),
            ('Notice to leave', ('told to leave', 'directed to leave', 'notice', 'revoked', 'leave'), 'Establish exactly what direction was given and whether it was communicated.'),
            ('Legal / policy basis', ('authority', 'probable cause', 'reasonable suspicion', 'policy', 'procedure', 'elements', 'facts'), 'Explain what facts and authority would support any enforcement decision.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Fact-based disposition', ('based on', 'facts', 'disposition', 'leave', 'citation', 'arrest', 'release', 'warning'), 'State a disposition tied to the facts actually developed.'),
            ('Notifications', ('dispatch', 'supervisor', 'notify', 'status', 'clear'), 'Identify required status or supervisory notifications.'),
            ('Documentation', ('report', 'document', 'ccn', 'blotter', 'statement'), 'Explain what you document and where.'),
            ('Evidence / statements', ('evidence', 'video', 'statement', 'witness'), 'Account for relevant statements and evidence in the final disposition.'),
        ]},
    ],
    'S002': [
        {'minimum': 2, 'criteria': [
            ('Gate coordination', ('gate', 'dispatch', 'inspection area', 'status', 'coordinate'), 'Coordinate with gate personnel and confirm the situation before contact.'),
            ('Officer safety', ('position', 'hands', 'occupant', 'vehicle', 'safety', 'approach'), 'Address safe vehicle-contact positioning and occupant behavior.'),
            ('Identity / purpose', ('identify', 'license', 'credential', 'purpose', 'meeting', 'contractor'), 'Identify the driver and purpose for seeking access.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Identity verification', ('license', 'identity', 'verify', 'credential'), 'Verify identity and available credentials rather than accepting the explanation at face value.'),
            ('Sponsor / destination', ('sponsor', 'contractor', 'meeting', 'destination', 'contact'), 'Verify who is expecting the driver and why.'),
            ('Professional control', ('calm', 'explain', 'professional', 'listen', 'instruction'), 'Explain the process while maintaining control of the contact.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Sponsor confirmation', ('sponsor', 'contractor', 'confirm', 'verify', 'contact'), 'Confirm the claimed visit through an appropriate source.'),
            ('Access requirements', ('access', 'credential', 'pre-clear', 'policy', 'procedure', 'visitor'), 'Apply the installation access process rather than improvising.'),
            ('Additional checks', ('check', 'records', 'dispatch', 'vehicle', 'identity'), 'Identify any appropriate checks before deciding access.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Access disposition', ('deny', 'access', 'turn around', 'visitor', 'escort', 'release'), 'State the access disposition supported by the established facts and procedure.'),
            ('Communication', ('explain', 'professional', 'notify', 'gate', 'dispatch'), 'Explain the outcome and coordinate it with gate personnel.'),
            ('Documentation', ('document', 'report', 'blotter', 'entry', 'record'), 'State what record or documentation is required.'),
        ]},
    ],
    'S003': [
        {'minimum': 3, 'criteria': [
            ('Scene safety / approach', ('safe', 'safety', 'approach', 'position', 'scene'), 'Address scene safety before focusing on property damage.'),
            ('Notifications / status', ('dispatch', 'radio', 'notify', 'on scene', 'status'), 'Include appropriate arrival/status communication.'),
            ('Identify involved persons', ('identify', 'witness', 'driver', 'employee', 'reporting'), 'Identify the people connected to the incident.'),
            ('Preserve / document damage', ('photo', 'photograph', 'damage', 'document', 'preserve', 'vehicle'), 'Preserve and document the visible scene before it changes.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Reporting person interview', ('reporting', 'employee', 'complainant', 'interview', 'ask'), 'Clarify what the reporting person personally knows.'),
            ('Firsthand witness identification', ('witness', 'actually saw', 'firsthand', 'personally', 'who saw'), 'Separate firsthand knowledge from hearsay.'),
            ('Driver / vehicle identification', ('driver', 'vehicle', 'operator', 'identify', 'contractor'), 'Identify the driver/operator and involved vehicle.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Physical corroboration', ('damage', 'vehicle', 'pole', 'match', 'consistent', 'physical'), 'Compare physical damage and scene evidence without overstating what it proves.'),
            ('Witness corroboration', ('witness', 'statement', 'interview', 'saw', 'account'), 'Obtain the firsthand witness account.'),
            ('Driver interview', ('driver', 'interview', 'ask', 'statement', 'account'), 'Obtain and document the driver’s explanation.'),
            ('Evidence documentation', ('photo', 'photograph', 'video', 'evidence', 'document'), 'Document and preserve available evidence.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Observed vs reported facts', ('observed', 'stated', 'reported', 'according', 'facts', 'witness'), 'Clearly distinguish what you observed from what others reported.'),
            ('Culpability not assumed', ('accident', 'negligent', 'willful', 'intent', 'without assuming', 'based on facts'), 'Do not label intent or negligence beyond what the evidence supports.'),
            ('Documentation', ('report', 'document', 'ccn', 'blotter', 'statement'), 'Complete the appropriate written documentation.'),
            ('Notifications / evidence', ('notify', 'supervisor', 'evidence', 'photo', 'statement'), 'Address required notifications and evidence handling.'),
        ]},
    ],
    'S004': [
        {'minimum': 3, 'criteria': [
            ('Scene / subject safety', ('safety', 'subject', 'hands', 'separate', 'control'), 'Maintain safe control of the contact and involved persons.'),
            ('Identify parties', ('identify', 'loss prevention', 'staff', 'subject', 'witness'), 'Identify the subject and reporting/witness personnel.'),
            ('Separate accounts', ('separate', 'interview', 'statement', 'ask'), 'Keep accounts independent enough to evaluate reliability.'),
            ('Property preservation', ('merchandise', 'property', 'evidence', 'preserve', 'photo'), 'Preserve the recovered property and its condition.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Firsthand observation', ('observed', 'saw', 'loss prevention', 'witness', 'firsthand'), 'Establish exactly what the witness personally observed.'),
            ('Video / evidence', ('video', 'camera', 'evidence', 'review'), 'Review or preserve available video before deciding the case.'),
            ('Value / property details', ('value', 'price', 'merchandise', 'property', 'receipt'), 'Document the item and reliable value information.'),
            ('Subject account', ('subject', 'ask', 'interview', 'statement', 'account'), 'Obtain the subject’s account before drawing a conclusion.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Intent facts', ('intent', 'conceal', 'bag', 'actions', 'facts'), 'Identify facts bearing on intent instead of presuming it.'),
            ('Legal / policy basis', ('probable cause', 'elements', 'authority', 'policy', 'procedure', 'facts'), 'Articulate the factual and legal/policy basis for any enforcement action.'),
            ('Required notifications / screening', ('cid', 'screen', 'supervisor', 'notify', 'notification'), 'Address required supervisory or investigative screening.'),
            ('Evidence review', ('video', 'statement', 'evidence', 'review'), 'Resolve material conflicts with available evidence.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Fact-based disposition', ('based on', 'facts', 'citation', 'arrest', 'release', 'warning', 'disposition'), 'State the final action and connect it to established facts.'),
            ('Written statements', ('statement', 'written', 'loss prevention', 'witness'), 'Account for required written statements.'),
            ('Evidence / property', ('evidence', 'property', 'video', 'merchandise'), 'State how evidence and recovered property are handled.'),
            ('Report / screening', ('report', 'ccn', 'document', 'cid', 'screen'), 'Complete the required report and screening/notification workflow.'),
        ]},
    ],
    'S005': [
        {'minimum': 3, 'criteria': [
            ('Radio traffic', ('radio', 'dispatch', 'location', 'vehicle', 'plate', 'traffic stop'), 'Transmit the stop/location and vehicle information.'),
            ('Safe stop location / positioning', ('safe location', 'position', 'offset', 'approach', 'traffic', 'visibility'), 'Address stop location and patrol-vehicle/officer positioning.'),
            ('Observation / legal basis', ('violation', 'observed', 'reason for stop', 'basis', 'traffic offense'), 'State the observed basis for the stop.'),
            ('Occupant awareness', ('occupant', 'hands', 'movement', 'vehicle', 'observe'), 'Describe what you watch for before and during the approach.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Hands / movement control', ('hands', 'console', 'movement', 'keep', 'visible'), 'Address the repeated reaching behavior with clear, lawful directions.'),
            ('Position / reactionary safety', ('position', 'distance', 'cover', 'passenger side', 'safety'), 'Maintain a position that supports observation and reaction.'),
            ('Professional communication', ('calm', 'professional', 'explain', 'instruction', 'de-escalat'), 'Use clear commands and professional communication despite argument.'),
            ('Documents / checks', ('license', 'registration', 'records', 'check', 'dispatch'), 'Obtain required documents and conduct appropriate checks.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Clear direction / control', ('direction', 'command', 'hands', 'comply', 'instruction'), 'Give clear directions and reassess compliance before escalating.'),
            ('Threat / behavior assessment', ('threat', 'behavior', 'movement', 'risk', 'assess', 'compliance'), 'Tie your next action to the driver’s behavior and observable risk.'),
            ('Legal basis for escalation', ('reasonable suspicion', 'probable cause', 'authority', 'facts', 'basis', 'lawful'), 'Articulate the facts/authority supporting any detention, search, or force decision.'),
            ('Backup / coordination', ('backup', 'dispatch', 'additional unit', 'notify'), 'Consider additional resources when behavior raises safety concerns.'),
        ]},
        {'minimum': 3, 'criteria': [
            ('Enforcement decision', ('warning', 'citation', 'ticket', 'enforcement', 'disposition'), 'State the traffic enforcement decision based on the observed violation.'),
            ('Explain outcome', ('explain', 'professional', 'instructions', 'court', 'safe'), 'Explain the disposition and safe conclusion of the stop.'),
            ('Radio / clear status', ('dispatch', 'radio', 'clear', 'status'), 'Close the stop with appropriate status communication.'),
            ('Documentation', ('document', 'report', 'citation', 'notes'), 'Document the stop and any unusual safety or conduct issues as required.'),
        ]},
    ],
    'S006': [
        {'minimum': 2, 'criteria': [
            ('Immediate medical priority', ('ems', 'medical', 'patient', 'aid', 'condition', 'conscious'), 'Prioritize patient condition and EMS access.'),
            ('Scene safety', ('safety', 'hazard', 'scene', 'secure'), 'Check for hazards and keep the scene workable for medical personnel.'),
            ('Initial witness control', ('witness', 'coworker', 'separate', 'identify'), 'Identify who has information and avoid blending conflicting accounts.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Do not interfere with care', ('ems', 'medical care', 'patient care', 'do not interfere', 'space'), 'Gather facts without delaying or interfering with treatment.'),
            ('Separate / identify witnesses', ('separate', 'witness', 'coworker', 'identify'), 'Separate and identify witnesses when practical.'),
            ('Source reliability', ('actually saw', 'firsthand', 'witnessed', 'reliable', 'clarify'), 'Determine who personally observed the beginning of the event.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Full-event witness', ('full event', 'witness', 'saw', 'firsthand', 'beginning'), 'Locate the person who observed the complete sequence.'),
            ('Patient account / condition', ('patient', 'ask', 'statement', 'condition', 'confused'), 'Document the patient’s account/condition to the extent appropriate.'),
            ('Contradiction resolution', ('conflict', 'clarify', 'compare', 'corroborat', 'accounts'), 'Resolve or clearly document conflicting accounts.'),
        ]},
        {'minimum': 2, 'criteria': [
            ('Medical disposition', ('ems', 'transport', 'medical', 'patient', 'disposition'), 'Document the medical disposition without inventing diagnosis.'),
            ('Witness / fact documentation', ('witness', 'statement', 'document', 'report', 'blotter'), 'Document who observed what and distinguish conflicting statements.'),
            ('Final status / notifications', ('dispatch', 'clear', 'notify', 'supervisor', 'status'), 'Address final status and any required notification.'),
        ]},
    ],
}

LEGAL_BASIS_TERMS = (
    'probable cause', 'reasonable suspicion', 'authority', 'lawful', 'facts', 'based on',
    'consent', 'warrant', 'incident to arrest', 'policy', 'procedure', 'elements',
)
FORCE_BASIS_TERMS = ('threat', 'resist', 'assault', 'weapon', 'necessary', 'reasonable', 'proportionate', 'immediate')
SEARCH_BASIS_TERMS = ('consent', 'probable cause', 'warrant', 'incident to arrest', 'authorized', 'authority', 'policy')
UNSUPPORTED_CERTAINTY = ('obviously guilty', 'definitely guilty', 'definitely stole', 'must have stolen', 'must have done it')


def _normalize(value):
    return ' '.join(str(value or '').split()).strip()


def _valid_scenario(value):
    return value if value in SCENARIOS else 'S001'


def _new_state(scenario_id):
    return {
        'scenario_id': scenario_id,
        'turn': 0,
        'complete': False,
        # Raw trainee responses are intentionally not retained in the session.
        'area_counts': {label: 0 for label, _terms in PRACTICE_AREAS},
        'stage_attempts': {},
        'total_attempts': 0,
        'revision_count': 0,
        'hint_count': 0,
        'intervention_count': 0,
        'last_feedback': None,
    }


def _state_for(scenario_id):
    state = session.get(SESSION_KEY)
    if not isinstance(state, dict) or state.get('scenario_id') != scenario_id:
        state = _new_state(scenario_id)
        session[SESSION_KEY] = state
        session.modified = True
    return state


def _apply_action_cues(state, response_text):
    low = _normalize(response_text).lower()
    counts = dict(state.get('area_counts') or {})
    for label, terms in PRACTICE_AREAS:
        hits = sum(1 for term in terms if term in low)
        if hits:
            counts[label] = min(9, int(counts.get(label, 0)) + min(3, hits))
    state['area_counts'] = counts


def _critical_issues(response_text):
    low = _normalize(response_text).lower()
    issues = []
    words = re.findall(r"[a-z0-9']+", low)
    if len(words) < 8 or len(low) < 45:
        issues.append('The response is too brief to demonstrate a safe, reasoned decision. Explain what you would do and why.')

    enforcement_terms = ('arrest', 'take him to jail', 'take them to jail', 'detain')
    if any(term in low for term in enforcement_terms) and not any(term in low for term in LEGAL_BASIS_TERMS):
        issues.append('Enforcement action was stated without articulating the facts or legal/policy basis that would authorize it.')

    if re.search(r'\bsearch(?:ed|ing)?\b', low) and not any(term in low for term in SEARCH_BASIS_TERMS):
        issues.append('A search was proposed without identifying a lawful basis such as consent, warrant, probable cause, or another recognized authority.')

    force_terms = ('shoot', 'tase', 'taser', 'pepper spray', 'oc spray', 'strike', 'use force', 'go hands on', 'draw my weapon', 'point my weapon')
    if any(term in low for term in force_terms) and not any(term in low for term in FORCE_BASIS_TERMS):
        issues.append('Force or weapon use was proposed without facts showing a threat, resistance, necessity, or proportional response.')

    if any(term in low for term in UNSUPPORTED_CERTAINTY):
        issues.append('The response reaches a guilt/intent conclusion that has not been established by the facts provided.')

    if any(term in low for term in ('ignore dispatch', 'skip the report', 'no need to document', 'do not document')):
        issues.append('The response proposes skipping a required accountability or documentation step.')

    return issues


def _evaluate_action(scenario_id, turn, response_text):
    rubric = SCENARIO_RUBRICS.get(scenario_id, [])[turn]
    low = _normalize(response_text).lower()
    matched = []
    missing = []
    for label, terms, hint in rubric['criteria']:
        row = {'label': label, 'hint': hint}
        if any(term in low for term in terms):
            matched.append(row)
        else:
            missing.append(row)

    issues = _critical_issues(response_text)
    accepted = len(matched) >= int(rubric['minimum']) and not issues
    if accepted:
        status = 'accepted'
        headline = 'Decision accepted — continue the scenario'
        consequence = 'Your decision met the minimum training standard for this stage. The next facts are now released.'
    elif issues:
        status = 'intervention'
        headline = 'FTO intervention — decision cannot continue as written'
        consequence = 'The scenario is paused at this decision point. Correct the safety, legal, or articulation issue before new facts are released.'
    else:
        status = 'revise'
        headline = 'Decision held — revise your response'
        consequence = 'The scenario remains at the same decision point. Add the missing operational concepts before continuing.'

    return {
        'stage': turn,
        'status': status,
        'accepted': accepted,
        'headline': headline,
        'consequence': consequence,
        'strengths': [item['label'] for item in matched],
        'gaps': [item['label'] for item in missing],
        'hints': [item['hint'] for item in missing[:3]],
        'issues': issues,
        'met_count': len(matched),
        'required_count': int(rubric['minimum']),
        'criteria_count': len(rubric['criteria']),
    }


def _hint_feedback(scenario_id, turn, previous_feedback=None):
    rubric = SCENARIO_RUBRICS.get(scenario_id, [])[turn]
    missing_labels = set((previous_feedback or {}).get('gaps') or [])
    rows = []
    for label, _terms, hint in rubric['criteria']:
        if not missing_labels or label in missing_labels:
            rows.append({'label': label, 'hint': hint})
    rows = rows[:3]
    return {
        'stage': turn,
        'status': 'hint',
        'accepted': False,
        'headline': 'Coaching hint — scenario not advanced',
        'consequence': 'Use the prompts below to strengthen your own decision. The answer is not being supplied for you.',
        'strengths': [],
        'gaps': [row['label'] for row in rows],
        'hints': [row['hint'] for row in rows],
        'issues': [],
        'met_count': 0,
        'required_count': int(rubric['minimum']),
        'criteria_count': len(rubric['criteria']),
    }


def _coaching_summary(state):
    rows = []
    for label, _terms in PRACTICE_AREAS:
        count = int((state.get('area_counts') or {}).get(label, 0))
        if count >= 4:
            status = 'Demonstrated repeatedly'
            level = 'good'
        elif count >= 1:
            status = 'Some cues demonstrated'
            level = 'partial'
        else:
            status = 'Not yet demonstrated in accepted decisions'
            level = 'needs-work'
        rows.append({'area': label, 'status': status, 'level': level})

    revisions = int(state.get('revision_count', 0))
    interventions = int(state.get('intervention_count', 0))
    hints = int(state.get('hint_count', 0))
    if interventions >= 2 or revisions >= 4:
        practice_outcome = 'Completed after significant coaching / remediation'
    elif interventions or revisions >= 2 or hints >= 2:
        practice_outcome = 'Completed with coaching'
    else:
        practice_outcome = 'Strong practice run'

    return {
        'areas': rows,
        'discussion': [row['area'] for row in rows if row['level'] == 'needs-work'][:5],
        'practice_outcome': practice_outcome,
        'attempts': int(state.get('total_attempts', 0)),
        'revisions': revisions,
        'hints': hints,
        'interventions': interventions,
        'notice': (
            'These are text-based practice cues only, not SEG/DOR ratings. '
            'The practice outcome describes this training run only. The assigned FTO must evaluate actual behavior against the approved FTP standards.'
        ),
    }


@bp.route('/', methods=['GET', 'POST'])
@login_required
def lab():
    requested_id = _valid_scenario(request.values.get('scenario_id') or 'S001')
    state = _state_for(requested_id)
    scenario = SCENARIOS[state['scenario_id']]
    stages = scenario['stages']

    if request.method == 'POST':
        action = _normalize(request.form.get('action')).lower()

        if action == 'reset':
            session[SESSION_KEY] = _new_state(requested_id)
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=requested_id))

        if action == 'switch':
            session[SESSION_KEY] = _new_state(requested_id)
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=requested_id))

        turn = int(state.get('turn', 0))

        if action == 'finish':
            if turn < len(stages):
                flash('Complete every scenario decision before finishing the coaching review.', 'warning')
            else:
                state['complete'] = True
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

        if action == 'hint':
            if state.get('complete') or turn >= len(stages):
                flash('No additional hint is available at this point.', 'info')
            else:
                state['hint_count'] = int(state.get('hint_count', 0)) + 1
                state['last_feedback'] = _hint_feedback(state['scenario_id'], turn, state.get('last_feedback'))
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

        if action == 'act':
            if state.get('complete'):
                flash('This scenario is complete. Reset it or select another scenario to continue.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

            if turn >= len(stages):
                flash('All scenario stages are complete. Finish the scenario for the coaching review.', 'info')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

            response_text = _normalize(request.form.get('response_text'))[:2500]
            if not response_text:
                flash('Describe what you would do before continuing the scenario.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

            attempts = dict(state.get('stage_attempts') or {})
            stage_key = str(turn)
            attempts[stage_key] = int(attempts.get(stage_key, 0)) + 1
            state['stage_attempts'] = attempts
            state['total_attempts'] = int(state.get('total_attempts', 0)) + 1

            feedback = _evaluate_action(state['scenario_id'], turn, response_text)
            feedback['attempt'] = attempts[stage_key]
            state['last_feedback'] = feedback

            if feedback['accepted']:
                _apply_action_cues(state, response_text)
                state['turn'] = turn + 1
            else:
                state['revision_count'] = int(state.get('revision_count', 0)) + 1
                if feedback['status'] == 'intervention':
                    state['intervention_count'] = int(state.get('intervention_count', 0)) + 1

            session[SESSION_KEY] = state
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

    turn = int(state.get('turn', 0))
    latest_reveal = stages[turn - 1]['reveal'] if turn > 0 else None
    current_stage = stages[turn] if turn < len(stages) else None
    ready_to_finish = turn >= len(stages)
    result = _coaching_summary(state) if state.get('complete') else None
    last_feedback = state.get('last_feedback')

    return render_template(
        'scenario_lab.html',
        user=current_user,
        scenarios=SCENARIOS,
        scenario_id=state['scenario_id'],
        scenario=scenario,
        turn=turn,
        total_turns=len(stages),
        latest_reveal=latest_reveal,
        current_stage=current_stage,
        ready_to_finish=ready_to_finish,
        complete=bool(state.get('complete')),
        result=result,
        last_feedback=last_feedback,
        stage_attempt=int((state.get('stage_attempts') or {}).get(str(turn), 0)),
        total_attempts=int(state.get('total_attempts', 0)),
        revision_count=int(state.get('revision_count', 0)),
        intervention_count=int(state.get('intervention_count', 0)),
        hint_count=int(state.get('hint_count', 0)),
        practice_areas=[label for label, _terms in PRACTICE_AREAS],
    )
