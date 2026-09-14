import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..services.ai_client import (
    ask_openai_with_system,
    configured_openai_api_key,
    is_ai_unavailable_message,
)
from .scenario_lab import (
    PRACTICE_AREAS,
    SCENARIOS,
    SCENARIO_RUBRICS,
    _apply_action_cues,
    _coaching_summary,
    _evaluate_action,
    _normalize,
    _valid_scenario,
)

bp = Blueprint('scenario_lab', __name__, url_prefix='/scenario-lab')
SESSION_KEY = 'sentinel_scenario_lab_v2'

# Scenario Lab is synthetic practice. It never creates an official DOR score or
# makes a real criminal/legal finding. Consequences below are exercise outcomes.

SCENARIO_META = {
    'S001': {
        'scene': 'Facility entrance / interior disturbance',
        'visual': ['Staff member outside', 'Subject reported inside', 'Public-facing facility', 'No weapon reported'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [
                ('weapon|armed|gun|knife', 'No weapon has been reported.'),
                ('backup|unit|other officer', 'No additional unit has been assigned yet. Advise if you need one.'),
                ('location|building|where', 'The call is at Building 7130.'),
            ]},
            {'id': 'staff', 'name': 'Staff Member', 'role': 'Reporting Party', 'from': 0, 'facts': [
                ('what happened|why|problem|call', 'He became disruptive inside and we told him to leave more than once.'),
                ('weapon|armed|threat', 'I have not seen a weapon. He is yelling and arguing.'),
                ('leave|told|revoked|invited', 'He had been invited earlier, but we told him the invitation was over after the disturbance started.'),
            ]},
            {'id': 'subject', 'name': 'Subject', 'role': 'Subject', 'from': 1, 'facts': [
                ('why|what happened|side|story', 'I was invited here. They got mad when I argued with them, and now they are trying to throw me out.'),
                ('leave|told|order', 'They told me to leave, but I did not think they could change their mind after inviting me.'),
                ('weapon|armed', 'I do not have a weapon.'),
            ]},
            {'id': 'employee2', 'name': 'Second Employee', 'role': 'Witness', 'from': 2, 'facts': [
                ('see|hear|witness|leave', 'I personally heard staff tell him to leave.'),
                ('video|camera', 'The facility cameras should have recorded the area.'),
            ]},
        ],
    },
    'S002': {
        'scene': 'Main Gate inspection area',
        'visual': ['Vehicle stopped in inspection area', 'Gate personnel present', 'Driver has state license', 'No valid installation credential'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [
                ('status|location|gate', 'Main Gate has the vehicle stopped in the inspection area.'),
                ('wanted|records|check', 'No records check has been requested yet.'),
            ]},
            {'id': 'gate', 'name': 'Gate Officer', 'role': 'Gate Personnel', 'from': 0, 'facts': [
                ('credential|access|why stopped', 'The driver cannot produce a valid installation access credential.'),
                ('behavior|argument|threat', 'He is argumentative, but no threat or weapon has been reported.'),
            ]},
            {'id': 'driver', 'name': 'Driver', 'role': 'Driver', 'from': 0, 'facts': [
                ('why|purpose|meeting|contractor', 'I am here to meet a contractor. I thought they already knew I was coming.'),
                ('license|id|identity', 'I have my state driver license.'),
                ('credential|pass|access', 'I do not have an installation credential.'),
            ]},
            {'id': 'contractor', 'name': 'Contractor', 'role': 'Phone Contact', 'from': 2, 'facts': [
                ('meeting|expect|confirm', 'Yes, I am expecting the driver for a meeting.'),
                ('preclear|pre-clear|access|sponsor', 'He was not pre-cleared for installation access.'),
            ]},
        ],
    },
    'S003': {
        'scene': 'Facility parking area / damaged government property',
        'visual': ['Damaged light pole', 'White contractor pickup nearby', 'No injuries reported', 'Scene still available to document'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [
                ('injury|injured|medical', 'No injuries have been reported.'),
                ('vehicle|truck', 'The reported vehicle is a contractor pickup near the facility.'),
            ]},
            {'id': 'reporting', 'name': 'Facility Employee', 'role': 'Reporting Party', 'from': 0, 'facts': [
                ('see|witness|collision|hit', 'I did not see the collision. Another worker told me the truck hit the pole.'),
                ('when|time', 'I learned about it after the collision had already happened.'),
            ]},
            {'id': 'witness', 'name': 'Worker', 'role': 'Witness', 'from': 2, 'facts': [
                ('see|witness|what happened', 'I saw the truck back into the pole.'),
                ('driver|who', 'The driver is still available nearby.'),
            ]},
            {'id': 'driver', 'name': 'Driver', 'role': 'Driver', 'from': 2, 'facts': [
                ('hit|contact|know|realize', 'I did not realize I made contact with the pole.'),
                ('intent|purpose|damage', 'I did not intentionally hit it.'),
            ]},
        ],
    },
    'S004': {
        'scene': 'Retail / exchange facility office',
        'visual': ['Subject waiting with staff', 'Recovered merchandise on table', 'Loss-prevention witness', 'Video may be available'],
        'cast': [
            {'id': 'lp', 'name': 'Loss Prevention', 'role': 'Witness', 'from': 0, 'facts': [
                ('see|observe|what happened|conceal', 'I observed the subject place the item into a bag.'),
                ('statement|written', 'I can provide a written statement.'),
                ('video|camera', 'There is video of the incident.'),
                ('value|price', 'The merchandise has a documented retail price.'),
            ]},
            {'id': 'subject', 'name': 'Subject', 'role': 'Subject', 'from': 1, 'facts': [
                ('why|intent|steal|bag', 'I was carrying other things and put the item in the bag. I was not trying to steal it.'),
                ('leave|exit', 'The merchandise was recovered before I left the facility.'),
            ]},
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [
                ('backup|unit', 'No additional unit has been requested.'),
                ('records|wanted|check', 'No records check has been requested yet.'),
            ]},
        ],
    },
    'S005': {
        'scene': 'Roadside traffic stop',
        'visual': ['Stopped vehicle ahead', 'Driver remains seated', 'Traffic exposure present', 'Driver becoming argumentative'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [
                ('backup|unit', 'No backup unit has been requested.'),
                ('records|wanted|license|plate', 'A records check can be run when you provide the information.'),
            ]},
            {'id': 'driver', 'name': 'Driver', 'role': 'Driver', 'from': 1, 'facts': [
                ('why|stop|reason', 'Why are you stopping me? I do not think I did anything wrong.'),
                ('license|registration', 'Here is my license and registration.'),
                ('console|reach|hands', 'I was reaching for my paperwork.'),
                ('weapon|gun|armed', 'I am not telling you I have a weapon. You have not seen one.'),
            ]},
        ],
    },
    'S006': {
        'scene': 'Workplace medical assist',
        'visual': ['Patient conscious but confused', 'EMS en route', 'Coworkers disagree about what happened', 'No known assault'],
        'cast': [
            {'id': 'dispatch', 'name': 'Dispatch', 'role': 'Radio', 'from': 0, 'facts': [
                ('ems|medical', 'EMS is en route.'),
                ('assault|fight|weapon', 'No assault or weapon has been reported.'),
            ]},
            {'id': 'coworker1', 'name': 'Coworker One', 'role': 'Witness', 'from': 0, 'facts': [
                ('see|what happened|fall', 'I saw him on the floor, but I did not actually see how it started.'),
                ('hit|assault', 'I did not see anyone strike him.'),
            ]},
            {'id': 'coworker2', 'name': 'Coworker Two', 'role': 'Witness', 'from': 0, 'facts': [
                ('see|what happened|sit', 'I thought he sat down before becoming ill, but I did not see the whole event.'),
            ]},
            {'id': 'patient', 'name': 'Patient', 'role': 'Patient', 'from': 0, 'facts': [
                ('what happened|feel|condition', 'I feel dizzy and I am having trouble remembering exactly what happened.'),
                ('hit|assault', 'No one hit me.'),
            ]},
            {'id': 'fullwitness', 'name': 'Full-Event Witness', 'role': 'Witness', 'from': 2, 'facts': [
                ('see|what happened|full|beginning', 'I saw the whole thing. He became dizzy, sat down, and then slid to the floor.'),
            ]},
        ],
    },
}

NEXT_SCENARIO = {'S001': 'S002', 'S002': 'S003', 'S003': 'S004', 'S004': 'S005', 'S005': 'S006', 'S006': 'S001'}


def _new_state(scenario_id):
    return {
        'scenario_id': scenario_id,
        'turn': 0,
        'complete': False,
        'terminated': False,
        'terminal_outcome': None,
        'fto_alert': False,
        'area_counts': {label: 0 for label, _terms in PRACTICE_AREAS},
        'stage_attempts': {},
        'stage_interactions': {},
        'stage_hints': {},
        'total_attempts': 0,
        'revision_count': 0,
        'intervention_count': 0,
        'hint_count': 0,
        'actor_interactions': 0,
        'last_feedback': None,
        'dialogue': [],
        'consequences': [],
    }


def _state_for(scenario_id):
    state = session.get(SESSION_KEY)
    if not isinstance(state, dict) or state.get('scenario_id') != scenario_id:
        state = _new_state(scenario_id)
        session[SESSION_KEY] = state
        session.modified = True
        return state

    # Backward-compatible upgrade for sessions created by the previous lab.
    defaults = _new_state(scenario_id)
    for key, value in defaults.items():
        if key not in state:
            state[key] = value
    session[SESSION_KEY] = state
    session.modified = True
    return state


def _available_cast(scenario_id, turn):
    rows = []
    for actor in SCENARIO_META.get(scenario_id, {}).get('cast', []):
        if int(actor.get('from', 0)) <= turn:
            rows.append(actor)
    return rows


def _actor_for(scenario_id, turn, actor_id):
    for actor in _available_cast(scenario_id, turn):
        if actor['id'] == actor_id:
            return actor
    return None


def _released_facts(scenario_id, turn):
    scenario = SCENARIOS[scenario_id]
    facts = [f"Dispatch: {scenario['dispatch']}"]
    for index in range(min(turn, len(scenario['stages']))):
        facts.append(scenario['stages'][index]['reveal'])
    return facts


def _fallback_actor_reply(actor, question):
    low = _normalize(question).lower()
    for pattern, reply in actor.get('facts', []):
        if re.search(pattern, low):
            return reply
    role = actor.get('role', 'person')
    if role == 'Radio':
        return 'Dispatch copies. Be more specific about what information or resource you are requesting.'
    if role == 'Subject':
        return 'What exactly are you asking me?'
    if role == 'Patient':
        return 'I am not sure. I am having trouble remembering everything clearly.'
    return 'I can answer what I personally know, but I need a more specific question.'


def _roleplay_reply(scenario_id, turn, actor, question):
    fallback = _fallback_actor_reply(actor, question)
    api_key = configured_openai_api_key()
    if not api_key:
        return fallback, 'scripted'

    actor_facts = '\n'.join(f'- {reply}' for _pattern, reply in actor.get('facts', [])) or '- No additional facts.'
    released = '\n'.join(f'- {fact}' for fact in _released_facts(scenario_id, turn))
    system_prompt = f"""You are role-playing one person in a synthetic police field-training scenario.
Character: {actor['name']} ({actor['role']}).
Scenario: {SCENARIOS[scenario_id]['title']}.

Facts already available in the exercise:
{released}

Facts this character is allowed to know or state:
{actor_facts}

Rules:
- Stay in character and answer only the trainee officer's question.
- Use 1-3 short natural sentences.
- Never coach the officer, never say what the officer should do, and never reveal evaluation criteria.
- Never invent a weapon, crime, injury, confession, probable cause, policy requirement, or future fact.
- Never reveal facts from a later stage.
- If the question asks for something this character would not know, say you do not know.
- If the question is vague, ask the officer to be more specific.
- Do not praise or grade the trainee.
"""
    answer = ask_openai_with_system(question, system_prompt, api_key)
    if is_ai_unavailable_message(answer) or not _normalize(answer):
        return fallback, 'scripted'
    return _normalize(answer)[:700], 'ai'


def _append_dialogue(state, actor, answer, mode):
    rows = list(state.get('dialogue') or [])
    rows.append({
        'actor': actor['name'],
        'role': actor['role'],
        'answer': _normalize(answer)[:700],
        'mode': mode,
        'stage': int(state.get('turn', 0)),
    })
    state['dialogue'] = rows[-10:]


def _negative_phrase(low, term):
    return bool(re.search(rf"\b(?:do not|don't|would not|wouldn't|not going to|will not)\s+(?:\w+\s+){{0,2}}{term}\b", low))


def _catastrophic_outcome(scenario_id, turn, response_text):
    low = _normalize(response_text).lower()

    deadly_patterns = ('shoot', 'fire my weapon', 'fire the weapon', 'shoot him', 'shoot her', 'shoot them')
    if any(term in low for term in deadly_patterns) and not _negative_phrase(low, 'shoot') and 'do not fire' not in low:
        return {
            'severity': 'critical',
            'title': 'Exercise terminated — unjustified deadly-force decision',
            'public_outcome': 'Training simulation: the person is shot and may be seriously injured or killed.',
            'officer_outcome': 'The officer is removed from the scenario and from simulated duty. A criminal and administrative investigation is initiated in the exercise.',
            'legal_outcome': 'Training storyline: arrest or criminal charging of the officer is a possible consequence because the presented facts did not establish a deadly threat. This is a training outcome, not a real legal finding.',
            'fto': 'Immediate FTO alert required. The exercise cannot continue as though the decision were acceptable.',
        }

    if scenario_id == 'S005' and turn >= 1:
        if any(term in low for term in ('turn my back', 'turn my back on', 'ignore the reaching', 'ignore his hands')):
            return {
                'severity': 'critical',
                'title': 'Exercise terminated — officer-safety failure',
                'public_outcome': 'Training simulation: the traffic contact escalates while the officer gives up observation and reaction time.',
                'officer_outcome': 'The officer is seriously injured in the exercise. The scenario ends for mandatory safety remediation.',
                'legal_outcome': 'No criminal conclusion is assigned. The training consequence is a preventable officer-safety failure.',
                'fto': 'Immediate FTO alert required for officer-safety remediation.',
            }

    if scenario_id == 'S006':
        if any(term in low for term in ('leave the patient', 'ignore the patient', 'cancel ems', 'send ems away')):
            return {
                'severity': 'critical',
                'title': 'Exercise terminated — medical-duty failure',
                'public_outcome': 'Training simulation: the patient deteriorates after medical care is disregarded or sent away.',
                'officer_outcome': 'The officer is removed from the scenario for mandatory remediation and supervisory review.',
                'legal_outcome': 'The exercise flags potential administrative/civil exposure; actual legal conclusions would depend on real facts and law.',
                'fto': 'Immediate FTO alert required.',
            }
    return None


def _nonterminal_consequence(scenario_id, turn, response_text, feedback):
    low = _normalize(response_text).lower()
    if feedback.get('accepted'):
        return None
    if any(term in low for term in ('tase', 'taser', 'pepper spray', 'oc spray', 'go hands on', 'use force')):
        return 'Your force decision increases risk and triggers an FTO stop. The scenario remains paused until you articulate necessity, proportionality, and the facts supporting the action.'
    if scenario_id == 'S005' and turn >= 1 and 'backup' not in low and any(term in low for term in ('reaching', 'console', 'hands')):
        return 'Risk remains elevated. Your next decision must account for the repeated reaching behavior and available resources.'
    if scenario_id == 'S004' and any(term in low for term in ('arrest', 'citation')) and not any(term in low for term in ('video', 'evidence', 'facts', 'probable cause')):
        return 'The enforcement decision is premature in the exercise because material evidence or legal articulation is still unresolved.'
    return None


def _terminate(state, outcome):
    state['terminated'] = True
    state['complete'] = True
    state['fto_alert'] = True
    state['terminal_outcome'] = outcome
    state['intervention_count'] = int(state.get('intervention_count', 0)) + 1
    rows = list(state.get('consequences') or [])
    rows.append(outcome['title'])
    state['consequences'] = rows[-8:]


def _stage_key(turn):
    return str(int(turn))


def _hint_status(state, turn):
    key = _stage_key(turn)
    attempts = int((state.get('stage_attempts') or {}).get(key, 0))
    interactions = int((state.get('stage_interactions') or {}).get(key, 0))
    used = int((state.get('stage_hints') or {}).get(key, 0))
    required_attempts = 3 + (used * 2)
    required_interactions = 5 + (used * 3)
    unlocked = attempts >= required_attempts or interactions >= required_interactions
    return {
        'unlocked': unlocked,
        'attempts': attempts,
        'interactions': interactions,
        'used': used,
        'required_attempts': required_attempts,
        'required_interactions': required_interactions,
    }


def _socratic_hint(scenario_id, turn, state):
    rubric = SCENARIO_RUBRICS[scenario_id][turn]
    previous_gaps = list((state.get('last_feedback') or {}).get('gaps') or [])
    labels = previous_gaps or [row[0] for row in rubric['criteria']]
    index = int((state.get('stage_hints') or {}).get(_stage_key(turn), 0))
    focus = labels[index % len(labels)] if labels else 'your decision-making process'
    prompts = [
        f'Reassess the situation through the lens of “{focus}.” What have you not yet established?',
        f'Before taking the next step, what fact or risk connected to “{focus}” still needs to be addressed?',
        f'Explain your reasoning for “{focus}” as if your FTO asked, “What fact made that action appropriate?”',
    ]
    return prompts[min(index, len(prompts) - 1)]


def _summary(state):
    result = _coaching_summary(state)
    result['actor_interactions'] = int(state.get('actor_interactions', 0))
    result['consequences'] = list(state.get('consequences') or [])
    result['fto_alert'] = bool(state.get('fto_alert'))
    return result


@bp.route('/', methods=['GET', 'POST'])
@login_required
def lab():
    requested_id = _valid_scenario(request.values.get('scenario_id') or 'S001')
    state = _state_for(requested_id)
    scenario_id = state['scenario_id']
    scenario = SCENARIOS[scenario_id]
    stages = scenario['stages']

    if request.method == 'POST':
        action = _normalize(request.form.get('action')).lower()

        if action in {'reset', 'switch'}:
            session[SESSION_KEY] = _new_state(requested_id)
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=requested_id))

        if action == 'next':
            next_id = NEXT_SCENARIO.get(scenario_id, 'S001')
            session[SESSION_KEY] = _new_state(next_id)
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=next_id))

        turn = int(state.get('turn', 0))

        if action == 'ask_actor':
            if state.get('complete'):
                flash('This exercise is complete. Start the next scenario or restart this one.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))
            actor_id = _normalize(request.form.get('actor_id'))
            question = _normalize(request.form.get('question_text'))[:800]
            actor = _actor_for(scenario_id, turn, actor_id)
            if not actor:
                flash('That person is not available at this point in the scenario.', 'warning')
            elif not question:
                flash('Ask a specific question before contacting the person.', 'warning')
            else:
                answer, mode = _roleplay_reply(scenario_id, turn, actor, question)
                _append_dialogue(state, actor, answer, mode)
                key = _stage_key(turn)
                counts = dict(state.get('stage_interactions') or {})
                counts[key] = int(counts.get(key, 0)) + 1
                state['stage_interactions'] = counts
                state['actor_interactions'] = int(state.get('actor_interactions', 0)) + 1
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'hint':
            if state.get('complete') or turn >= len(stages):
                flash('No hint is available at this point.', 'info')
            else:
                status = _hint_status(state, turn)
                if not status['unlocked']:
                    flash(
                        f"Coaching is still locked. Work the problem first: {status['attempts']}/{status['required_attempts']} decision attempts or {status['interactions']}/{status['required_interactions']} live contacts.",
                        'warning',
                    )
                else:
                    key = _stage_key(turn)
                    used = dict(state.get('stage_hints') or {})
                    hint_text = _socratic_hint(scenario_id, turn, state)
                    used[key] = int(used.get(key, 0)) + 1
                    state['stage_hints'] = used
                    state['hint_count'] = int(state.get('hint_count', 0)) + 1
                    state['last_feedback'] = {
                        'status': 'hint',
                        'accepted': False,
                        'headline': 'FTO coaching question — scenario not advanced',
                        'consequence': hint_text,
                        'strengths': [],
                        'gaps': [],
                        'hints': [],
                        'issues': [],
                        'met_count': 0,
                        'required_count': int(SCENARIO_RUBRICS[scenario_id][turn]['minimum']),
                        'criteria_count': len(SCENARIO_RUBRICS[scenario_id][turn]['criteria']),
                    }
                    session[SESSION_KEY] = state
                    session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'finish':
            if state.get('terminated'):
                flash('This exercise ended with a terminal training outcome. Review it, then continue to the next scenario.', 'warning')
            elif turn < len(stages):
                flash('Complete every decision point before finishing the coaching review.', 'warning')
            else:
                state['complete'] = True
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'act':
            if state.get('complete'):
                flash('This exercise is complete. Start the next scenario or restart this one.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))
            if turn >= len(stages):
                flash('All decision points are complete. Finish the scenario for the coaching review.', 'info')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            response_text = _normalize(request.form.get('response_text'))[:2500]
            if not response_text:
                flash('Describe what you would actually do before continuing.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            attempts = dict(state.get('stage_attempts') or {})
            key = _stage_key(turn)
            attempts[key] = int(attempts.get(key, 0)) + 1
            state['stage_attempts'] = attempts
            state['total_attempts'] = int(state.get('total_attempts', 0)) + 1

            catastrophic = _catastrophic_outcome(scenario_id, turn, response_text)
            if catastrophic:
                _terminate(state, catastrophic)
                session[SESSION_KEY] = state
                session.modified = True
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            feedback = _evaluate_action(scenario_id, turn, response_text)
            feedback['attempt'] = attempts[key]
            state['last_feedback'] = feedback

            consequence = _nonterminal_consequence(scenario_id, turn, response_text, feedback)
            if consequence:
                rows = list(state.get('consequences') or [])
                rows.append(consequence)
                state['consequences'] = rows[-8:]

            if feedback['accepted']:
                _apply_action_cues(state, response_text)
                state['turn'] = turn + 1
            else:
                state['revision_count'] = int(state.get('revision_count', 0)) + 1
                if feedback.get('status') == 'intervention':
                    state['intervention_count'] = int(state.get('intervention_count', 0)) + 1

            session[SESSION_KEY] = state
            session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

    turn = int(state.get('turn', 0))
    current_stage = stages[turn] if turn < len(stages) else None
    latest_reveal = stages[turn - 1]['reveal'] if turn > 0 else None
    ready_to_finish = turn >= len(stages) and not state.get('terminated')
    hint_status = _hint_status(state, turn) if current_stage else None
    result = _summary(state) if state.get('complete') and not state.get('terminated') else None

    return render_template(
        'scenario_lab_live.html',
        user=current_user,
        scenarios=SCENARIOS,
        scenario_id=scenario_id,
        scenario=scenario,
        scene_meta=SCENARIO_META.get(scenario_id, {}),
        turn=turn,
        total_turns=len(stages),
        current_stage=current_stage,
        latest_reveal=latest_reveal,
        ready_to_finish=ready_to_finish,
        complete=bool(state.get('complete')),
        terminated=bool(state.get('terminated')),
        terminal_outcome=state.get('terminal_outcome'),
        fto_alert=bool(state.get('fto_alert')),
        feedback=state.get('last_feedback'),
        dialogue=list(state.get('dialogue') or []),
        consequences=list(state.get('consequences') or []),
        available_cast=_available_cast(scenario_id, turn),
        hint_status=hint_status,
        result=result,
        practice_areas=[label for label, _terms in PRACTICE_AREAS],
        next_scenario_id=NEXT_SCENARIO.get(scenario_id, 'S001'),
    )
