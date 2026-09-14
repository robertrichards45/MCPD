import re

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..simulator.action_interpreter import actions_to_semantic_text, interpret_action
from ..simulator.dispatch_engine import handle_radio_transmission
from ..simulator.npc_engine import respond as npc_respond
from ..simulator.run_store import (
    can_evaluator_view,
    can_trainee_view,
    load_run,
    load_run_state,
    persist_run,
    send_fto_coaching,
    set_coaching_mode,
    set_pause,
)
from ..simulator.world_state import (
    add_known_information,
    add_timeline,
    apply_interpreted_actions,
    discover_person,
    ensure_world_state,
    evaluator_world,
    observable_world,
)
from .fto_program import can_manage
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
    resolve_branch_event,
    scene_status,
)
from .scenario_variants import NEXT_SCENARIO, actor_variant_fact, build_run_context

bp = Blueprint('scenario_lab', __name__, url_prefix='/scenario-lab')
SESSION_KEY = 'sentinel_scenario_lab_v2'


def _new_state(scenario_id):
    run_context = build_run_context(scenario_id)
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
        'semantic_actions': {},
        'total_attempts': 0,
        'revision_count': 0,
        'intervention_count': 0,
        'hint_count': 0,
        'actor_interactions': 0,
        'last_feedback': None,
        'dialogue': [],
        'consequences': [],
        'run_context': run_context,
    }
    ensure_engine_state(state, scenario_id)
    ensure_world_state(state, scenario_id)
    dispatch_text = run_context.get('dispatch_variant') or SCENARIOS[scenario_id]['dispatch']
    add_known_information(state, dispatch_text, source='dispatch')
    add_timeline(state, 'dispatch', dispatch_text, actor='Dispatch', channel='radio', visible_to_trainee=True)
    return state


def _merge_remote_controls(state):
    run_id = str(((state.get('run_context') or {}).get('run_id')) or '').strip()
    if not run_id or not getattr(current_user, 'is_authenticated', False):
        return state
    row = load_run(run_id)
    if row is None or row.trainee_id != current_user.id:
        return state
    remote = load_run_state(row)
    remote_world = remote.get('world') or {}
    world = ensure_world_state(state, state.get('scenario_id', ''))
    for key in ('paused', 'coaching_mode', 'fto_message'):
        if key in remote_world:
            world[key] = remote_world[key]
    return state


def _state_for(scenario_id):
    state = session.get(SESSION_KEY)
    if not isinstance(state, dict) or state.get('scenario_id') != scenario_id:
        state = _new_state(scenario_id)
    else:
        defaults = {
            'complete': False, 'terminated': False, 'terminal_outcome': None,
            'fto_alert': False, 'semantic_actions': {}, 'dialogue': [],
            'consequences': [], 'stage_attempts': {}, 'stage_interactions': {},
            'stage_hints': {}, 'total_attempts': 0, 'revision_count': 0,
            'intervention_count': 0, 'hint_count': 0, 'actor_interactions': 0,
            'last_feedback': None,
        }
        for key, value in defaults.items():
            state.setdefault(key, value)
        if not state.get('run_context'):
            state['run_context'] = build_run_context(scenario_id)
        ensure_engine_state(state, scenario_id)
        ensure_world_state(state, scenario_id)
    _merge_remote_controls(state)
    _sync_discovered_people(state, scenario_id, int(state.get('turn', 0)))
    session[SESSION_KEY] = state
    session.modified = True
    return state


def _available_cast(state, scenario_id, turn):
    rows = []
    for actor in SCENARIO_META.get(scenario_id, {}).get('cast', []):
        if actor.get('role') == 'Radio':
            continue
        if int(actor.get('from', 0)) <= turn and actor_available(state, scenario_id, actor['id']):
            rows.append(actor)
    return rows


def _sync_discovered_people(state, scenario_id, turn):
    for actor in _available_cast(state, scenario_id, turn):
        discover_person(state, actor)


def _released_facts(state, scenario_id, turn):
    scenario = SCENARIOS[scenario_id]
    run_context = state.get('run_context') or {}
    facts = [run_context.get('dispatch_variant') or scenario['dispatch']]
    for index in range(min(turn, len(scenario['stages']))):
        facts.append(scenario['stages'][index]['reveal'])
    facts.extend(dynamic_facts(state, scenario_id))
    return [_normalize(value) for value in facts if _normalize(value)]


def _actor_by_id(state, scenario_id, turn, actor_id):
    for actor in _available_cast(state, scenario_id, turn):
        if actor.get('id') == actor_id:
            return actor
    return None


def _resolve_actor(state, scenario_id, turn, actions):
    visible = _available_cast(state, scenario_id, turn)
    targets = [str(row.get('target') or '').strip().lower() for row in (actions or []) if row.get('target')]
    for target in targets:
        for actor in visible:
            if target in {str(actor.get('id')).lower(), str(actor.get('name')).lower(), str(actor.get('role')).lower()}:
                return actor
    if len(visible) == 1:
        return visible[0]
    return None


def _fallback_actor_reply(state, scenario_id, actor, question):
    variant = actor_variant_fact(state.get('run_context') or {}, actor['id'], question)
    if variant:
        return variant
    low = _normalize(question).lower()
    for pattern, reply in actor.get('facts', []):
        if re.search(pattern, low):
            return reply
    if actor.get('role') == 'Subject':
        return 'What exactly are you asking me?'
    if actor.get('role') == 'Patient':
        return 'Ask me one specific thing at a time.'
    return 'I can tell you what I personally know, but I need a more specific question.'


def _talk_to_actor(state, scenario_id, turn, actor, officer_text, actions):
    allowed = [reply for _pattern, reply in actor.get('facts', [])]
    variant = actor_variant_fact(state.get('run_context') or {}, actor['id'], officer_text)
    if variant:
        allowed.append(variant)
    answer, mode = npc_respond(
        state,
        actor,
        officer_text,
        allowed_facts=allowed,
        visible_facts=_released_facts(state, scenario_id, turn),
        fallback=_fallback_actor_reply(state, scenario_id, actor, officer_text),
        run_context=state.get('run_context') or {},
        officer_actions=actions,
    )
    dialogue = list(state.get('dialogue') or [])
    dialogue.append({
        'actor': actor.get('name'), 'role': actor.get('role'),
        'question': _normalize(officer_text)[:1000], 'answer': answer,
        'mode': mode, 'clock': (state.get('world') or {}).get('clock', 0),
    })
    state['dialogue'] = dialogue[-30:]
    add_timeline(state, 'npc_response', answer, actor=actor.get('name'), channel='face_to_face', details={'actor_id': actor.get('id')})
    state['actor_interactions'] = int(state.get('actor_interactions', 0)) + 1
    return answer


def _append_consequences(state, values):
    rows = list(state.get('consequences') or [])
    for value in values or []:
        value = _normalize(value)
        if value and value not in rows:
            rows.append(value)
            add_timeline(state, 'consequence', value, actor='Simulation', channel='scene', visible_to_trainee=True)
    state['consequences'] = rows[-20:]


def _negative_phrase(low, term):
    return bool(re.search(rf"\b(?:do not|don't|would not|wouldn't|not going to|will not)\s+(?:\w+\s+){{0,2}}{term}\b", low))


def _catastrophic_outcome(scenario_id, turn, response_text):
    low = _normalize(response_text).lower()
    deadly_patterns = ('shoot', 'fire my weapon', 'fire the weapon', 'shoot him', 'shoot her', 'shoot them')
    if any(term in low for term in deadly_patterns) and not _negative_phrase(low, 'shoot') and 'do not fire' not in low:
        return {
            'severity': 'critical',
            'title': 'Exercise terminated — deadly-force decision unsupported by presented facts',
            'public_outcome': 'Training simulation: a person is shot and may be seriously injured or killed.',
            'officer_outcome': 'The officer is removed from the simulated patrol role and the incident moves to criminal/administrative review in the training storyline.',
            'legal_outcome': 'The simulator flags the decision for human legal and FTO review. It does not make a real criminal finding.',
            'fto': 'Immediate FTO review required.',
        }
    if scenario_id == 'S005' and turn >= 1 and any(term in low for term in ('turn my back', 'ignore the reaching', 'ignore his hands')):
        return {
            'severity': 'critical',
            'title': 'Exercise terminated — preventable officer-safety failure',
            'public_outcome': 'Training simulation: the contact escalates while the officer gives up observation and reaction time.',
            'officer_outcome': 'The officer is seriously injured in the exercise and the run ends for remediation.',
            'legal_outcome': 'No automatic criminal conclusion is assigned.',
            'fto': 'Immediate FTO review required.',
        }
    if scenario_id == 'S006' and any(term in low for term in ('leave the patient', 'ignore the patient', 'cancel ems', 'send ems away')):
        return {
            'severity': 'critical',
            'title': 'Exercise terminated — medical-duty failure',
            'public_outcome': 'Training simulation: the patient deteriorates after medical care is disregarded.',
            'officer_outcome': 'The officer is removed from the run for remediation and supervisory review.',
            'legal_outcome': 'Potential administrative/civil exposure is flagged for human review only.',
            'fto': 'Immediate FTO review required.',
        }
    return None


def _terminate(state, outcome):
    state['terminated'] = True
    state['complete'] = True
    state['fto_alert'] = True
    state['terminal_outcome'] = outcome
    state['intervention_count'] = int(state.get('intervention_count', 0)) + 1
    add_timeline(state, 'terminal_outcome', outcome.get('title'), actor='Simulation', channel='system', details=outcome, visible_to_trainee=True)


def _decision_key(state, turn):
    event = pending_event(state, state['scenario_id'])
    return f"event:{event['id']}" if event else str(int(turn))


def _accumulate_semantics(state, key, actions, raw_text):
    rows = dict(state.get('semantic_actions') or {})
    existing = list(rows.get(key) or [])
    for action in actions or []:
        existing.append({
            'action_type': action.get('action_type'),
            'target': action.get('target'),
            'reason': action.get('reason'),
            'confidence': action.get('confidence'),
        })
    rows[key] = existing[-40:]
    state['semantic_actions'] = rows
    return actions_to_semantic_text(existing, original_text=raw_text)


def _hidden_evaluate_and_advance(state, scenario_id, raw_text, actions):
    scenario = SCENARIOS[scenario_id]
    stages = scenario['stages']
    turn = int(state.get('turn', 0))
    if turn >= len(stages) and not pending_event(state, scenario_id):
        return

    catastrophic = _catastrophic_outcome(scenario_id, turn, raw_text)
    if catastrophic:
        _terminate(state, catastrophic)
        return

    key = _decision_key(state, turn)
    cumulative_semantic = _accumulate_semantics(state, key, actions, raw_text)
    current_semantic = actions_to_semantic_text(actions, original_text=raw_text)
    attempts = dict(state.get('stage_attempts') or {})
    attempts[key] = int(attempts.get(key, 0)) + 1
    state['stage_attempts'] = attempts
    state['total_attempts'] = int(state.get('total_attempts', 0)) + 1

    active_event = pending_event(state, scenario_id)
    if active_event:
        feedback = evaluate_branch_event(active_event['id'], cumulative_semantic)
        feedback['attempt'] = attempts[key]
        state['last_feedback'] = feedback
        add_timeline(state, 'evaluator_observation', 'Hidden evaluator observation recorded.', actor='Evaluator', channel='hidden', details=feedback, visible_to_trainee=False)
        if feedback['accepted']:
            _apply_action_cues(state, current_semantic)
            _append_consequences(state, resolve_branch_event(state, scenario_id, active_event['id'], cumulative_semantic))
        else:
            state['revision_count'] = int(state.get('revision_count', 0)) + 1
        return

    feedback = _evaluate_action(scenario_id, turn, cumulative_semantic)
    feedback['attempt'] = attempts[key]
    state['last_feedback'] = feedback
    add_timeline(state, 'evaluator_observation', 'Hidden evaluator observation recorded.', actor='Evaluator', channel='hidden', details=feedback, visible_to_trainee=False)

    # The legacy event engine receives canonical semantic intent, never the raw
    # trainee wording. This preserves deterministic consequences while the
    # simulator migrates away from stage rubrics.
    _append_consequences(state, apply_core_decision(state, scenario_id, turn, current_semantic, feedback['accepted']))

    if feedback['accepted']:
        _apply_action_cues(state, current_semantic)
        state['turn'] = turn + 1
        reveal = stages[turn]['reveal']
        add_known_information(state, reveal, source='scene')
        add_timeline(state, 'scene_development', reveal, actor='Scene', channel='scene', visible_to_trainee=True)
        _sync_discovered_people(state, scenario_id, state['turn'])
    else:
        state['revision_count'] = int(state.get('revision_count', 0)) + 1
        if feedback.get('status') == 'intervention':
            state['intervention_count'] = int(state.get('intervention_count', 0)) + 1


def _maybe_complete_after_clear(state, actions):
    if state.get('terminated'):
        return
    scenario_id = state['scenario_id']
    all_core_done = int(state.get('turn', 0)) >= len(SCENARIOS[scenario_id]['stages'])
    no_event = pending_event(state, scenario_id) is None
    types = {str(row.get('action_type') or '').lower() for row in (actions or [])}
    if all_core_done and no_event and 'clear_call' in types:
        state['complete'] = True
        add_timeline(state, 'call_cleared', 'The trainee clears the synthetic call.', actor='Trainee', channel='radio', visible_to_trainee=True)


def _persist_session_state(state):
    session[SESSION_KEY] = state
    session.modified = True
    try:
        return persist_run(state, current_user.id)
    except Exception:
        # The simulator remains usable if persistence is temporarily unavailable;
        # session state is still preserved and CI exercises the DB-backed path.
        return None


def _evaluator_url(run):
    if not run:
        return None
    if can_evaluator_view(current_user, run, can_manage_fn=can_manage):
        return url_for('reports.fto_refinements.scenario_lab.evaluator', run_id=run.run_id)
    return None


@bp.route('/', methods=['GET', 'POST'])
@login_required
def lab():
    requested_id = _valid_scenario(request.values.get('scenario_id') or 'S001')
    state = _state_for(requested_id)
    scenario_id = state['scenario_id']
    scenario = SCENARIOS[scenario_id]

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

        world = ensure_world_state(state, scenario_id)
        if world.get('paused'):
            flash('The instructor has paused this simulation. Your exact call state is preserved.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        turn = int(state.get('turn', 0))
        _sync_discovered_people(state, scenario_id, turn)
        visible_people = _available_cast(state, scenario_id, turn)
        visible_resources = [key for key, row in (world.get('resources') or {}).items() if row.get('status') != 'hidden']

        if action == 'radio':
            text = _normalize(request.form.get('radio_text'))[:1200]
            if not text:
                flash('Transmit something over the radio first.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))
            actions = interpret_action(text, channel='radio', visible_people=visible_people, visible_resources=visible_resources)
            handle_radio_transmission(state, actions, text, state.get('run_context') or {})
            apply_interpreted_actions(state, actions, raw_text=text, channel='radio')
            _hidden_evaluate_and_advance(state, scenario_id, text, actions)
            _maybe_complete_after_clear(state, actions)
            _persist_session_state(state)
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action in {'officer_action', 'act'}:
            text = _normalize(request.form.get('command_text') or request.form.get('response_text'))[:2500]
            if not text:
                flash('State what you do or say before continuing.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))
            actions = interpret_action(text, channel='scene', visible_people=visible_people, visible_resources=visible_resources)
            apply_interpreted_actions(state, actions, raw_text=text, channel='scene')

            action_types = {str(row.get('action_type') or '').lower() for row in actions}
            if action_types & {'speak', 'interview'}:
                actor = _resolve_actor(state, scenario_id, turn, actions)
                if actor:
                    _talk_to_actor(state, scenario_id, turn, actor, text, actions)
                else:
                    add_timeline(state, 'ambiguous_contact', 'The trainee spoke without identifying a specific present person.', actor='Simulation', channel='scene', visible_to_trainee=False)

            _hidden_evaluate_and_advance(state, scenario_id, text, actions)
            _maybe_complete_after_clear(state, actions)
            _persist_session_state(state)
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

        if action == 'hint':
            flash('Evaluation runs do not provide automated hints. An FTO may enable Coaching Mode when appropriate.', 'info')
            return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))

    _sync_discovered_people(state, scenario_id, int(state.get('turn', 0)))
    run = _persist_session_state(state)
    turn = int(state.get('turn', 0))
    latest_reveal = scenario['stages'][turn - 1]['reveal'] if turn > 0 and turn <= len(scenario['stages']) else None
    observable = observable_world(state)
    safe_status = scene_status(state, scenario_id)
    review_url = url_for('reports.fto_refinements.scenario_lab.review', run_id=run.run_id) if run and state.get('complete') else None

    return render_template(
        'scenario_lab_live.html',
        user=current_user,
        scenarios=SCENARIOS,
        scenario_id=scenario_id,
        scenario=scenario,
        scene_meta=SCENARIO_META.get(scenario_id, {}),
        run_context=state.get('run_context') or {},
        observable=observable,
        visible_scene_updates=list(safe_status.get('updates') or []),
        latest_reveal=latest_reveal,
        complete=bool(state.get('complete')),
        terminated=bool(state.get('terminated')),
        terminal_outcome=state.get('terminal_outcome'),
        evaluator_url=_evaluator_url(run),
        review_url=review_url,
    )


@bp.get('/evaluator/<run_id>')
@login_required
def evaluator(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    if not can_evaluator_view(current_user, run, can_manage_fn=can_manage):
        abort(403)
    state = load_run_state(run)
    scenario_id = state.get('scenario_id') or run.scenario_id
    turn = int(state.get('turn', 0))
    engine = state.get('engine') or {}
    legal_refs = legal_context_for(scenario_id, state.get('run_context') or {}, turn, engine)
    events = run.events.order_by(run.events.column_descriptions[0]['entity'].sequence.asc()).all()
    return render_template(
        'scenario_lab_evaluator.html',
        user=current_user,
        run=run,
        state=state,
        world=evaluator_world(state),
        engine=engine,
        turn=turn,
        feedback=state.get('last_feedback'),
        legal_refs=legal_refs,
        events=events,
    )


@bp.post('/evaluator/<run_id>/control')
@login_required
def evaluator_control(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    if not can_evaluator_view(current_user, run, can_manage_fn=can_manage):
        abort(403)
    control = _normalize(request.form.get('control')).lower()
    if control == 'pause':
        set_pause(run, True)
    elif control == 'resume':
        set_pause(run, False)
    elif control == 'coaching_on':
        set_coaching_mode(run, True)
    elif control == 'coaching_off':
        set_coaching_mode(run, False)
    elif control == 'coach':
        message = _normalize(request.form.get('message'))[:1000]
        if message:
            send_fto_coaching(run, message)
    return redirect(url_for('reports.fto_refinements.scenario_lab.evaluator', run_id=run_id))


@bp.get('/review/<run_id>')
@login_required
def review(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    evaluator_access = can_evaluator_view(current_user, run, can_manage_fn=can_manage)
    trainee_access = can_trainee_view(current_user, run)
    if not (evaluator_access or trainee_access):
        abort(403)
    if run.status not in {'COMPLETED', 'TERMINATED'} and not evaluator_access:
        abort(403)
    state = load_run_state(run)
    scenario_id = state.get('scenario_id') or run.scenario_id
    turn = int(state.get('turn', 0))
    engine = state.get('engine') or {}
    result = _coaching_summary(state)
    result['actor_interactions'] = int(state.get('actor_interactions', 0))
    result['run_id'] = run.run_id
    legal_refs = legal_context_for(scenario_id, state.get('run_context') or {}, turn, engine)
    events = run.events.order_by(run.events.column_descriptions[0]['entity'].sequence.asc()).all()
    return render_template(
        'scenario_lab_review.html',
        user=current_user,
        run=run,
        state=state,
        result=result,
        legal_refs=legal_refs,
        events=events,
        evaluator_access=evaluator_access,
    )
