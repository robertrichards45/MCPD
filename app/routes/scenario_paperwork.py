import difflib
import secrets
from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..fto_models import FTORemediation
from ..simulator.report_consistency import review_training_narrative
from ..simulator.run_store import (
    can_evaluator_view,
    can_trainee_view,
    load_run,
    load_run_state,
    persist_run,
)
from ..simulator.training_forms import (
    existing_values_by_document,
    narrative_lines,
    parse_training_form_submission,
    training_form_definitions,
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
FTO_ACTIONS = {
    'accept': 'FTO_ACCEPTED',
    'correction': 'CORRECTION_REQUIRED',
    'remediation': 'REMEDIATION_REQUIRED',
}
ANNOTATION_CATEGORIES = {
    'factual_accuracy': 'Factual Accuracy',
    'chronology': 'Chronology',
    'source_attribution': 'Source Attribution',
    'completeness': 'Completeness',
    'form_field': 'Form Field',
    'policy_procedure': 'Policy / Procedure',
    'clarity': 'Clarity',
    'other': 'Other',
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


def _merge_remote_package(state):
    """Refresh FTO-side package review changes into the trainee's browser session."""
    run_id = _run_id(state)
    if not run_id or not getattr(current_user, 'is_authenticated', False):
        return state
    run = load_run(run_id)
    if run is None or run.trainee_id != current_user.id:
        return state
    remote_state = load_run_state(run)
    remote_package = remote_state.get('training_package')
    if isinstance(remote_package, dict):
        state['training_package'] = remote_package
        session[SESSION_KEY] = state
        session.modified = True
    return state


def _package(state):
    package = state.get('training_package')
    if not isinstance(package, dict):
        package = {
            'status': 'NOT_STARTED',
            'submissions': [],
            'review_history': [],
            'fto_review': None,
            'self_assessment': None,
            'trainee_acknowledgement': None,
            'annotations': [],
            'annotation_actions': [],
        }
        state['training_package'] = package
    package.setdefault('submissions', [])
    package.setdefault('review_history', [])
    package.setdefault('status', 'NOT_STARTED')
    package.setdefault('fto_review', None)
    package.setdefault('self_assessment', None)
    package.setdefault('trainee_acknowledgement', None)
    package.setdefault('annotations', [])
    package.setdefault('annotation_actions', [])
    return package


def _latest_submission(package):
    rows = package.get('submissions') or []
    return rows[-1] if rows else None


def _submission_by_revision(package, revision):
    for item in package.get('submissions') or []:
        if int(item.get('revision', -1)) == int(revision):
            return item
    return None


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
        'training_forms': [],
        'training_form_history': [],
        'forms_complete': not bool(selected),
    }


def _self_assessment_from_form():
    return {
        'submitted_at': _utc_iso(),
        'what_went_well': (request.form.get('what_went_well') or '').strip()[:4000],
        'what_change': (request.form.get('what_change') or '').strip()[:4000],
        'decision_basis': (request.form.get('decision_basis') or '').strip()[:4000],
        'notifications_considered': (request.form.get('notifications_considered') or '').strip()[:3000],
        'training_need': (request.form.get('training_need') or '').strip()[:3000],
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
        'report_analysis': submission.get('report_analysis') or {'mode': 'not_run', 'suggestions': []},
    }


def _flatten_form_fields(submission):
    rows = []
    for document in (submission or {}).get('training_forms') or []:
        document_id = _text(document.get('document_id'))
        document_name = _text(document.get('document_name'))
        for index, field in enumerate(document.get('fields') or []):
            if not isinstance(field, dict):
                continue
            rows.append({
                'key': f'{document_id}:{index}',
                'document_id': document_id,
                'document_name': document_name,
                'field_index': index,
                'name': _text(field.get('name')),
                'label': _text(field.get('label')) or _text(field.get('name')),
                'value': str(field.get('value') or '').strip(),
            })
    return rows


def _find_form_field(submission, field_key):
    try:
        document_id, raw_index = str(field_key or '').split(':', 1)
        index = int(raw_index)
    except (ValueError, TypeError):
        return None
    for field in _flatten_form_fields(submission):
        if field['document_id'] == document_id and field['field_index'] == index:
            return field
    return None


def _decorated_annotations(package, revision):
    resolution = {}
    for action in package.get('annotation_actions') or []:
        if not isinstance(action, dict) or action.get('action') != 'resolve':
            continue
        resolution[_text(action.get('annotation_id'))] = action

    rows = []
    for raw in package.get('annotations') or []:
        if not isinstance(raw, dict) or int(raw.get('revision', -1)) != int(revision):
            continue
        item = dict(raw)
        category = _text(item.get('category')).lower() or 'other'
        item['category_label'] = ANNOTATION_CATEGORIES.get(category, category.replace('_', ' ').title())
        if item.get('anchor_type') == 'narrative':
            item['anchor_label'] = f"Narrative line {item.get('line_number')}"
        else:
            item['anchor_label'] = f"{item.get('document_name') or 'Training form'} — {item.get('field_label') or item.get('field_name') or 'Field'}"
        resolved = resolution.get(_text(item.get('id')))
        item['resolved'] = bool(resolved)
        item['resolution_note'] = _text((resolved or {}).get('note'))
        rows.append(item)
    return rows


def _revision_diff(package, revision):
    submissions = package.get('submissions') or []
    if not submissions or int(revision) == int(submissions[0].get('revision', 0)):
        return []
    original = str(submissions[0].get('narrative') or '').splitlines()
    current = str((_submission_by_revision(package, revision) or {}).get('narrative') or '').splitlines()
    if not original:
        original = [str(submissions[0].get('narrative') or '')]
    if not current:
        current = [str((_submission_by_revision(package, revision) or {}).get('narrative') or '')]
    rows = []
    for line in difflib.ndiff(original, current):
        if line.startswith('? '):
            continue
        marker = line[:2]
        rows.append({
            'marker': marker.strip() or '·',
            'kind': 'add' if marker == '+ ' else 'remove' if marker == '- ' else 'same',
            'text': line[2:],
        })
    return rows


def _apply_fto_review(run, state, package):
    action = _text(request.form.get('fto_action')).lower()
    if action not in FTO_ACTIONS:
        return False, 'Choose a valid FTO review action.'

    comments = (request.form.get('fto_comments') or '').strip()[:5000]
    area = _text(request.form.get('remediation_area'))[:120]
    plan = (request.form.get('remediation_plan') or '').strip()[:8000]
    if action in {'correction', 'remediation'} and not comments:
        return False, 'Enter FTO comments explaining what requires follow-up.'
    if action == 'remediation' and (not area or not plan):
        return False, 'Enter the remediation area and training plan.'

    remediation_id = None
    if action == 'remediation' and run.assignment_id:
        item = FTORemediation(
            assignment_id=run.assignment_id,
            area=area,
            plan=plan,
            status='OPEN',
            created_by=current_user.id,
        )
        db.session.add(item)
        db.session.flush()
        remediation_id = item.id

    review = {
        'action': action,
        'status': FTO_ACTIONS[action],
        'reviewed_at': _utc_iso(),
        'reviewed_by': current_user.id,
        'comments': comments,
        'revision_reviewed': package.get('latest_revision'),
        'remediation_area': area if action == 'remediation' else '',
        'remediation_plan': plan if action == 'remediation' else '',
        'remediation_id': remediation_id,
    }
    history = list(package.get('review_history') or [])
    history.append(review)
    package['review_history'] = history
    package['fto_review'] = review
    package['trainee_acknowledgement'] = None
    package['status'] = FTO_ACTIONS[action]
    state['training_package'] = package
    add_timeline(
        state,
        'fto_package_review',
        f"FTO review completed: {FTO_ACTIONS[action].replace('_', ' ').title()}.",
        actor='FTO',
        channel='paperwork',
        details={
            'status': FTO_ACTIONS[action],
            'revision_reviewed': package.get('latest_revision'),
            'remediation_id': remediation_id,
        },
        visible_to_trainee=True,
    )
    persist_run(state, run.trainee_id)
    return True, {
        'accept': 'Training package accepted by the FTO.',
        'correction': 'Training package returned for correction. The original submission remains preserved.',
        'remediation': 'Remedial training assigned for human follow-up.',
    }[action]


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

    state = _merge_remote_package(state)
    scenario_id = _text(state.get('scenario_id')).upper()
    package = _package(state)
    if request.method == 'POST':
        action = _text(request.form.get('action')).lower()

        if action == 'acknowledge':
            if not package.get('fto_review'):
                flash('There is no FTO review to acknowledge yet.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
            if package.get('trainee_acknowledgement'):
                flash('This FTO review has already been acknowledged.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
            if _text(request.form.get('acknowledge_review')).lower() != 'yes':
                flash('Confirm that the FTO review was presented to you before acknowledging it.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
            acknowledgement = {
                'acknowledged_at': _utc_iso(),
                'acknowledged_by': current_user.id,
                'reviewed_revision': package.get('fto_review', {}).get('revision_reviewed'),
                'trainee_comments': (request.form.get('trainee_comments') or '').strip()[:5000],
                'meaning': 'Acknowledgement confirms review/receipt and does not indicate agreement with every finding.',
            }
            package['trainee_acknowledgement'] = acknowledgement
            state['training_package'] = package
            add_timeline(
                state,
                'trainee_review_acknowledgement',
                'Trainee acknowledged receipt/review of the FTO feedback.',
                actor='Trainee',
                channel='training_review',
                details={'revision': acknowledgement['reviewed_revision']},
                visible_to_trainee=True,
            )
            session[SESSION_KEY] = state
            session.modified = True
            persist_run(state, current_user.id)
            flash('FTO review acknowledged. Acknowledgement confirms review, not agreement.', 'success')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

        if package.get('status') == 'FTO_ACCEPTED':
            flash('This package has been accepted by the FTO and is read only.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

        if action == 'self_assess':
            latest = _latest_submission(package)
            if not latest:
                flash('Submit the training paperwork before completing the self-assessment.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
            if not latest.get('forms_complete', not bool(latest.get('selected_documents'))):
                flash('Complete the selected training-form replicas before the self-assessment.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.training_forms_page'))
            assessment = _self_assessment_from_form()
            required = (
                assessment['what_went_well'],
                assessment['what_change'],
                assessment['decision_basis'],
                assessment['notifications_considered'],
            )
            if not all(required):
                flash('Complete the required self-assessment questions before submitting.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
            package['self_assessment'] = assessment
            package['status'] = 'READY_FOR_FTO_REVIEW'
            state['training_package'] = package
            add_timeline(
                state,
                'trainee_self_assessment',
                'Trainee completed the post-call self-assessment before FTO disposition.',
                actor='Trainee',
                channel='training_review',
                details={'revision': package.get('latest_revision')},
                visible_to_trainee=True,
            )
            session[SESSION_KEY] = state
            session.modified = True
            persist_run(state, current_user.id)
            flash('Self-assessment submitted. The training package is ready for FTO review.', 'success')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

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
        package['submitted_at'] = submission['submitted_at']
        package['latest_revision'] = submission['revision']
        if action == 'revise':
            package['fto_review'] = None
            package['trainee_acknowledgement'] = None
            package['self_assessment'] = None
        package['status'] = 'FORMS_REQUIRED' if submission['selected_documents'] else 'SELF_ASSESSMENT_REQUIRED'
        state['training_package'] = package
        submission['report_analysis'] = review_training_narrative(state, submission['narrative'])
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
                'report_analysis_mode': (submission.get('report_analysis') or {}).get('mode'),
            },
            visible_to_trainee=True,
        )
        session[SESSION_KEY] = state
        session.modified = True
        persist_run(state, current_user.id)
        if submission['selected_documents']:
            flash('Paperwork selection preserved. Complete the selected synthetic training forms next.', 'success')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.training_forms_page'))
        flash('Training paperwork submitted. Complete the self-assessment before FTO disposition.', 'success')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

    latest = _latest_submission(package)
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


@bp.route('/training-forms', methods=['GET', 'POST'])
@login_required
def training_forms_page():
    state = _active_state()
    if state is None:
        flash('No active simulator training package was found.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_lab.lab'))
    if not (state.get('complete') or state.get('terminated')):
        flash('Training forms are available only after the call is cleared.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_lab.lab', scenario_id=state.get('scenario_id')))

    state = _merge_remote_package(state)
    package = _package(state)
    submission = _latest_submission(package)
    if not submission:
        flash('Select and submit the post-call paperwork before opening training forms.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))
    if package.get('status') == 'FTO_ACCEPTED':
        flash('This package has already been accepted by the FTO and is read only.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

    definitions = training_form_definitions(submission.get('selected_documents') or [])
    existing_values = existing_values_by_document(submission)

    if request.method == 'POST':
        documents, errors = parse_training_form_submission(submission.get('selected_documents') or [], request.form)
        if errors:
            for error in errors[:12]:
                flash(error, 'warning')
            return render_template(
                'scenario_training_forms.html',
                user=current_user,
                run_id=_run_id(state),
                submission=submission,
                definitions=definitions,
                existing_values=existing_values,
                read_only=False,
                back_url=url_for('reports.fto_refinements.scenario_paperwork.paperwork'),
                markup_url=None,
            )

        history = list(submission.get('training_form_history') or [])
        history.append({
            'snapshot': len(history),
            'saved_at': _utc_iso(),
            'documents': documents,
        })
        submission['training_form_history'] = history
        submission['training_forms'] = documents
        submission['forms_complete'] = True
        submission['forms_completed_at'] = _utc_iso()

        package['fto_review'] = None
        package['trainee_acknowledgement'] = None
        package['self_assessment'] = None
        package['status'] = 'SELF_ASSESSMENT_REQUIRED'
        state['training_package'] = package
        add_timeline(
            state,
            'training_forms_saved',
            'Trainee completed a preserved synthetic training-form snapshot.',
            actor='Trainee',
            channel='paperwork',
            details={
                'revision': submission.get('revision'),
                'form_snapshot': len(history) - 1,
                'documents': [item.get('document_name') for item in documents],
            },
            visible_to_trainee=True,
        )
        session[SESSION_KEY] = state
        session.modified = True
        persist_run(state, current_user.id)
        flash('Training forms saved. Earlier form snapshots remain preserved for FTO review.', 'success')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.paperwork'))

    return render_template(
        'scenario_training_forms.html',
        user=current_user,
        run_id=_run_id(state),
        submission=submission,
        definitions=definitions,
        existing_values=existing_values,
        read_only=False,
        back_url=url_for('reports.fto_refinements.scenario_paperwork.paperwork'),
        markup_url=None,
    )


@bp.get('/run/<run_id>/training-forms')
@login_required
def review_training_forms(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    evaluator_access = can_evaluator_view(current_user, run, can_manage_fn=can_manage)
    trainee_access = can_trainee_view(current_user, run)
    if not (evaluator_access or trainee_access):
        abort(403)
    state = load_run_state(run)
    package = _package(state)
    submission = _latest_submission(package)
    if not submission:
        flash('No submitted training package is available for this run.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id))
    definitions = training_form_definitions(submission.get('selected_documents') or [])
    return render_template(
        'scenario_training_forms.html',
        user=current_user,
        run_id=run.run_id,
        submission=submission,
        definitions=definitions,
        existing_values=existing_values_by_document(submission),
        read_only=True,
        back_url=url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id),
        markup_url=(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id) if evaluator_access else None),
    )


@bp.route('/run/<run_id>/markup', methods=['GET', 'POST'])
@login_required
def markup(run_id):
    run = load_run(run_id)
    if run is None:
        abort(404)
    if not can_evaluator_view(current_user, run, can_manage_fn=can_manage):
        abort(403)

    state = load_run_state(run)
    package = _package(state)
    submissions = package.get('submissions') or []
    if not submissions:
        flash('The trainee has not submitted documentation yet.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id))

    requested_revision = request.args.get('revision', type=int)
    submission = _submission_by_revision(package, requested_revision) if requested_revision is not None else submissions[-1]
    if submission is None:
        abort(404)
    revision = int(submission.get('revision', 0))
    lines = narrative_lines(submission.get('narrative'))
    form_fields = _flatten_form_fields(submission)

    if request.method == 'POST':
        action = _text(request.form.get('action')).lower()
        if action in {'annotate_narrative', 'annotate_form'}:
            comment = (request.form.get('comment') or '').strip()[:3000]
            category = _text(request.form.get('category')).lower()
            if category not in ANNOTATION_CATEGORIES:
                category = 'other'
            if not comment:
                flash('Enter an FTO comment before saving the annotation.', 'warning')
                return redirect(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id, revision=revision))

            annotation = {
                'id': secrets.token_hex(8),
                'revision': revision,
                'created_at': _utc_iso(),
                'created_by': current_user.id,
                'category': category,
                'comment': comment,
            }
            if action == 'annotate_narrative':
                line_number = request.form.get('line_number', type=int)
                line = next((item for item in lines if item['number'] == line_number), None)
                if line is None:
                    flash('Choose a valid narrative line.', 'warning')
                    return redirect(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id, revision=revision))
                annotation.update({
                    'anchor_type': 'narrative',
                    'line_number': line['number'],
                    'snapshot': line['text'],
                })
            else:
                field = _find_form_field(submission, request.form.get('field_key'))
                if field is None:
                    flash('Choose a valid training-form field.', 'warning')
                    return redirect(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id, revision=revision))
                annotation.update({
                    'anchor_type': 'form_field',
                    'document_id': field['document_id'],
                    'document_name': field['document_name'],
                    'field_index': field['field_index'],
                    'field_name': field['name'],
                    'field_label': field['label'],
                    'snapshot': field['value'],
                })

            annotations = list(package.get('annotations') or [])
            annotations.append(annotation)
            package['annotations'] = annotations
            state['training_package'] = package
            add_timeline(
                state,
                'fto_document_annotation',
                'FTO added a preserved documentation annotation.',
                actor='FTO',
                channel='training_review',
                details={'revision': revision, 'annotation_id': annotation['id'], 'anchor_type': annotation['anchor_type']},
                visible_to_trainee=True,
            )
            persist_run(state, run.trainee_id)
            flash('FTO annotation saved without changing the trainee submission.', 'success')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id, revision=revision))

        if action == 'resolve_annotation':
            annotation_id = _text(request.form.get('annotation_id'))
            exists = any(_text(item.get('id')) == annotation_id for item in package.get('annotations') or [] if isinstance(item, dict))
            if not exists:
                abort(404)
            actions = list(package.get('annotation_actions') or [])
            actions.append({
                'action': 'resolve',
                'annotation_id': annotation_id,
                'at': _utc_iso(),
                'by': current_user.id,
                'note': (request.form.get('resolution_note') or '').strip()[:1000],
            })
            package['annotation_actions'] = actions
            state['training_package'] = package
            persist_run(state, run.trainee_id)
            flash('Annotation marked resolved. The original annotation remains preserved.', 'success')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id, revision=revision))

        flash('Unknown markup action.', 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id, revision=revision))

    return render_template(
        'scenario_fto_markup.html',
        user=current_user,
        run=run,
        state=state,
        package=package,
        submission=submission,
        narrative_lines=lines,
        form_fields=form_fields,
        annotations=_decorated_annotations(package, revision),
        diff_rows=_revision_diff(package, revision),
        annotation_categories=ANNOTATION_CATEGORIES,
        package_url=url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id),
        forms_url=url_for('reports.fto_refinements.scenario_paperwork.review_training_forms', run_id=run.run_id),
        evaluator_url=url_for('reports.fto_refinements.scenario_lab.evaluator', run_id=run.run_id),
    )


@bp.route('/run/<run_id>', methods=['GET', 'POST'])
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
    latest = _latest_submission(package)

    if request.method == 'POST':
        if not evaluator_access:
            abort(403)
        if not latest:
            flash('The trainee has not submitted a training package yet.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id))
        if not latest.get('forms_complete', not bool(latest.get('selected_documents'))):
            flash('The trainee still has selected training forms to complete for this revision.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id))
        if not package.get('self_assessment'):
            flash('The trainee self-assessment is still pending. FTO disposition is locked until it is submitted.', 'warning')
            return redirect(url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id))
        ok, message = _apply_fto_review(run, state, package)
        flash(message, 'success' if ok else 'warning')
        return redirect(url_for('reports.fto_refinements.scenario_paperwork.review_paperwork', run_id=run.run_id))

    comparison = _comparison(run.scenario_id, latest) if evaluator_access and latest else None
    if evaluator_access:
        revision = int((latest or {}).get('revision', 0))
        return render_template(
            'scenario_fto_document_review.html',
            user=current_user,
            run=run,
            state=state,
            package=package,
            latest=latest,
            comparison=comparison,
            scenario=SCENARIOS.get(run.scenario_id) or {},
            scenario_id=run.scenario_id,
            annotations=_decorated_annotations(package, revision) if latest else [],
            markup_url=url_for('reports.fto_refinements.scenario_paperwork.markup', run_id=run.run_id),
            forms_url=url_for('reports.fto_refinements.scenario_paperwork.review_training_forms', run_id=run.run_id),
            notebook_url=url_for('reports.fto_refinements.scenario_notebook.review_notebook', run_id=run.run_id),
            evaluator_url=url_for('reports.fto_refinements.scenario_lab.evaluator', run_id=run.run_id),
        )

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
        evaluator_mode=False,
        comparison=None,
        run=run,
    )
