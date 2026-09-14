from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..simulator.run_store import load_run
from ..simulator.shift_engine import assign_next_call, complete_active_call, end_shift, new_shift


bp = Blueprint('scenario_shift', __name__, url_prefix='/scenario-lab/shift')
SHIFT_SESSION_KEY = 'sentinel_virtual_shift_v1'


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
    outcome = 'TERMINATED' if run.status == 'TERMINATED' else 'CLEARED'
    complete_active_call(shift, run_id, outcome=outcome)
    return shift


def _ensure_assignment(shift):
    if shift.get('status') != 'ACTIVE' or shift.get('active_scenario_id'):
        return shift
    assign_next_call(shift)
    return shift


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
            _save(shift_state)
            return redirect(url_for('reports.fto_refinements.scenario_shift.shift'))
        if action == 'end' and isinstance(shift_state, dict):
            _refresh_completed_call(shift_state)
            end_shift(shift_state)
            _save(shift_state)
            return redirect(url_for('reports.fto_refinements.scenario_shift.shift'))
        if action == 'respond' and isinstance(shift_state, dict) and shift_state.get('active_scenario_id'):
            _save(shift_state)
            return redirect(url_for(
                'reports.fto_refinements.scenario_lab.lab',
                scenario_id=shift_state['active_scenario_id'],
            ))

    if isinstance(shift_state, dict):
        _refresh_completed_call(shift_state)
        _ensure_assignment(shift_state)
        _save(shift_state)

    return render_template(
        'scenario_shift.html',
        user=current_user,
        shift=shift_state if isinstance(shift_state, dict) else None,
    )
