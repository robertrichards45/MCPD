from flask import Blueprint, Response, abort
from flask_login import current_user, login_required

from ..simulator.crash_visual import render_s007_crash_svg
from ..simulator.evidence_visuals import initialize_visual_evidence, render_evidence_svg
from ..simulator.run_store import can_evaluator_view, can_trainee_view, load_run, load_run_state
from .fto_program import can_manage
from . import scenario_handbook_register as _scenario_handbook_register  # noqa: F401,E402


bp = Blueprint('scenario_evidence', __name__, url_prefix='/scenario-lab/evidence')


@bp.get('/<run_id>/<evidence_id>.svg')
@login_required
def evidence_svg(run_id, evidence_id):
    run = load_run(run_id)
    if run is None:
        abort(404)

    evaluator_access = can_evaluator_view(current_user, run, can_manage_fn=can_manage)
    trainee_access = can_trainee_view(current_user, run)
    if not (evaluator_access or trainee_access):
        abort(403)

    state = load_run_state(run)
    scenario_id = state.get('scenario_id') or run.scenario_id
    initialize_visual_evidence(state, scenario_id)

    # Evaluators may inspect hidden synthetic evidence from their authorized
    # evaluator view. Trainees only receive evidence already made visible by
    # their own actions in the run.
    evaluator_only = evaluator_access and not trainee_access
    svg = render_evidence_svg(state, evidence_id, evaluator=evaluator_only)
    if not svg and scenario_id == 'S007' and evidence_id == 'crash_scene':
        svg = render_s007_crash_svg(state, evaluator=evaluator_only)
    if not svg:
        abort(404)

    response = Response(svg, mimetype='image/svg+xml')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
