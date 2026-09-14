import json
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..fto_models import FTODailyObservation, FTOProgramAssignment, FTORemediation
from ..models import (
    AuditLog,
    ROLE_DESK_SGT,
    ROLE_FIELD_TRAINING,
    ROLE_TRAINING_MANAGER,
    ROLE_WATCH_COMMANDER,
    ROLE_WEBSITE_CONTROLLER,
    User,
)

bp = Blueprint('fto_program', __name__, url_prefix='/fto-center')

PROGRAM_WEEKS = {'standard': 8, 'accelerated': 4}
RATING_AREAS = [
    'Radio Communication',
    'Officer Safety',
    'Investigation',
    'Legal Authority',
    'Judgment / Decision Making',
    'Documentation',
    'Professionalism',
    'Policy / Procedure Awareness',
]
RATING_CHOICES = [
    (0, 'Not Observed'),
    (1, '1 — Unacceptable'),
    (2, '2 — Needs Improvement'),
    (3, '3 — Acceptable'),
    (4, '4 — Strong'),
    (5, '5 — Superior'),
]
MANAGER_ROLES = (
    ROLE_WEBSITE_CONTROLLER,
    ROLE_TRAINING_MANAGER,
    ROLE_WATCH_COMMANDER,
    ROLE_DESK_SGT,
)
EVALUATOR_ROLES = MANAGER_ROLES + (ROLE_FIELD_TRAINING,)
ACTIVE_STATUSES = ('ACTIVE', 'PAUSED', 'EXTENDED')


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _parse_date(value, fallback=None):
    raw = _text(value)
    if not raw:
        return fallback
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return fallback


def _json_dict(raw):
    try:
        value = json.loads(raw or '{}')
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def can_manage(user):
    return bool(user and getattr(user, 'is_authenticated', False) and user.has_any_role(*MANAGER_ROLES))


def can_evaluate(user):
    return bool(user and getattr(user, 'is_authenticated', False) and user.has_any_role(*EVALUATOR_ROLES))


def can_view_assignment(user, assignment):
    return can_manage(user) or user.id in {
        assignment.trainee_id,
        assignment.assigned_fto_id,
        assignment.supervisor_id,
    }


def can_evaluate_assignment(user, assignment):
    return can_manage(user) or (can_evaluate(user) and user.id == assignment.assigned_fto_id)


def can_supervise_assignment(user, assignment):
    return can_manage(user) or bool(assignment.supervisor_id and user.id == assignment.supervisor_id)


def _audit(action, detail):
    db.session.add(AuditLog(actor_id=current_user.id, action=action, details=_text(detail)[:1000]))


def _base_weeks(assignment):
    return PROGRAM_WEEKS.get((assignment.program_type or '').lower(), 8)


def _sync_progress(assignment):
    base_weeks = _base_weeks(assignment)
    if assignment.status == 'COMPLETED':
        assignment.progress_percent = 100
    elif assignment.current_week > base_weeks:
        assignment.progress_percent = 99
    else:
        assignment.progress_percent = min(99, round((max(0, assignment.current_week - 1) / base_weeks) * 100))


def _phase_label(assignment):
    base_weeks = _base_weeks(assignment)
    if assignment.current_week <= base_weeks:
        return f'Week {assignment.current_week} of {base_weeks}'
    return f'Extension Week {assignment.current_week - base_weeks}'


def _assignment_query_for(user):
    query = FTOProgramAssignment.query
    if can_manage(user):
        return query
    return query.filter(
        or_(
            FTOProgramAssignment.trainee_id == user.id,
            FTOProgramAssignment.assigned_fto_id == user.id,
            FTOProgramAssignment.supervisor_id == user.id,
        )
    )


def _candidate_lists():
    users = User.query.filter_by(active=True).order_by(User.name.asc(), User.username.asc()).all()
    ftos = [user for user in users if user.has_any_role(*EVALUATOR_ROLES)]
    supervisors = [user for user in users if user.has_any_role(*MANAGER_ROLES)]
    return users, ftos, supervisors


def _summary(assignment):
    observations = assignment.daily_observations.order_by(
        FTODailyObservation.training_date.asc(), FTODailyObservation.id.asc()
    ).all()
    finalized = [item for item in observations if item.status == 'FINALIZED']
    remediation = assignment.remediation_items.order_by(FTORemediation.created_at.desc()).all()
    open_remediation = [item for item in remediation if item.status == 'OPEN']

    series = {area: [] for area in RATING_AREAS}
    for item in finalized:
        ratings = _json_dict(item.ratings_json)
        for area in RATING_AREAS:
            try:
                score = int(ratings.get(area, 0) or 0)
            except (TypeError, ValueError):
                score = 0
            if score > 0:
                series[area].append(score)

    trends = []
    all_scores = []
    for area in RATING_AREAS:
        values = series[area]
        all_scores.extend(values)
        average = round(sum(values) / len(values), 1) if values else None
        if len(values) >= 2:
            delta = values[-1] - values[0]
            trend = 'Improving' if delta >= 1 else 'Declining' if delta <= -1 else 'Stable'
        elif values:
            trend = 'Baseline'
        else:
            trend = 'No data'
        trends.append({'area': area, 'average': average, 'trend': trend, 'observations': len(values)})

    return {
        'observations': list(reversed(observations)),
        'finalized_count': len(finalized),
        'draft_count': sum(1 for item in observations if item.status == 'DRAFT'),
        'pending_ack_count': sum(1 for item in finalized if not item.trainee_acknowledged_at),
        'pending_supervisor_review_count': sum(1 for item in finalized if not item.supervisor_reviewed_at),
        'remediation': remediation,
        'open_remediation': open_remediation,
        'trends': trends,
        'overall_average': round(sum(all_scores) / len(all_scores), 1) if all_scores else None,
        'phase_label': _phase_label(assignment),
        'base_weeks': _base_weeks(assignment),
    }


@bp.get('/programs')
@login_required
def dashboard():
    assignments = _assignment_query_for(current_user).order_by(
        FTOProgramAssignment.updated_at.desc(), FTOProgramAssignment.id.desc()
    ).limit(100).all()
    trainees = ftos = supervisors = []
    if can_manage(current_user):
        trainees, ftos, supervisors = _candidate_lists()
    return render_template(
        'fto_program_dashboard.html',
        user=current_user,
        assignments=assignments,
        can_manage_fto=can_manage(current_user),
        trainees=trainees,
        ftos=ftos,
        supervisors=supervisors,
        today=date.today(),
    )


@bp.post('/programs')
@login_required
def create_program():
    if not can_manage(current_user):
        abort(403)
    try:
        trainee_id = int(request.form.get('trainee_id') or 0)
        fto_id = int(request.form.get('assigned_fto_id') or 0)
        supervisor_id = int(request.form.get('supervisor_id') or current_user.id)
    except (TypeError, ValueError):
        trainee_id = fto_id = supervisor_id = 0

    trainee = db.session.get(User, trainee_id)
    assigned_fto = db.session.get(User, fto_id)
    supervisor = db.session.get(User, supervisor_id) if supervisor_id else None
    program_type = _text(request.form.get('program_type')).lower()
    if program_type not in PROGRAM_WEEKS:
        program_type = 'standard'

    if not trainee or not assigned_fto:
        flash('Select a valid trainee and assigned FTO.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.dashboard'))
    if trainee.id == assigned_fto.id:
        flash('The trainee and assigned FTO must be different users.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.dashboard'))
    if not assigned_fto.has_any_role(*EVALUATOR_ROLES):
        flash('The assigned evaluator must have an FTO, training, or supervisory role.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.dashboard'))
    if supervisor and not supervisor.has_any_role(*MANAGER_ROLES):
        flash('The selected supervisor is not authorized for FTO supervision.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.dashboard'))

    existing = FTOProgramAssignment.query.filter(
        FTOProgramAssignment.trainee_id == trainee.id,
        FTOProgramAssignment.status.in_(ACTIVE_STATUSES),
    ).first()
    if existing:
        flash('This trainee already has an active FTO program.', 'warning')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=existing.id))

    start_date = _parse_date(request.form.get('start_date'), date.today()) or date.today()
    weeks = PROGRAM_WEEKS[program_type]
    row = FTOProgramAssignment(
        trainee_id=trainee.id,
        assigned_fto_id=assigned_fto.id,
        supervisor_id=supervisor.id if supervisor else current_user.id,
        program_type=program_type,
        status='ACTIVE',
        current_week=1,
        progress_percent=0,
        start_date=start_date,
        expected_completion_date=start_date + timedelta(weeks=weeks),
        curriculum_json=json.dumps({
            'version': 1,
            'program_type': program_type,
            'weeks': weeks,
            'control': 'Approved MCPD FTO order/curriculum remains controlling.',
        }),
        created_by=current_user.id,
    )
    db.session.add(row)
    db.session.flush()
    _audit('fto_program_created', f'assignment={row.id}|trainee={trainee.id}|fto={assigned_fto.id}|program={program_type}')
    db.session.commit()
    flash('FTO program created.', 'success')
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=row.id))


@bp.get('/programs/<int:assignment_id>')
@login_required
def assignment(assignment_id):
    row = FTOProgramAssignment.query.get_or_404(assignment_id)
    if not can_view_assignment(current_user, row):
        abort(403)
    return render_template(
        'fto_program_assignment.html',
        user=current_user,
        assignment=row,
        summary=_summary(row),
        rating_areas=RATING_AREAS,
        rating_choices=RATING_CHOICES,
        can_evaluate=can_evaluate_assignment(current_user, row),
        can_supervise=can_supervise_assignment(current_user, row),
        can_acknowledge=current_user.id == row.trainee_id,
        today=date.today(),
    )


@bp.post('/programs/<int:assignment_id>/dor')
@login_required
def create_dor(assignment_id):
    assignment = FTOProgramAssignment.query.get_or_404(assignment_id)
    if not can_evaluate_assignment(current_user, assignment):
        abort(403)
    if assignment.status == 'COMPLETED':
        flash('Completed FTO programs are read-only.', 'warning')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))

    ratings = {}
    observed = []
    for index, area in enumerate(RATING_AREAS):
        try:
            rating = int(request.form.get(f'rating_{index}') or 0)
        except (TypeError, ValueError):
            rating = 0
        rating = max(0, min(5, rating))
        ratings[area] = rating
        if rating:
            observed.append(rating)

    status = 'FINALIZED' if _text(request.form.get('action')).lower() == 'finalize' else 'DRAFT'
    if status == 'FINALIZED' and not observed:
        flash('Rate at least one observed performance area before finalizing a DOR.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))

    dor = FTODailyObservation(
        assignment_id=assignment.id,
        evaluator_id=current_user.id,
        training_date=_parse_date(request.form.get('training_date'), date.today()) or date.today(),
        week_number=assignment.current_week,
        scenario_id=_text(request.form.get('scenario_id')) or None,
        ratings_json=json.dumps(ratings, sort_keys=True),
        overall_rating=round(sum(observed) / len(observed), 2) if observed else None,
        strengths=_text(request.form.get('strengths')) or None,
        development_areas=_text(request.form.get('development_areas')) or None,
        comments=(request.form.get('comments') or '').strip() or None,
        status=status,
        finalized_at=datetime.utcnow() if status == 'FINALIZED' else None,
    )
    db.session.add(dor)
    db.session.flush()
    _audit(
        'fto_dor_finalized' if status == 'FINALIZED' else 'fto_dor_saved',
        f'dor={dor.id}|assignment={assignment.id}|week={assignment.current_week}|evaluator={current_user.id}',
    )
    db.session.commit()
    flash('DOR finalized.' if status == 'FINALIZED' else 'DOR draft saved.', 'success')
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))


@bp.post('/dor/<int:dor_id>/supervisor-review')
@login_required
def supervisor_review(dor_id):
    dor = FTODailyObservation.query.get_or_404(dor_id)
    assignment = dor.assignment
    if not can_supervise_assignment(current_user, assignment):
        abort(403)
    if dor.status != 'FINALIZED':
        flash('Only finalized DORs can receive supervisor review.', 'warning')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
    dor.supervisor_reviewed_by = current_user.id
    dor.supervisor_reviewed_at = datetime.utcnow()
    dor.supervisor_note = _text(request.form.get('supervisor_note')) or None
    _audit('fto_dor_supervisor_reviewed', f'dor={dor.id}|assignment={assignment.id}')
    db.session.commit()
    flash('Supervisor review recorded.', 'success')
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))


@bp.post('/dor/<int:dor_id>/acknowledge')
@login_required
def acknowledge_dor(dor_id):
    dor = FTODailyObservation.query.get_or_404(dor_id)
    assignment = dor.assignment
    if current_user.id != assignment.trainee_id:
        abort(403)
    if dor.status != 'FINALIZED':
        flash('Only finalized DORs can be acknowledged.', 'warning')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
    if not dor.trainee_acknowledged_at:
        dor.trainee_acknowledged_at = datetime.utcnow()
        dor.trainee_acknowledgment_note = _text(request.form.get('acknowledgment_note')) or None
        _audit('fto_dor_acknowledged', f'dor={dor.id}|assignment={assignment.id}|trainee={current_user.id}')
        db.session.commit()
    flash('DOR acknowledgment recorded. Acknowledgment does not necessarily indicate agreement.', 'success')
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))


@bp.post('/programs/<int:assignment_id>/remediation')
@login_required
def create_remediation(assignment_id):
    assignment = FTOProgramAssignment.query.get_or_404(assignment_id)
    if not (can_evaluate_assignment(current_user, assignment) or can_supervise_assignment(current_user, assignment)):
        abort(403)
    area = _text(request.form.get('area'))
    plan = (request.form.get('plan') or '').strip()
    if not area or not plan:
        flash('Remediation area and plan are required.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
    item = FTORemediation(
        assignment_id=assignment.id,
        area=area,
        plan=plan,
        due_date=_parse_date(request.form.get('due_date')),
        status='OPEN',
        created_by=current_user.id,
    )
    db.session.add(item)
    db.session.flush()
    _audit('fto_remediation_created', f'remediation={item.id}|assignment={assignment.id}|area={area[:120]}')
    db.session.commit()
    flash('Remediation plan added.', 'success')
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))


@bp.post('/remediation/<int:remediation_id>/close')
@login_required
def close_remediation(remediation_id):
    item = FTORemediation.query.get_or_404(remediation_id)
    assignment = item.assignment
    if not (can_evaluate_assignment(current_user, assignment) or can_supervise_assignment(current_user, assignment)):
        abort(403)
    item.status = 'CLOSED'
    item.verified_by = current_user.id
    item.verified_at = datetime.utcnow()
    item.verification_note = _text(request.form.get('verification_note')) or None
    _audit('fto_remediation_closed', f'remediation={item.id}|assignment={assignment.id}')
    db.session.commit()
    flash('Remediation item closed after human verification.', 'success')
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))


@bp.post('/programs/<int:assignment_id>/advance')
@login_required
def advance_program(assignment_id):
    assignment = FTOProgramAssignment.query.get_or_404(assignment_id)
    if not can_supervise_assignment(current_user, assignment):
        abort(403)

    action = _text(request.form.get('action')).lower()
    base_weeks = _base_weeks(assignment)
    finalized_this_week = assignment.daily_observations.filter_by(
        status='FINALIZED', week_number=assignment.current_week
    ).count()
    open_remediation = assignment.remediation_items.filter_by(status='OPEN').count()

    if action == 'advance':
        if assignment.status == 'PAUSED':
            flash('Resume the program before advancing it.', 'warning')
            return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
        if finalized_this_week < 1:
            flash('A finalized DOR is required for the current week before advancement.', 'warning')
            return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
        assignment.current_week += 1
        if assignment.current_week > base_weeks:
            assignment.status = 'EXTENDED'
            assignment.extension_weeks = max(assignment.extension_weeks, assignment.current_week - base_weeks)
            if assignment.expected_completion_date:
                assignment.expected_completion_date += timedelta(days=7)
        _sync_progress(assignment)
        _audit('fto_program_advanced', f'assignment={assignment.id}|week={assignment.current_week}')
        flash('FTO program advanced by supervisory action.', 'success')

    elif action == 'extend':
        assignment.current_week = max(assignment.current_week + 1, base_weeks + 1)
        assignment.status = 'EXTENDED'
        assignment.extension_weeks = max(1, assignment.current_week - base_weeks)
        if assignment.expected_completion_date:
            assignment.expected_completion_date += timedelta(days=7)
        _sync_progress(assignment)
        _audit('fto_program_extended', f'assignment={assignment.id}|week={assignment.current_week}')
        flash('FTO program extended by supervisory action.', 'success')

    elif action == 'pause':
        assignment.status = 'PAUSED'
        _audit('fto_program_paused', f'assignment={assignment.id}|week={assignment.current_week}')
        flash('FTO program paused.', 'success')

    elif action == 'resume':
        assignment.status = 'EXTENDED' if assignment.current_week > base_weeks else 'ACTIVE'
        _audit('fto_program_resumed', f'assignment={assignment.id}|week={assignment.current_week}')
        flash('FTO program resumed.', 'success')

    elif action == 'complete':
        if assignment.current_week < base_weeks:
            flash('The program cannot be completed before the final scheduled week.', 'warning')
            return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
        if finalized_this_week < 1:
            flash('A finalized DOR is required in the current/final week before completion.', 'warning')
            return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
        if open_remediation:
            flash('Open remediation items must be resolved before program completion.', 'warning')
            return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
        assignment.status = 'COMPLETED'
        assignment.completed_at = datetime.utcnow()
        assignment.completion_recommendation = 'SUPERVISOR_COMPLETED'
        assignment.completion_note = (request.form.get('completion_note') or '').strip() or None
        _sync_progress(assignment)
        _audit('fto_program_completed', f'assignment={assignment.id}|week={assignment.current_week}')
        flash('FTO program marked complete by supervisory action.', 'success')

    else:
        flash('No valid FTO program action was selected.', 'danger')
        return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))

    db.session.commit()
    return redirect(url_for('reports.sentinel.fto_program.assignment', assignment_id=assignment.id))
