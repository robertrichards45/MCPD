import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..simulator.run_store import load_run, load_run_state
from ..simulator.shift_engine import (
    assign_next_call,
    attach_run,
    complete_active_call,
    end_shift,
    new_shift,
    set_dispatch_details,
)
from .scenario_lab import SCENARIOS
from .scenario_variants import SEED_OVERRIDE_KEY, build_run_context


bp = Blueprint('scenario_shift', __name__, url_prefix='/scenario-lab/shift')
SHIFT_SESSION_KEY = 'sentinel_virtual_shift_v1'
SCENARIO_SESSION_KEY = 'sentinel_scenario_lab_v2'
RANDOM_DECK_KEY = 'sentinel_scenario_random_deck_v1'
LAUNCH_MODE_KEY = 'sentinel_scenario_launch_mode_v1'


def _save(shift):
    session[SHIFT_SESSION_KEY] = shift
    session.modified = True


def _refresh_completed_call(shift):
    run_id = shift.get('active_run_id')
    if not run_id:
        return shift
    run = load_run(run_id)
    if run is None or run.status not in {'COMPLETED', 'TERMINATED'}:
        return shift
    state = load_run_state(run)
    duration = int(((state.get('world') or {}).get('clock')) or 0)
    outcome = 'TERMINATED' if run.status == 'TERMINATED' else 'CLEARED'
    complete_active_call(shift, run_id, outcome=outcome, duration_minutes=max(1, duration))
    return shift


def _ensure_assignment(shift):
    if shift.get('status') != 'ACTIVE' or shift.get('active_scenario_id'):
        return shift
    scenario_id, _idle = assign_next_call(shift)
    run_context = build_run_context(scenario_id, seed=shift.get('active_call_seed'))
    set_dispatch_details(shift, run_context.get('dispatch_variant') or '')
    return shift


def _scenario_ids():
    return [str(value) for value in SCENARIOS.keys()]


def _draw_random_scenario():
    """Draw from a shuffled no-repeat deck of every registered scenario family."""
    scenario_ids = _scenario_ids()
    if not scenario_ids:
        return 'S001'

    current_state = session.get(SCENARIO_SESSION_KEY)
    current_id = current_state.get('scenario_id') if isinstance(current_state, dict) else None
    stored = session.get(RANDOM_DECK_KEY)
    deck = [sid for sid in stored if sid in scenario_ids] if isinstance(stored, list) else []

    if not deck:
        deck = list(scenario_ids)
        secrets.SystemRandom().shuffle(deck)

    # A random button should feel random. Never intentionally serve the exact
    # same scenario family twice in a row when another family is available.
    if len(deck) > 1 and deck[0] == current_id:
        replacement_index = next((idx for idx, sid in enumerate(deck[1:], start=1) if sid != current_id), None)
        if replacement_index is not None:
            deck[0], deck[replacement_index] = deck[replacement_index], deck[0]

    selected = deck.pop(0)
    session[RANDOM_DECK_KEY] = deck
    session.modified = True
    return selected


@bp.post('/launch')
@login_required
def launch_call():
    """Launch either a targeted scenario or a true blind random dispatch."""
    mode = str(request.form.get('mode') or 'selected').strip().lower()
    if mode == 'random':
        scenario_id = _draw_random_scenario()
        launch_mode = 'random'
    else:
        requested = str(request.form.get('scenario_id') or '').strip()
        scenario_id = requested if requested in SCENARIOS else (_scenario_ids()[0] if _scenario_ids() else 'S001')
        launch_mode = 'selected'

    # Force a fresh run even when the instructor deliberately relaunches the
    # same family. build_run_context will generate a new fact pattern/seed.
    session.pop(SCENARIO_SESSION_KEY, None)
    session.pop(SEED_OVERRIDE_KEY, None)
    session[LAUNCH_MODE_KEY] = {
        'mode': launch_mode,
        'scenario_id': scenario_id,
    }
    session.modified = True
    return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id))


def _start_assigned_run(shift_state):
    scenario_id = shift_state.get('active_scenario_id')
    if not scenario_id:
        return None
    if shift_state.get('active_run_id'):
        return shift_state.get('active_run_id')

    from .scenario_lab_live import _new_state

    session[SEED_OVERRIDE_KEY] = {
        'scenario_id': scenario_id,
        'seed': shift_state.get('active_call_seed'),
    }
    state = _new_state(scenario_id)
    state['shift_context'] = {
        'shift_id': shift_state.get('shift_id'),
        'call_number': shift_state.get('call_index'),
        'unit_id': shift_state.get('unit_id'),
    }
    session[SCENARIO_SESSION_KEY] = state
    session[LAUNCH_MODE_KEY] = {
        'mode': 'shift',
        'scenario_id': scenario_id,
    }
    run_id = (state.get('run_context') or {}).get('run_id')
    attach_run(shift_state, scenario_id, run_id, shift_state.get('active_dispatch_text'))
    session.modified = True
    return run_id


@bp.route('/', methods=['GET', 'POST'])
@login_required
def shift():
    shift_state = session.get(SHIFT_SESSION_KEY)

    if request.method == 'POST':
        action = str(request.form.get('action') or '').strip().lower()
        if action == 'start':
            unit_id = str(request.form.get('unit_id') or '214').strip()[:20] or '214'
            shift_state = new_shift(unit_id=unit_id)
            _ensure_assignment(shift_state)
            session.pop(SCENARIO_SESSION_KEY, None)
            session[LAUNCH_MODE_KEY] = {'mode': 'shift', 'scenario_id': shift_state.get('active_scenario_id')}
            _save(shift_state)
            return redirect(url_for('reports.fto_refinements.scenario_shift.shift'))
        if action == 'end' and isinstance(shift_state, dict):
            _refresh_completed_call(shift_state)
            end_shift(shift_state)
            _save(shift_state)
            return redirect(url_for('reports.fto_refinements.scenario_shift.shift'))
        if action == 'respond' and isinstance(shift_state, dict) and shift_state.get('active_scenario_id'):
            _start_assigned_run(shift_state)
            _save(shift_state)
            return redirect(url_for(
                'reports.fto_refinements.scenario_lab.lab',
                scenario_id=shift_state['active_scenario_id'],
                shift='1',
            ))

    if isinstance(shift_state, dict):
        _refresh_completed_call(shift_state)
        _ensure_assignment(shift_state)
        _save(shift_state)

    return render_template('scenario_shift.html', user=current_user, shift=shift_state if isinstance(shift_state, dict) else None)
