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


def _normalize(value):
    return ' '.join(str(value or '').split()).strip()


def _valid_scenario(value):
    return value if value in SCENARIOS else 'S001'


def _new_state(scenario_id):
    return {
        'scenario_id': scenario_id,
        'turn': 0,
        'complete': False,
        # Only derived cue counts are retained in the signed session cookie.
        # Raw trainee responses are not persisted by Scenario Lab.
        'area_counts': {label: 0 for label, _terms in PRACTICE_AREAS},
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
            status = 'Not yet demonstrated in written actions'
            level = 'needs-work'
        rows.append({'area': label, 'status': status, 'level': level})
    return {
        'areas': rows,
        'discussion': [row['area'] for row in rows if row['level'] == 'needs-work'][:5],
        'notice': (
            'These are text-based practice cues only, not SEG/DOR ratings. '
            'The assigned FTO must evaluate actual behavior against the approved FTP standards.'
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

        if action == 'finish':
            if int(state.get('turn', 0)) < 1:
                flash('Complete at least one scenario decision before finishing.', 'warning')
            else:
                state['complete'] = True
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

        if action == 'act':
            if state.get('complete'):
                flash('This scenario is complete. Reset it or select another scenario to continue.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

            turn = int(state.get('turn', 0))
            if turn >= len(stages):
                flash('All scenario stages are complete. Finish the scenario for the coaching review.', 'info')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

            response_text = _normalize(request.form.get('response_text'))
            if not response_text:
                flash('Describe what you would do before continuing the scenario.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

            _apply_action_cues(state, response_text[:2500])
            state['turn'] = turn + 1
            session[SESSION_KEY] = state
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state['scenario_id']))

    turn = int(state.get('turn', 0))
    latest_reveal = stages[turn - 1]['reveal'] if turn > 0 else None
    current_stage = stages[turn] if turn < len(stages) else None
    ready_to_finish = turn >= len(stages)
    result = _coaching_summary(state) if state.get('complete') else None

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
        practice_areas=[label for label, _terms in PRACTICE_AREAS],
    )
