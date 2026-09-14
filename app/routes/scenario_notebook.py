from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..simulator.field_notebook import add_field_note, field_notes, revise_field_note
from ..simulator.run_store import (
    can_evaluator_view,
    can_trainee_view,
    load_run,
    load_run_state,
    persist_run,
)
from .fto_program import can_manage
from .scenario_lab import SCENARIOS


bp = Blueprint('scenario_notebook', __name__, url_prefix='/scenario-notebook')
SESSION_KEY = 'sentinel_scenario_lab_v2'


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _active_state():
    state = session.get(SESSION_KEY)
    return state if isinstance(state, dict) else None


def _scenario_label(state):
    scenario_id = _text((state or {}).get('scenario_id'))
    scenario = SCENARIOS.get(scenario_id) or {}
    return scenario_id, scenario.get('title') or scenario_id or 'No active scenario'


def _run_id(state):
    return _text(((state or {}).get('run_context') or {}).get('run_id'))


@bp.route('/', methods=['GET', 'POST'])
@login_required
def notebook():
    state = _active_state()
    if state is None:
        return render_template(
            'scenario_notebook.html',
            user=current_user,
            state=None,
            notes=[],
            editable=False,
            evaluator_mode=False,
            run=None,
            run_id='',
            scenario_id='',
            scenario_title='No active scenario',
            back_url=url_for('reports.fto_refinements.scenario_lab.lab'),
        )

    scenario_id, scenario_title = _scenario_label(state)
    editable = not bool(state.get('complete') or state.get('terminated'))

    if request.method == 'POST':
        if not editable:
            flash('This run is closed. Field notes are preserved and can no longer be changed.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_notebook.notebook'))

        action = _text(request.form.get('action')).lower()
        if action == 'add':
            note = add_field_note(
                state,
                request.form.get('note_text'),
                category=request.form.get('category') or 'general',
            )
            if note is None:
                flash('Enter a field note before saving.', 'warning')
            else:
                flash('Field note saved to this training run.', 'success')
        elif action == 'revise':
            note = revise_field_note(
                state,
                request.form.get('note_id'),
                request.form.get('note_text'),
                category=request.form.get('category'),
            )
            if note is None:
                flash('That note could not be revised. Only the current active version can be amended.', 'warning')
            else:
                flash('Field note revised. The original entry remains preserved for FTO review.', 'success')
        else:
            flash('Unknown notebook action.', 'warning')

        session[SESSION_KEY] = state
        session.modified = True
        persist_run(state, current_user.id)
        return redirect(url_for('reports.fto_refinements.scenario_notebook.notebook'))

    return render_template(
        'scenario_notebook.html',
        user=current_user,
        state=state,
        notes=field_notes(state, include_superseded=True),
        editable=editable,
        evaluator_mode=False,
        run=None,
        run_id=_run_id(state),
        scenario_id=scenario_id,
        scenario_title=scenario_title,
        back_url=url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=scenario_id),
    )


@bp.get('/run/<run_id>')
@login_required
def review_notebook(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)

    evaluator_access = can_evaluator_view(current_user, run, can_manage_fn=can_manage)
    trainee_access = can_trainee_view(current_user, run)
    if not (evaluator_access or trainee_access):
        abort(403)

    state = load_run_state(run)
    scenario_id, scenario_title = _scenario_label(state)
    if evaluator_access:
        back_url = url_for('reports.fto_refinements.scenario_lab.evaluator', run_id=run.run_id)
    else:
        back_url = url_for('reports.fto_refinements.scenario_lab.review', run_id=run.run_id)

    return render_template(
        'scenario_notebook.html',
        user=current_user,
        state=state,
        notes=field_notes(state, include_superseded=True),
        editable=False,
        evaluator_mode=evaluator_access,
        run=run,
        run_id=run.run_id,
        scenario_id=scenario_id,
        scenario_title=scenario_title,
        back_url=back_url,
    )
