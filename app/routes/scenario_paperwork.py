from copy import deepcopy
from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..simulator.run_store import (
    can_evaluator_view,
    can_trainee_view,
    load_run,
    load_run_state,
    persist_run,
)
from ..simulator.training_requirements import requirements_for_scenario, trainee_requirement_choices
from ..simulator.world_state import add_timeline
from .fto_program import can_manage
from .scenario_lab import SCENARIOS


bp = Blueprint('scenario_paperwork', __name__, url_prefix='/scenario-paperwork')
SESSION_KEY = 'sentinel_scenario_lab_v2'
CID_DECISIONS = {
    'screen': 'CID screening is required',
    'notify': 'CID notification is required',
    'not_required': 'CID screening/notification is not required',
    'conditional': 'CID depends on additional facts / policy review',
}


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _utc_iso():
    return datetime.now(timezone.utc).isoformat()


def _active_state():
    state = session.get(SESSION_KEY)
    return state if isinstance(state, dict) else None


def _run_id(state):
    return _text(((state or {}).get('run_context') or {}).get('run_id'))


def _package(state):
    package = state.get('training_package')
    if not isinstance(package, dict):
        package = {
            'status': 'NOT_STARTED',
            'submissions': [],
            'fto_review': None,
        }
        state['training_package'] = package
    package.setdefault('submissions', [])
    package.setdefault('status', 'NOT_STARTED')
    package.setdefault('fto_review', None)
    return package


def _submission_from_form(state):
    selected = []
    seen = set()
    for value in request.form.getlist('selected_documents'):
        value = _text(value)
        key = value.lower()
        if value and key not in seen and 'blotter' not in key and 'desk journal' not in key:
            selected.append(value)
            seen.add(key)
    cid_decision = _text(request.form.get('cid_decision')).lower()
    if cid_decision not in CID_DECISIONS:
        cid_decision = ''
    narrative = (request.form.get('narrative') or '').strip()[:12000]
    notification_notes = (request.form.get('notification_notes') or '').strip()[:3000]
    return {
        'revision': len(_package(state).get('submissions') or []),
        'submitted_at': _utc_iso(),
        'selected_documents': selected,
        'cid_decision': cid_decision,
        'cid_decision_label': CID_DECISIONS.get(cid_decision, ''),
        'notification_notes': notification_notes,
        'narrative': narrative,
    }


def _comparison(scenario_id, submission):
    req = requirements_for_scenario(scenario_id)
    required_docs = req.get('officer_documents') or []
    selected = submission.get('selected_documents') or []
    selected_keys = {item.lower(): item for item in selected}
    required_keys = {item.lower(): item for item in required_docs}
    missing = [value for key, value in required_keys.items() if key not in selected_keys]
    extra = [value for key, value in selected_keys.items() if key not in required_keys]

    cid_required = (req.get('cid') or {}).get('requirement') or 'unconfigured'
    trainee_cid = submission.get('cid_decision') or ''
    cid_match = None
    if cid_required in {'screen', 'notify'}:
        cid_match = trainee_cid == cid_required
    elif cid_required == 'none':
        cid_match = trainee_cid == 'not_required'
    elif cid_required == 'conditional':
        cid_match = trainee_cid in {'conditional', 'screen', 'notify'}

    return {
        'requirements': req,
        'missing_documents': missing,
        'additional_documents': extra,
        'cid_match': cid_match,
        'cid_required': cid_required,
        'trainee_cid': trainee_cid,
    }


@bp.route('/', methods=['GET', 'POST'])
@login_required
def paperwork():
    state = _active_state()
    if state is None:
        flash('Start and complete a simulator call before opening training paperwork.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_lab.lab'))
    if not (state.get('complete') or state.get('terminated')):
        flash('Finish or clear the synthetic call before completing post-call paperwork.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state.get('scenario_id')))

    scenario_id = _text(state.get('scenario_id')).upper()
    package = _package(state)
    if request.method == 'POST':
        action = _text(request.form.get('action')).lower()
        if action not in {'submit', 'revise'}:
            flash('Unknown training-package action.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

        submission = _submission_from_form(state)
        if not submission['narrative']:
            flash('Complete the training narrative before submitting the package.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
        if not submission['cid_decision']:
            flash('Make a CID screening/notification decision before submitting the package.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

        submissions = list(package.get('submissions') or [])
        submission['revision'] = len(submissions)
        submissions.append(submission)
        package['submissions'] = submissions
        package['status'] = 'SUBMITTED'
        package['submitted_at'] = submission['submitted_at']
        package['latest_revision'] = submission['revision']
        state['training_package'] = package
        add_timeline(
            state,
            'training_package_submitted' if submission['revision'] == 0 else 'training_package_revised',
            'Post-call training paperwork submitted to the FTO.',
            actor='Trainee',
            channel='paperwork',
            details={
                'revision': submission['revision'],
                'selected_documents': submission['selected_documents'],
                'cid_decision': submission['cid_decision'],
            },
            visible_to_trainee=True,
        )
        session[SESSION_KEY] = state
        session.modified = True
        persist_run(state, current_user.id)
        flash('Training package submitted. The original submission is preserved for FTO review.', 'success')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

    latest = (package.get('submissions') or [])[-1] if package.get('submissions') else None
    return render_template(
        'scenario_paperwork.html',
        user=current_user,
        state=state,
        package=package,
        latest=latest,
        scenario=SCENARIOS.get(scenario_id) or {},
        scenario_id=scenario_id,
        run_id=_run_id(state),
        document_choices=trainee_requirement_choices(scenario_id),
        cid_decisions=CID_DECISIONS,
        evaluator_mode=False,
        comparison=None,
        run=None,
    )


@bp.get('/run/<run_id>')
@login_required
def review_paperwork(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    evaluator_access = can_evaluator_view(current_user, run, can_manage_fn=can_manage)
    trainee_access = can_trainee_view(current_user, run)
    if not (evaluator_access or trainee_access):
        abort(403)

    state = load_run_state(run)
    package = _package(state)
    latest = (package.get('submissions') or [])[-1] if package.get('submissions') else None
    comparison = _comparison(run.scenario_id, latest) if evaluator_access and latest else None
    return render_template(
        'scenario_paperwork.html',
        user=current_user,
        state=state,
        package=package,
        latest=latest,
        scenario=SCENARIOS.get(run.scenario_id) or {},
        scenario_id=run.scenario_id,
        run_id=run.run_id,
        document_choices=trainee_requirement_choices(run.scenario_id),
        cid_decisions=CID_DECISIONS,
        evaluator_mode=evaluator_access,
        comparison=comparison,
        run=run,
    )
