from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from .sentinel import SCENARIOS, _evaluate_fto, _normalize

bp = Blueprint('scenario_lab', __name__, url_prefix='/scenario-lab')
SESSION_KEY = 'sentinel_scenario_lab'
MAX_TURNS = 12

SCRIPTED_FACTS = {
    'S001': [
        {'id': 'staff', 'triggers': ['staff', 'complainant', 'witness', 'employee', 'interview', 'ask'], 'text': 'A staff member states the individual was told twice to leave after yelling at employees. The staff member did not observe a weapon or hear a specific threat.'},
        {'id': 'subject', 'triggers': ['subject', 'individual', 'contact', 'speak', 'identify'], 'text': 'The individual says he is waiting for a ride and does not believe staff can make him leave. He is argumentative, keeps his hands visible, and does not attempt to leave.'},
        {'id': 'manager', 'triggers': ['manager', 'authority', 'trespass', 'leave', 'property representative'], 'text': 'The facility manager confirms the individual was clearly directed to leave the facility and surrounding controlled area and is still refusing.'},
        {'id': 'backup', 'triggers': ['backup', 'cover', 'additional unit', 'second unit'], 'text': 'A second patrol unit arrives and is available to assist.'},
    ],
    'S002': [
        {'id': 'gate', 'triggers': ['gate', 'guard', 'staff', 'interview', 'ask'], 'text': 'Gate personnel state the driver presented an expired credential and could not produce another document authorizing installation access.'},
        {'id': 'driver', 'triggers': ['driver', 'contact', 'speak', 'identify', 'license'], 'text': 'The driver provides a valid state driver license, says he previously had base access, and becomes verbally frustrated when told entry may be denied.'},
        {'id': 'vehicle', 'triggers': ['vehicle', 'registration', 'plate', 'records', 'check'], 'text': 'The vehicle registration matches the driver. No additional scripted alert is returned from the training records check.'},
        {'id': 'supervisor', 'triggers': ['supervisor', 'access control', 'sponsor', 'verify'], 'text': 'The listed sponsor cannot immediately confirm a current access requirement for the driver.'},
    ],
    'S003': [
        {'id': 'witness', 'triggers': ['witness', 'complainant', 'staff', 'interview', 'ask'], 'text': 'A witness states a contractor pickup backed into the light pole while maneuvering in the parking area. The witness describes the impact as low speed.'},
        {'id': 'driver', 'triggers': ['driver', 'contractor', 'contact', 'speak', 'identify'], 'text': 'The contractor driver acknowledges the vehicle contacted the pole and says he did not see it while backing.'},
        {'id': 'damage', 'triggers': ['damage', 'inspect', 'property', 'pole', 'photo', 'photograph'], 'text': 'The light pole is bent near its base. The vehicle has minor rear-bumper scuffing. No injury is reported in the scripted scenario.'},
        {'id': 'documentation', 'triggers': ['statement', 'evidence', 'report', 'ccn', 'notify'], 'text': 'Facility personnel can provide the property point of contact and request documentation of the damage for follow-up.'},
    ],
    'S004': [
        {'id': 'staff', 'triggers': ['staff', 'employee', 'complainant', 'interview', 'ask'], 'text': 'Store staff state they observed the subject conceal merchandise and pass the last point of sale without paying.'},
        {'id': 'property', 'triggers': ['property', 'merchandise', 'item', 'value', 'recover'], 'text': 'The recovered merchandise is intact and staff provide a documented retail value for the training scenario.'},
        {'id': 'video', 'triggers': ['video', 'camera', 'cctv', 'evidence', 'review'], 'text': 'Store video is available and appears to show the subject selecting, concealing, and carrying the merchandise past the registers.'},
        {'id': 'subject', 'triggers': ['subject', 'suspect', 'contact', 'interview', 'statement'], 'text': 'The subject identifies himself and says he intended to pay but forgot after receiving a phone call. He does not provide additional scripted facts.'},
    ],
    'S005': [
        {'id': 'initial', 'triggers': ['radio', 'dispatch', 'plate', 'location', 'stop'], 'text': 'Dispatch acknowledges the stop location and vehicle description. No additional scripted alert is returned.'},
        {'id': 'driver', 'triggers': ['driver', 'contact', 'license', 'registration', 'insurance'], 'text': 'The driver provides the requested documents but repeatedly asks why he was stopped and speaks in an increasingly loud tone.'},
        {'id': 'safety', 'triggers': ['hands', 'weapon', 'safety', 'position', 'observe'], 'text': 'The driver keeps both hands visible. No weapon or furtive movement is observed in the scripted scenario.'},
        {'id': 'backup', 'triggers': ['backup', 'cover', 'second unit', 'additional unit'], 'text': 'A second unit arrives and takes a cover position.'},
    ],
    'S006': [
        {'id': 'patient', 'triggers': ['patient', 'contact', 'medical', 'assessment', 'speak'], 'text': 'The patient is conscious but appears weak and says he became dizzy shortly before sitting down.'},
        {'id': 'witness1', 'triggers': ['witness', 'coworker', 'interview', 'ask', 'separate'], 'text': 'One coworker says the patient briefly stumbled but did not fall or strike his head.'},
        {'id': 'witness2', 'triggers': ['second witness', 'another coworker', 'conflicting', 'separate'], 'text': 'A second coworker believes the patient may have lowered himself to one knee but did not see a head strike.'},
        {'id': 'ems', 'triggers': ['ems', 'ambulance', 'medical personnel', 'turn over'], 'text': 'EMS arrives, assumes patient care, and begins its medical assessment.'},
    ],
}


def _new_state(scenario_id):
    return {'scenario_id': scenario_id, 'turns': [], 'revealed': []}


def _state_for(scenario_id):
    state = session.get(SESSION_KEY)
    if not isinstance(state, dict) or state.get('scenario_id') != scenario_id:
        state = _new_state(scenario_id)
        session[SESSION_KEY] = state
    return state


def _reveal_for_action(scenario_id, action_text, already_revealed):
    low = _normalize(action_text).lower()
    newly_revealed = []
    for fact in SCRIPTED_FACTS.get(scenario_id, []):
        if fact['id'] in already_revealed:
            continue
        if any(trigger in low for trigger in fact['triggers']):
            newly_revealed.append(fact)
        if len(newly_revealed) >= 2:
            break
    if newly_revealed:
        return newly_revealed, ' '.join(fact['text'] for fact in newly_revealed)
    return [], 'No additional scripted facts are revealed from that action. Continue using only the facts currently known.'


def _known_facts(scenario_id, revealed_ids):
    return [fact for fact in SCRIPTED_FACTS.get(scenario_id, []) if fact['id'] in revealed_ids]


@bp.route('/', methods=['GET', 'POST'])
@login_required
def lab():
    scenario_id = request.args.get('scenario_id') or request.form.get('scenario_id') or 'S001'
    if scenario_id not in SCENARIOS:
        scenario_id = 'S001'
    scenario = SCENARIOS[scenario_id]
    state = _state_for(scenario_id)
    result = None

    if request.method == 'POST':
        action = _normalize(request.form.get('action')).lower()
        if action == 'reset':
            session[SESSION_KEY] = _new_state(scenario_id)
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        response_text = (request.form.get('response_text') or '').strip()
        if response_text:
            if len(state['turns']) >= MAX_TURNS:
                flash('This practice scenario has reached the 12-turn limit. Finish and evaluate, or reset it.', 'warning')
            else:
                facts, scene_update = _reveal_for_action(scenario_id, response_text, set(state.get('revealed', [])))
                for fact in facts:
                    if fact['id'] not in state['revealed']:
                        state['revealed'].append(fact['id'])
                state['turns'].append({
                    'number': len(state['turns']) + 1,
                    'trainee': response_text[:2000],
                    'update': scene_update,
                })
                session[SESSION_KEY] = state
                session.modified = True
        elif action != 'finish':
            flash('Enter what you would do next before submitting the action.', 'warning')

        if action == 'finish':
            if not state['turns']:
                flash('Complete at least one scenario action before finishing.', 'warning')
            else:
                combined = '\n'.join(turn['trainee'] for turn in state['turns'])
                result = _evaluate_fto(combined)
                result['turn_count'] = len(state['turns'])
                result['revealed_count'] = len(state['revealed'])

    return render_template(
        'scenario_lab.html',
        user=current_user,
        scenarios=SCENARIOS,
        scenario_id=scenario_id,
        scenario=scenario,
        state=state,
        known_facts=_known_facts(scenario_id, state.get('revealed', [])),
        result=result,
        max_turns=MAX_TURNS,
    )
