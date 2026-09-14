from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..fto_models import FTOProgramAssignment, FTOScenarioRun
from ..models import User
from ..simulator.analytics import aggregate_patterns, compare_runs, summarize_run
from ..simulator.run_store import load_run_state
from .fto_program import can_manage


bp = Blueprint('scenario_analytics', __name__, url_prefix='/scenario-lab/analytics')


def _assignment_for_trainee(trainee_id):
    return (
        FTOProgramAssignment.query
        .filter_by(trainee_id=trainee_id)
        .order_by(FTOProgramAssignment.updated_at.desc(), FTOProgramAssignment.id.desc())
        .first()
    )


def _can_view_analytics(user, trainee_id):
    if can_manage(user):
        return True
    assignment = _assignment_for_trainee(trainee_id)
    if assignment is None:
        return False
    return user.id in {assignment.assigned_fto_id, assignment.supervisor_id}


def _run_for_trainee(run_id, trainee_id):
    try:
        row_id = int(run_id or 0)
    except (TypeError, ValueError):
        return None
    if row_id <= 0:
        return None
    return FTOScenarioRun.query.filter_by(id=row_id, trainee_id=trainee_id).first()


@bp.get('/<int:trainee_id>')
@login_required
def dashboard(trainee_id):
    if not _can_view_analytics(current_user, trainee_id):
        abort(403)
    trainee = db.session.get(User, trainee_id)
    if trainee is None:
        abort(404)

    runs = (
        FTOScenarioRun.query
        .filter(
            FTOScenarioRun.trainee_id == trainee_id,
            FTOScenarioRun.status.in_(('COMPLETED', 'TERMINATED')),
        )
        .order_by(FTOScenarioRun.started_at.desc(), FTOScenarioRun.id.desc())
        .limit(50)
        .all()
    )
    states = [load_run_state(run) for run in runs]
    analytics = aggregate_patterns(states)
    run_summaries = {run.id: summarize_run(state) for run, state in zip(runs, states)}

    first = _run_for_trainee(request.args.get('first'), trainee_id)
    second = _run_for_trainee(request.args.get('second'), trainee_id)
    comparison = None
    comparison_error = ''
    if first and second:
        if first.id == second.id:
            comparison_error = 'Select two different runs to compare.'
        elif first.scenario_id != second.scenario_id:
            comparison_error = 'Run comparison is limited to the same scenario family so the evidence is meaningful.'
        else:
            comparison = compare_runs(load_run_state(first), load_run_state(second))

    return render_template(
        'scenario_analytics.html',
        user=current_user,
        trainee=trainee,
        runs=runs,
        analytics=analytics,
        run_summaries=run_summaries,
        first=first,
        second=second,
        comparison=comparison,
        comparison_error=comparison_error,
    )
