from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..simulator.instructor_control import inject_event, instructor_options
from ..simulator.run_store import can_evaluator_view, load_run, load_run_state, persist_run
from .fto_program import can_manage


bp = Blueprint('scenario_instructor', __name__, url_prefix='/scenario-lab/instructor')


@bp.route('/<run_id>', methods=['GET', 'POST'])
@login_required
def control(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    if not can_evaluator_view(current_user, run, can_manage_fn=can_manage):
        abort(403)

    state = load_run_state(run)
    if request.method == 'POST':
        if run.status in {'COMPLETED', 'TERMINATED'}:
            flash('Completed simulator runs are read-only.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_instructor.control', run_id=run.run_id))

        event_type = str(request.form.get('event_type') or '').strip()
        target_id = str(request.form.get('target_id') or '').strip()
        text = str(request.form.get('event_text') or '').strip()[:1200]
        delay = request.form.get('delay')
        environment = {
            key: request.form.get(key)
            for key in ('weather', 'lighting', 'noise', 'visibility', 'crowd')
        }
        result = inject_event(
            state,
            event_type,
            text=text,
            target_id=target_id,
            delay=delay,
            environment=environment,
        )
        if result.get('ok'):
            persist_run(state, run.trainee_id)
            flash(result.get('message') or 'Instructor event injected.', 'success')
        else:
            flash(result.get('message') or 'Instructor event was not applied.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_instructor.control', run_id=run.run_id))

    return render_template(
        'scenario_instructor.html',
        user=current_user,
        run=run,
        state=state,
        options=instructor_options(state),
    )
