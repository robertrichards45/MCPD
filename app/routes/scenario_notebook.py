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
from ..simulator.world_state import add_timeline
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


@bp.post('/complete-call')
@login_required
def complete_call():
    """Close the synthetic call and move the trainee into post-call documentation.

    A trainee is allowed to clear a call even when simulator objectives remain
    unfinished. That is realistic FTO evidence, not a reason to trap the trainee
    in the live scene. The run records whether the handoff occurred before all
    scenario stages were developed so the FTO can review the decision later.
    """
    state = _active_state()
    if state is None:
        flash('No active simulator call was found.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_lab.lab'))

    scenario_id = _text(state.get('scenario_id')).upper()
    scenario = SCENARIOS.get(scenario_id) or {}
    stages_total = len(scenario.get('stages') or [])
    turn = int(state.get('turn', 0) or 0)

    if not state.get('complete'):
        state['complete'] = True
        state['post_call_handoff'] = {
            'turn_at_clear': turn,
            'stages_total': stages_total,
            'cleared_before_all_core_stages': bool(stages_total and turn < stages_total),
            'source': 'trainee_end_call',
        }
        add_timeline(
            state,
            'call_cleared',
            'The trainee ended the synthetic call and moved to post-call documentation.',
            actor='Trainee',
            channel='radio',
            details=dict(state['post_call_handoff']),
            visible_to_trainee=True,
        )

    session[SESSION_KEY] = state
    session.modified = True
    persist_run(state, current_user.id)
    flash('Call closed. Complete the required training paperwork and notification decisions.', 'success')
    return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))


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
