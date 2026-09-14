import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..services.ai_client import (
    ask_openai_with_system,
    configured_openai_api_key,
    is_ai_unavailable_message,
)
from .scenario_cast import SCENARIO_META
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
from .scenario_legal_context import legal_context_for
from .scenario_state_engine import (
    actor_available,
    apply_core_decision,
    current_decision,
    dynamic_facts,
    ensure_engine_state,
    evaluate_branch_event,
    pending_event,
    record_actor_interaction,
    resolve_branch_event,
    scene_status,
)
from .scenario_variants import NEXT_SCENARIO, actor_variant_fact, build_run_context

bp = Blueprint('scenario_lab', __name__, url_prefix='/scenario-lab')
SESSION_KEY = 'sentinel_scenario_lab_v2'

# Scenario Lab is synthetic practice. It never creates an official DOR score or
# makes a real criminal/legal finding. Consequences below are exercise outcomes.


def _new_state(scenario_id):
    state = {
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
        'run_context': build_run_context(scenario_id),
    }
    ensure_engine_state(state, scenario_id)
    return state


def _state_for(scenario_id):
    state = session.get(SESSION_KEY)
    if not isinstance(state, dict) or state.get('scenario_id') != scenario_id:
        state = _new_state(scenario_id)
        session[SESSION_KEY] = state
        session.modified = True
        return state

    defaults = _new_state(scenario_id)
    for key, value in defaults.items():
        if key not in state:
            state[key] = value
    ensure_engine_state(state, scenario_id)
    session[SESSION_KEY] = state
    session.modified = True
    return state


def _available_cast(state, scenario_id, turn):
    rows = []
    for actor in SCENARIO_META.get(scenario_id, {}).get('cast', []):
        if int(actor.get('from', 0)) <= turn and actor_available(state, scenario_id, actor['id']):
            rows.append(actor)
    return rows


def _actor_for(state, scenario_id, turn, actor_id):
    for actor in _available_cast(state, scenario_id, turn):
        if actor['id'] == actor_id:
            return actor
    return None


def _released_facts(state, scenario_id, turn):
    scenario = SCENARIOS[scenario_id]
    run_context = state.get('run_context') or {}
    facts = [f"Dispatch: {run_context.get('dispatch_variant') or scenario['dispatch']}"]
    for index in range(min(turn, len(scenario['stages']))):
        facts.append(scenario['stages'][index]['reveal'])
    facts.extend(dynamic_facts(state, scenario_id))
    return facts


def _fallback_actor_reply(state, scenario_id, actor, question):
    variant = actor_variant_fact(state.get('run_context') or {}, actor['id'], question)
    if variant:
        return variant
    low = _normalize(question).lower()
    for pattern, reply in actor.get('facts', []):
        if re.search(pattern, low):
            return reply
    role = actor.get('role', 'person')
    if role == 'Radio':
        return 'Dispatch copies. Be more specific about the information or resource you are requesting.'
    if role == 'Subject':
        return 'What exactly are you asking me?'
    if role == 'Patient':
        return 'I am not sure. Ask me one specific thing at a time.'
    return 'I can answer what I personally know, but I need a more specific question.'


def _roleplay_reply(state, scenario_id, turn, actor, question):
    fallback = _fallback_actor_reply(state, scenario_id, actor, question)
    api_key = configured_openai_api_key()
    if not api_key:
        return fallback, 'scripted'

    variant_fact = actor_variant_fact(state.get('run_context') or {}, actor['id'], question)
    actor_facts = [reply for _pattern, reply in actor.get('facts', [])]
    if variant_fact:
        actor_facts.append(variant_fact)
    allowed = '\n'.join(f'- {fact}' for fact in actor_facts) or '- No additional facts.'
    released = '\n'.join(f'- {fact}' for fact in _released_facts(state, scenario_id, turn))
    system_prompt = f"""You are role-playing one person in a synthetic police field-training scenario.
Character: {actor['name']} ({actor['role']}).
Scenario: {SCENARIOS[scenario_id]['title']}.
Run ID: {(state.get('run_context') or {}).get('run_id', 'synthetic')}.

Facts already available in the exercise:
{released}

Facts this character is allowed to know or state:
{allowed}

Rules:
- Stay in character and answer only the trainee officer's question.
- Use 1-3 short natural sentences.
- Never coach the officer, never say what the officer should do, and never reveal evaluation criteria.
- Never invent a weapon, crime, injury, confession, legal authority, policy requirement, or future fact.
- Never reveal facts from a later phase or unreleased branch.
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
        'phase': int(state.get('turn', 0)),
    })
    state['dialogue'] = rows[-12:]


def _append_consequences(state, values):
    rows = list(state.get('consequences') or [])
    for value in values or []:
        value = _normalize(value)
        if value and value not in rows:
            rows.append(value)
    state['consequences'] = rows[-12:]


def _negative_phrase(low, term):
    return bool(re.search(rf"\b(?:do not|don't|would not|wouldn't|not going to|will not)\s+(?:\w+\s+){{0,2}}{term}\b", low))


def _catastrophic_outcome(scenario_id, turn, response_text):
    low = _normalize(response_text).lower()
    deadly_patterns = ('shoot', 'fire my weapon', 'fire the weapon', 'shoot him', 'shoot her', 'shoot them')
    if any(term in low for term in deadly_patterns) and not _negative_phrase(low, 'shoot') and 'do not fire' not in low:
        return {
            'severity': 'critical',
            'title': 'Exercise terminated — unjustified deadly-force decision',
            'public_outcome': 'Training simulation: a person is shot and may be seriously injured or killed.',
            'officer_outcome': 'The officer is removed from the scenario and simulated duty. A criminal and administrative investigation begins in the exercise.',
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

    if scenario_id == 'S006' and any(term in low for term in ('leave the patient', 'ignore the patient', 'cancel ems', 'send ems away')):
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
        return 'Your control decision increases risk and triggers an FTO stop. The call remains paused until the necessity and supporting facts are articulated.'
    if scenario_id == 'S005' and turn >= 1 and 'backup' not in low and any(term in low for term in ('reaching', 'console', 'hands')):
        return 'Risk remains elevated. Later events may now be harder because additional resources were not requested.'
    if scenario_id == 'S004' and any(term in low for term in ('arrest', 'citation')) and not any(term in low for term in ('video', 'evidence', 'facts', 'probable cause')):
        return 'The enforcement decision is premature in the exercise because material evidence or legal articulation remains unresolved.'
    return None


def _terminate(state, outcome):
    state['terminated'] = True
    state['complete'] = True
    state['fto_alert'] = True
    state['terminal_outcome'] = outcome
    state['intervention_count'] = int(state.get('intervention_count', 0)) + 1
    _append_consequences(state, [outcome['title']])


def _decision_key(state, turn):
    event = pending_event(state, state['scenario_id'])
    return f"event:{event['id']}" if event else str(int(turn))


def _decision_rubric(state, scenario_id, turn):
    decision = current_decision(state, scenario_id, turn, SCENARIOS[scenario_id]['stages'][turn] if turn < len(SCENARIOS[scenario_id]['stages']) else None)
    if decision and decision.get('rubric'):
        return decision['rubric']
    if turn < len(SCENARIO_RUBRICS[scenario_id]):
        return SCENARIO_RUBRICS[scenario_id][turn]
    return {'minimum': 0, 'criteria': []}


def _hint_status(state, turn):
    key = _decision_key(state, turn)
    attempts = int((state.get('stage_attempts') or {}).get(key, 0))
    interactions = int((state.get('stage_interactions') or {}).get(key, 0))
    used = int((state.get('stage_hints') or {}).get(key, 0))
    required_attempts = 3 + (used * 2)
    required_interactions = 5 + (used * 3)
    return {
        'unlocked': attempts >= required_attempts or interactions >= required_interactions,
        'attempts': attempts,
        'interactions': interactions,
        'used': used,
        'required_attempts': required_attempts,
        'required_interactions': required_interactions,
    }


def _socratic_hint(state, scenario_id, turn):
    rubric = _decision_rubric(state, scenario_id, turn)
    previous_gaps = list((state.get('last_feedback') or {}).get('gaps') or [])
    labels = previous_gaps or [row[0] for row in rubric.get('criteria', [])]
    key = _decision_key(state, turn)
    index = int((state.get('stage_hints') or {}).get(key, 0))
    focus = labels[index % len(labels)] if labels else 'your decision-making process'
    prompts = [
        f'Reassess the call through the lens of “{focus}.” What fact, risk, or resource have you not resolved?',
        f'What changed in the scene, and how does “{focus}” affect what you do next?',
        f'If your FTO asked, “What fact made that action appropriate?”, how would you explain “{focus}” without guessing?',
    ]
    return prompts[min(index, len(prompts) - 1)]


def _summary(state):
    result = _coaching_summary(state)
    engine = state.get('engine') or {}
    result['actor_interactions'] = int(state.get('actor_interactions', 0))
    result['consequences'] = list(state.get('consequences') or [])
    result['fto_alert'] = bool(state.get('fto_alert'))
    result['branch_count'] = int(engine.get('branch_count', 0))
    result['run_id'] = (state.get('run_context') or {}).get('run_id', '')
    result['complaint_risk'] = bool(engine.get('complaint_risk'))
    result['use_of_force_review'] = bool(engine.get('use_of_force_review'))
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
        active_event = pending_event(state, scenario_id)

        if action == 'ask_actor':
            if state.get('complete'):
                flash('This exercise is complete. Start the next scenario or restart this one.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))
            actor_id = _normalize(request.form.get('actor_id'))
            question = _normalize(request.form.get('question_text'))[:800]
            actor = _actor_for(state, scenario_id, turn, actor_id)
            if not actor:
                flash('That person is not available in the current call state.', 'warning')
            elif not question:
                flash('Ask a specific question before contacting the person.', 'warning')
            else:
                answer, mode = _roleplay_reply(state, scenario_id, turn, actor, question)
                _append_dialogue(state, actor, answer, mode)
                key = _decision_key(state, turn)
                counts = dict(state.get('stage_interactions') or {})
                counts[key] = int(counts.get(key, 0)) + 1
                state['stage_interactions'] = counts
                state['actor_interactions'] = int(state.get('actor_interactions', 0)) + 1
                _append_consequences(state, record_actor_interaction(state, scenario_id, turn, actor_id, question))
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'hint':
            if state.get('complete'):
                flash('No coaching is available after the exercise ends.', 'info')
            else:
                status = _hint_status(state, turn)
                if not status['unlocked']:
                    flash(
                        f"Coaching is still locked. Keep working the call first: {status['attempts']}/{status['required_attempts']} decisions or {status['interactions']}/{status['required_interactions']} live contacts in the current problem.",
                        'warning',
                    )
                else:
                    key = _decision_key(state, turn)
                    used = dict(state.get('stage_hints') or {})
                    hint_text = _socratic_hint(state, scenario_id, turn)
                    used[key] = int(used.get(key, 0)) + 1
                    state['stage_hints'] = used
                    state['hint_count'] = int(state.get('hint_count', 0)) + 1
                    rubric = _decision_rubric(state, scenario_id, turn)
                    state['last_feedback'] = {
                        'status': 'hint',
                        'accepted': False,
                        'headline': 'FTO coaching question — call not advanced',
                        'consequence': hint_text,
                        'strengths': [], 'gaps': [], 'hints': [], 'issues': [],
                        'met_count': 0,
                        'required_count': int(rubric.get('minimum', 0)),
                        'criteria_count': len(rubric.get('criteria', [])),
                    }
                    session[SESSION_KEY] = state
                    session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'finish':
            if state.get('terminated'):
                flash('This exercise ended with a terminal training outcome. Review it, then continue to the next scenario.', 'warning')
            elif pending_event(state, scenario_id):
                flash('A live event is still unresolved. Work the call before finishing.', 'warning')
            elif turn < len(stages):
                flash('The call is still active. Resolve the remaining incident phases before ending the run.', 'warning')
            else:
                state['complete'] = True
                session[SESSION_KEY] = state
                session.modified = True
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'act':
            if state.get('complete'):
                flash('This exercise is complete. Start the next scenario or restart this one.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))
            if turn >= len(stages) and not active_event:
                flash('The incident is ready to close. Finish the run for the coaching review.', 'info')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            response_text = _normalize(request.form.get('response_text'))[:2500]
            if not response_text:
                flash('Describe what you would actually do before continuing.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            key = _decision_key(state, turn)
            attempts = dict(state.get('stage_attempts') or {})
            attempts[key] = int(attempts.get(key, 0)) + 1
            state['stage_attempts'] = attempts
            state['total_attempts'] = int(state.get('total_attempts', 0)) + 1

            catastrophic = _catastrophic_outcome(scenario_id, turn, response_text)
            if catastrophic:
                _terminate(state, catastrophic)
                session[SESSION_KEY] = state
                session.modified = True
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            active_event = pending_event(state, scenario_id)
            if active_event:
                feedback = evaluate_branch_event(active_event['id'], response_text)
                feedback['attempt'] = attempts[key]
                state['last_feedback'] = feedback
                if feedback['accepted']:
                    _apply_action_cues(state, response_text)
                    _append_consequences(state, resolve_branch_event(state, scenario_id, active_event['id'], response_text))
                else:
                    state['revision_count'] = int(state.get('revision_count', 0)) + 1
                session[SESSION_KEY] = state
                session.modified = True
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

            feedback = _evaluate_action(scenario_id, turn, response_text)
            feedback['attempt'] = attempts[key]
            state['last_feedback'] = feedback
            consequence = _nonterminal_consequence(scenario_id, turn, response_text, feedback)
            if consequence:
                _append_consequences(state, [consequence])

            # Every committed decision changes time/risk/resources, even if it does not
            # satisfy the training standard. Poor decisions therefore have downstream cost.
            _append_consequences(state, apply_core_decision(state, scenario_id, turn, response_text, feedback['accepted']))

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
    core_stage = stages[turn] if turn < len(stages) else None
    decision = current_decision(state, scenario_id, turn, core_stage)
    latest_reveal = stages[turn - 1]['reveal'] if turn > 0 else None
    ready_to_finish = turn >= len(stages) and not pending_event(state, scenario_id) and not state.get('terminated')
    hint_status = _hint_status(state, turn) if decision and not state.get('complete') else None
    result = _summary(state) if state.get('complete') and not state.get('terminated') else None
    engine = state.get('engine') or {}
    legal_refs = legal_context_for(scenario_id, state.get('run_context') or {}, turn, engine)

    return render_template(
        'scenario_lab_live.html',
        user=current_user,
        scenarios=SCENARIOS,
        scenario_id=scenario_id,
        scenario=scenario,
        scene_meta=SCENARIO_META.get(scenario_id, {}),
        run_context=state.get('run_context') or {},
        scene_status=scene_status(state, scenario_id),
        turn=turn,
        core_phases_cleared=turn,
        current_stage=decision,
        latest_reveal=latest_reveal,
        ready_to_finish=ready_to_finish,
        complete=bool(state.get('complete')),
        terminated=bool(state.get('terminated')),
        terminal_outcome=state.get('terminal_outcome'),
        fto_alert=bool(state.get('fto_alert')),
        feedback=state.get('last_feedback'),
        dialogue=list(state.get('dialogue') or []),
        consequences=list(state.get('consequences') or []),
        available_cast=_available_cast(state, scenario_id, turn),
        hint_status=hint_status,
        result=result,
        practice_areas=[label for label, _terms in PRACTICE_AREAS],
        next_scenario_id=NEXT_SCENARIO.get(scenario_id, 'S001'),
        legal_refs=legal_refs,
    )
