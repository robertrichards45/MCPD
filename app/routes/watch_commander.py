from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    AuditLog,
    BOLOEntry,
    Form,
    IncidentDraft,
    IncidentPacket,
    PACKET_APPROVAL_APPROVED,
    PACKET_APPROVAL_NEEDS_CORRECTION,
    PACKET_APPROVAL_PENDING,
    ROLE_DESK_SGT,
    ROLE_PATROL_OFFICER,
    ROLE_WATCH_COMMANDER,
    SavedForm,
    ShiftBrief,
    ShiftBriefAcknowledgement,
    TrainingRoster,
    TrainingSignature,
    User,
    WatchApproval,
    WatchAssignment,
    WatchNote,
    WatchShift,
    utcnow_naive,
)
from ..permissions import can_manage_site, effective_role

bp = Blueprint('watch_commander', __name__, url_prefix='/watch-commander')

OFFICER_STATUSES = ['On Duty', 'Patrol', 'Gate', 'Report Writing', 'Training', 'Meal', 'Off Duty', 'Leave']
ASSIGNMENT_TYPES = ['Patrol Zone', 'Gate Post', 'Desk Duty', 'Training Duty', 'Report Follow-Up', 'Special Task', 'RAM / Security Check']


def _can_access_watch_tools(user) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return (
        effective_role(user) in {ROLE_WATCH_COMMANDER, 'WEBSITE_CONTROLLER'}
        or can_manage_site(user)
        or bool(getattr(user, 'builder_mode_access', False))
    )


def _require_watch_tools():
    if not _can_access_watch_tools(current_user):
        abort(403)


def _audit(action: str, details: str = '') -> None:
    db.session.add(AuditLog(actor_id=current_user.id, action=action, details=details[:2000]))


def _officers():
    return (
        User.query.filter(User.active.is_(True))
        .order_by(User.last_name.asc(), User.first_name.asc(), User.username.asc())
        .all()
    )


def _latest_assignment(officer_id: int):
    return (
        WatchAssignment.query.filter_by(officer_id=officer_id)
        .order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
        .first()
    )


def _dashboard_context():
    officers = _officers()
    packets = IncidentPacket.query.order_by(IncidentPacket.submitted_at.desc()).limit(80).all()
    saved_forms = SavedForm.query.order_by(SavedForm.updated_at.desc()).limit(80).all()
    rosters = TrainingRoster.query.order_by(TrainingRoster.uploaded_at.desc()).limit(40).all()
    open_shift = WatchShift.query.filter(WatchShift.status != 'CLOSED').order_by(WatchShift.created_at.desc()).first()
    pending_approvals = WatchApproval.query.filter_by(status='PENDING').count()
    shift_notes = WatchNote.query.order_by(WatchNote.created_at.desc()).limit(8).all()
    return {
        'officers': officers,
        'open_shift': open_shift,
        'packets': packets,
        'saved_forms': saved_forms,
        'rosters': rosters,
        'shift_notes': shift_notes,
        'summary': {
            'officers_on_duty': WatchAssignment.query.filter(WatchAssignment.status.in_(['On Duty', 'Patrol', 'Gate', 'Report Writing', 'Training'])).count(),
            'reports_pending': sum(1 for p in packets if p.approval_status == PACKET_APPROVAL_PENDING),
            'saved_forms_pending': sum(1 for f in saved_forms if str(f.status or '').upper() in {'DRAFT', 'SUBMITTED', 'PENDING'}),
            'training_pending': sum(1 for r in rosters if str(r.status or '').upper() == 'ACTIVE'),
            'open_incidents': IncidentDraft.query.filter_by(status='ACTIVE').count(),
            'shift_notes': len(shift_notes),
            'pending_approvals': pending_approvals,
        },
        'mobile_cards': [
            ('Shift Status', 'watch_commander.shift'),
            ('Officers', 'watch_commander.officers'),
            ('Pending Reviews', 'watch_commander.reports'),
            ('Training', 'watch_commander.training'),
            ('Blotter', 'watch_commander.blotter'),
            ('Approvals', 'watch_commander.approvals'),
            ('Briefing', 'watch_commander.briefing'),
        ],
    }


@bp.route('/')
@bp.route('')
@login_required
def index():
    return redirect(url_for('watch_commander.dashboard'))


@bp.route('/dashboard')
@login_required
def dashboard():
    _require_watch_tools()
    return render_template('watch_commander/dashboard.html', title='Watch Commander Dashboard', user=current_user, **_dashboard_context())


@bp.route('/shift', methods=['GET', 'POST'])
@login_required
def shift():
    _require_watch_tools()
    if request.method == 'POST':
        shift_id = request.form.get('shift_id', type=int)
        item = db.session.get(WatchShift, shift_id) if shift_id else WatchShift()
        item.shift_date = (request.form.get('shift_date') or date.today().isoformat()).strip()
        item.shift_type = (request.form.get('shift_type') or 'Alpha').strip()
        item.watch_commander_id = current_user.id
        item.desk_sergeant_id = request.form.get('desk_sergeant_id', type=int)
        item.start_time = (request.form.get('start_time') or '').strip()
        item.end_time = (request.form.get('end_time') or '').strip()
        item.notes = (request.form.get('notes') or '').strip()
        item.status = (request.form.get('status') or 'OPEN').strip().upper()
        db.session.add(item)
        _audit('watch_shift_saved', f'shift_id={item.id or "new"}|status={item.status}')
        db.session.flush()

        assigned_officer_ids = set()
        if request.form.get('assign_self'):
            assigned_officer_ids.add(current_user.id)
        for raw_id in request.form.getlist('assigned_officer_ids'):
            try:
                assigned_officer_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

        assignment_type = (request.form.get('assignment_type') or 'Patrol Zone').strip()
        assignment_location = (request.form.get('assignment_location') or '').strip()
        assignment_status = (request.form.get('assignment_status') or 'On Duty').strip()
        for officer_id in assigned_officer_ids:
            officer = db.session.get(User, officer_id)
            if not officer or not officer.active:
                continue
            assignment = (
                WatchAssignment.query.filter_by(shift_id=item.id, officer_id=officer.id)
                .order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
                .first()
            ) or WatchAssignment(shift_id=item.id, officer_id=officer.id)
            assignment.assignment_type = assignment_type
            assignment.assignment_location = assignment_location
            assignment.status = assignment_status
            assignment.start_time = item.start_time
            assignment.end_time = item.end_time
            assignment.notes = (request.form.get('assignment_notes') or '').strip()
            db.session.add(assignment)
            _audit('watch_assignment_changed', f'officer_id={officer.id}|shift_id={item.id}|assignment={assignment.assignment_type}|status={assignment.status}')

        db.session.commit()
        flash('Shift saved and assignments updated.' if assigned_officer_ids else 'Shift saved.', 'success')
        return redirect(url_for('watch_commander.shift'))
    shifts = WatchShift.query.order_by(WatchShift.shift_date.desc(), WatchShift.created_at.desc()).limit(30).all()
    return render_template(
        'watch_commander/shift.html',
        title='Shift Management',
        user=current_user,
        shifts=shifts,
        officers=_officers(),
        statuses=OFFICER_STATUSES,
        assignment_types=ASSIGNMENT_TYPES,
    )


@bp.route('/officers', methods=['GET', 'POST'])
@login_required
def officers():
    _require_watch_tools()
    if request.method == 'POST':
        officer_id = request.form.get('officer_id', type=int)
        officer = db.session.get(User, officer_id)
        if not officer:
            abort(404)
        assignment = _latest_assignment(officer.id) or WatchAssignment(officer_id=officer.id)
        shift_id = request.form.get('shift_id', type=int)
        assignment.shift_id = shift_id
        assignment.assignment_type = (request.form.get('assignment_type') or 'Patrol Zone').strip()
        assignment.assignment_location = (request.form.get('assignment_location') or '').strip()
        assignment.status = (request.form.get('status') or 'On Duty').strip()
        assignment.start_time = (request.form.get('start_time') or '').strip()
        assignment.end_time = (request.form.get('end_time') or '').strip()
        assignment.notes = (request.form.get('notes') or '').strip()
        db.session.add(assignment)
        _audit('watch_assignment_changed', f'officer_id={officer.id}|assignment={assignment.assignment_type}|status={assignment.status}')
        db.session.commit()
        flash('Officer assignment updated.', 'success')
        return redirect(url_for('watch_commander.officers'))
    rows = []
    for officer in _officers():
        rows.append({
            'officer': officer,
            'assignment': _latest_assignment(officer.id),
            'saved_count': SavedForm.query.filter_by(officer_user_id=officer.id).count(),
            'draft_count': IncidentDraft.query.filter_by(officer_user_id=officer.id, status='ACTIVE').count(),
            'pending_corrections': IncidentPacket.query.filter_by(officer_user_id=officer.id, approval_status=PACKET_APPROVAL_NEEDS_CORRECTION).count(),
        })
    shifts = WatchShift.query.filter(WatchShift.status != 'CLOSED').order_by(WatchShift.created_at.desc()).all()
    return render_template('watch_commander/officers.html', title='Officer Status Board', user=current_user, rows=rows, shifts=shifts, statuses=OFFICER_STATUSES, assignment_types=ASSIGNMENT_TYPES)


@bp.route('/reports')
@login_required
def reports():
    _require_watch_tools()
    packets = IncidentPacket.query.order_by(IncidentPacket.submitted_at.desc()).limit(120).all()
    return render_template('watch_commander/reports.html', title='Report Review', user=current_user, packets=packets, pending=PACKET_APPROVAL_PENDING, approved=PACKET_APPROVAL_APPROVED, correction=PACKET_APPROVAL_NEEDS_CORRECTION)


@bp.route('/reports/<int:packet_id>/<action>', methods=['POST'])
@login_required
def report_action(packet_id, action):
    _require_watch_tools()
    packet = IncidentPacket.query.get_or_404(packet_id)
    notes = (request.form.get('notes') or '').strip()[:2000]
    if action == 'approve':
        packet.approval_status = PACKET_APPROVAL_APPROVED
        audit_action = 'watch_report_approved'
    elif action == 'return':
        packet.approval_status = PACKET_APPROVAL_NEEDS_CORRECTION
        audit_action = 'watch_report_returned'
    else:
        abort(404)
    packet.reviewer_user_id = current_user.id
    packet.reviewed_at = utcnow_naive()
    if notes:
        packet.supervisor_notes = notes
    _audit(audit_action, f'packet_id={packet.id}|officer_id={packet.officer_user_id}|notes={notes}')
    db.session.commit()
    flash('Report review updated.', 'success')
    return redirect(url_for('watch_commander.reports'))


@bp.route('/saved-work')
@login_required
def saved_work():
    _require_watch_tools()
    items = SavedForm.query.order_by(SavedForm.updated_at.desc()).limit(150).all()
    return render_template('watch_commander/saved_work.html', title='Saved Work Review', user=current_user, items=items)


@bp.route('/training')
@login_required
def training():
    _require_watch_tools()
    rosters = TrainingRoster.query.order_by(TrainingRoster.uploaded_at.desc()).limit(100).all()
    signed_counts = {r.id: TrainingSignature.query.filter_by(roster_id=r.id).count() for r in rosters}
    return render_template('watch_commander/training.html', title='Training Oversight', user=current_user, rosters=rosters, signed_counts=signed_counts)


@bp.route('/forms')
@login_required
def forms():
    _require_watch_tools()
    forms = Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).limit(120).all()
    saved = SavedForm.query.order_by(SavedForm.updated_at.desc()).limit(80).all()
    return render_template('watch_commander/forms.html', title='Forms Oversight', user=current_user, forms=forms, saved=saved)


@bp.route('/blotter', methods=['GET', 'POST'])
@login_required
def blotter():
    _require_watch_tools()
    if request.method == 'POST':
        note = WatchNote(
            shift_id=request.form.get('shift_id', type=int),
            created_by=current_user.id,
            note_type=(request.form.get('note_type') or 'shift_note').strip(),
            title=(request.form.get('title') or 'Watch Commander Note').strip(),
            body=(request.form.get('body') or '').strip(),
            priority=(request.form.get('priority') or 'Normal').strip(),
        )
        if not note.body:
            flash('Note body is required.', 'error')
            return redirect(url_for('watch_commander.blotter'))
        db.session.add(note)
        _audit('watch_note_created', f'note_type={note.note_type}|title={note.title}')
        db.session.commit()
        flash('Watch note created.', 'success')
        return redirect(url_for('watch_commander.blotter'))
    notes = WatchNote.query.order_by(WatchNote.created_at.desc()).limit(100).all()
    shifts = WatchShift.query.order_by(WatchShift.created_at.desc()).limit(20).all()
    return render_template('watch_commander/blotter.html', title='Blotter / Journal Review', user=current_user, notes=notes, shifts=shifts)


@bp.route('/approvals', methods=['GET', 'POST'])
@login_required
def approvals():
    _require_watch_tools()
    if request.method == 'POST':
        approval_id = request.form.get('approval_id', type=int)
        item = WatchApproval.query.get_or_404(approval_id)
        action = (request.form.get('action') or '').upper()
        if action in {'APPROVED', 'RETURNED', 'REJECTED', 'NEEDS_CORRECTION'}:
            item.status = action
            item.reviewed_by = current_user.id
            item.comments = (request.form.get('comments') or '').strip()
            _audit('watch_approval_updated', f'approval_id={item.id}|status={item.status}|target={item.target_type}:{item.target_id}')
            db.session.commit()
            flash('Approval updated.', 'success')
        return redirect(url_for('watch_commander.approvals'))
    queues = {
        'Reports pending review': IncidentPacket.query.filter_by(approval_status=PACKET_APPROVAL_PENDING).all(),
        'Forms pending review': SavedForm.query.filter(SavedForm.status.in_(['SUBMITTED', 'PENDING', 'DRAFT'])).limit(40).all(),
        'Narrative examples pending approval': WatchApproval.query.filter_by(target_type='learning', status='PENDING').all(),
        'Accident diagrams pending review': WatchApproval.query.filter_by(target_type='accident_diagram', status='PENDING').all(),
        'Officer assignment requests': WatchApproval.query.filter_by(target_type='assignment', status='PENDING').all(),
    }
    approvals = WatchApproval.query.order_by(WatchApproval.created_at.desc()).limit(100).all()
    return render_template('watch_commander/approvals.html', title='Approvals Center', user=current_user, queues=queues, approvals=approvals)


@bp.route('/assignments')
@login_required
def assignments():
    _require_watch_tools()
    assignments = WatchAssignment.query.order_by(WatchAssignment.updated_at.desc()).limit(150).all()
    return render_template('watch_commander/assignments.html', title='Assignments', user=current_user, assignments=assignments, statuses=OFFICER_STATUSES)


@bp.route('/briefing', methods=['GET', 'POST'])
@login_required
def briefing():
    _require_watch_tools()
    if request.method == 'POST':
        brief = ShiftBrief(
            shift_id=request.form.get('shift_id', type=int),
            created_by=current_user.id,
            title=(request.form.get('title') or 'Shift Brief').strip(),
            body=(request.form.get('body') or '').strip(),
            status=(request.form.get('status') or 'DRAFT').strip().upper(),
        )
        if not brief.body:
            flash('Brief body is required.', 'error')
            return redirect(url_for('watch_commander.briefing'))
        db.session.add(brief)
        _audit('shift_brief_created', f'title={brief.title}|status={brief.status}')
        db.session.commit()
        flash('Shift brief saved.', 'success')
        return redirect(url_for('watch_commander.briefing'))
    briefs = ShiftBrief.query.order_by(ShiftBrief.created_at.desc()).limit(50).all()
    shifts = WatchShift.query.order_by(WatchShift.created_at.desc()).limit(20).all()
    bolos = BOLOEntry.query.filter_by(status='ACTIVE').limit(10).all()
    notes = WatchNote.query.order_by(WatchNote.created_at.desc()).limit(10).all()
    return render_template('watch_commander/briefing.html', title='Shift Briefing', user=current_user, briefs=briefs, shifts=shifts, bolos=bolos, notes=notes)


@bp.route('/briefing/<int:brief_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_brief(brief_id):
    brief = ShiftBrief.query.get_or_404(brief_id)
    exists = ShiftBriefAcknowledgement.query.filter_by(brief_id=brief.id, officer_id=current_user.id).first()
    if not exists:
        db.session.add(ShiftBriefAcknowledgement(brief_id=brief.id, officer_id=current_user.id))
        db.session.commit()
    flash('Brief acknowledged.', 'success')
    return redirect(url_for('watch_commander.briefing'))


@bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    _require_watch_tools()
    if request.method == 'POST':
        note = WatchNote(
            created_by=current_user.id,
            note_type=(request.form.get('note_type') or 'general_notice').strip(),
            title=(request.form.get('subject') or 'Watch Notification').strip(),
            body=(request.form.get('message') or '').strip(),
            priority=(request.form.get('priority') or 'Normal').strip(),
        )
        db.session.add(note)
        _audit('watch_notification_sent', f'type={note.note_type}|priority={note.priority}|title={note.title}')
        db.session.commit()
        flash('Notification saved.', 'success')
        return redirect(url_for('watch_commander.notifications'))
    notes = WatchNote.query.order_by(WatchNote.created_at.desc()).limit(60).all()
    return render_template('watch_commander/notifications.html', title='Notifications', user=current_user, notes=notes, officers=_officers())
