import json
from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    AuditLog,
    BaseBuilding,
    BOLOEntry,
    Form,
    INSTALLATION_LABELS,
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
from ..models import ROLE_ASSISTANT_OPERATIONS_OFFICER
from ..permissions import can_manage_site, effective_role

bp = Blueprint('watch_commander', __name__, url_prefix='/watch-commander')

OFFICER_STATUSES = ['On Duty', 'Patrol', 'Gate', 'Report Writing', 'Training', 'Meal', 'Off Duty', 'Leave']

# Known MCLB Albany locations mapped to coordinates for demo/location-name fallback
_MCLB_LOCATIONS = {
    'main gate': (31.5709, -84.0765),
    'gate 1': (31.5709, -84.0765),
    'gate 2': (31.5760, -84.0700),
    'industrial': (31.5760, -84.0700),
    'gate 3': (31.5800, -84.0690),
    'north gate': (31.5800, -84.0690),
    'pmo': (31.5748, -84.0730),
    'provost': (31.5748, -84.0730),
    'police': (31.5748, -84.0730),
    'hq': (31.5770, -84.0640),
    'headquarters': (31.5770, -84.0640),
    'mcx': (31.5730, -84.0590),
    'exchange': (31.5730, -84.0590),
    'chapel': (31.5720, -84.0650),
    'logistics': (31.5795, -84.0580),
    'patrol zone a': (31.5735, -84.0670),
    'zone a': (31.5735, -84.0670),
    'patrol zone b': (31.5768, -84.0615),
    'zone b': (31.5768, -84.0615),
    'patrol zone c': (31.5752, -84.0740),
    'zone c': (31.5752, -84.0740),
    'desk': (31.5748, -84.0730),
    'dispatch': (31.5748, -84.0730),
}

# Demo scatter positions (lat, lng jitter) for units without a mapped location
_DEMO_SCATTER = [
    (31.5722, -84.0720), (31.5741, -84.0658), (31.5779, -84.0702),
    (31.5762, -84.0645), (31.5715, -84.0600), (31.5793, -84.0648),
    (31.5731, -84.0637), (31.5755, -84.0718),
]

# Roles that appear as units on the operational map
_MAP_ROLES = {ROLE_PATROL_OFFICER, ROLE_DESK_SGT, ROLE_WATCH_COMMANDER}
_OFF_DUTY_STATUSES = {'Off Duty', 'Leave'}

# Roles that can VIEW the unit map (broadened from watch tools)
_MAP_VIEWER_ROLES = {
    ROLE_WATCH_COMMANDER,
    ROLE_DESK_SGT,
    ROLE_ASSISTANT_OPERATIONS_OFFICER,
    'WEBSITE_CONTROLLER',
}


def _can_access_unit_map(user) -> bool:
    """Unit map is visible to command-level roles and site controllers."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return (
        effective_role(user) in _MAP_VIEWER_ROLES
        or can_manage_site(user)
        or bool(getattr(user, 'builder_mode_access', False))
    )


def _unit_map_supervisor_filter(viewer):
    """
    Returns the supervisor_id to scope unit queries, or None meaning 'see all'.

    WEBSITE_CONTROLLER + ASSISTANT_OPERATIONS_OFFICER → None (see everyone)
    WATCH_COMMANDER + DESK_SGT → viewer.id (see their direct reports only)
    """
    role = effective_role(viewer)
    if role in {ROLE_WEBSITE_CONTROLLER, ROLE_ASSISTANT_OPERATIONS_OFFICER} or can_manage_site(viewer):
        return None
    return viewer.id


def _resolve_location(assignment, idx: int):
    """Return (lat, lng) for a WatchAssignment; prefers stored coords, falls back to location name."""
    if assignment.unit_lat and assignment.unit_lng:
        return (assignment.unit_lat, assignment.unit_lng)
    loc = (assignment.assignment_location or '').lower().strip()
    for key, coords in _MCLB_LOCATIONS.items():
        if key in loc:
            return coords
    return _DEMO_SCATTER[idx % len(_DEMO_SCATTER)]


def _status_color(status: str) -> str:
    mapping = {
        'Patrol': '#22c55e',
        'On Duty': '#22c55e',
        'Gate': '#06b6d4',
        'Report Writing': '#3b82f6',
        'Training': '#a855f7',
        'Meal': '#f59e0b',
        'Off Duty': '#6b7280',
        'Leave': '#6b7280',
    }
    return mapping.get(status, '#94a3b8')
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


@bp.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    _require_watch_tools()
    if request.method == 'POST':
        officer_id = request.form.get('officer_id', type=int)
        officer = db.session.get(User, officer_id)
        if not officer or not officer.active:
            abort(404)
        shift_id = request.form.get('shift_id', type=int)
        assignment = (
            WatchAssignment.query.filter_by(shift_id=shift_id, officer_id=officer.id).first()
            if shift_id else None
        ) or WatchAssignment(officer_id=officer.id)
        assignment.shift_id = shift_id
        assignment.assignment_type = (request.form.get('assignment_type') or 'Patrol Zone').strip()
        assignment.assignment_location = (request.form.get('assignment_location') or '').strip()
        assignment.status = (request.form.get('status') or 'On Duty').strip()
        assignment.start_time = (request.form.get('start_time') or '').strip()
        assignment.end_time = (request.form.get('end_time') or '').strip()
        assignment.notes = (request.form.get('notes') or '').strip()
        db.session.add(assignment)
        _audit('watch_assignment_changed', f'officer_id={officer.id}|shift_id={shift_id or ""}|assignment={assignment.assignment_type}|status={assignment.status}')
        db.session.commit()
        flash('Assignment saved.', 'success')
        return redirect(url_for('watch_commander.assignments'))
    assignments = WatchAssignment.query.order_by(WatchAssignment.updated_at.desc()).limit(150).all()
    shifts = WatchShift.query.filter(WatchShift.status != 'CLOSED').order_by(WatchShift.created_at.desc()).all()
    return render_template('watch_commander/assignments.html', title='Assignments', user=current_user, assignments=assignments, officers=_officers(), shifts=shifts, statuses=OFFICER_STATUSES, assignment_types=ASSIGNMENT_TYPES)


@bp.route('/personnel')
@login_required
def personnel():
    _require_watch_tools()
    return redirect(url_for('auth.manage_users'))


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


# ── Unit Operational Map ───────────────────────────────────────────────────

@bp.route('/unit-map')
@login_required
def unit_map():
    if not _can_access_unit_map(current_user):
        abort(403)
    scope_id = _unit_map_supervisor_filter(current_user)
    can_see_all = scope_id is None
    return render_template(
        'watch_commander/unit_map.html',
        title='Unit Map',
        user=current_user,
        statuses=OFFICER_STATUSES,
        can_see_all=can_see_all,
    )


_DEMO_STATUSES = ['Patrol', 'On Duty', 'Gate', 'Report Writing', 'On Duty', 'Patrol', 'Training', 'Meal']


@bp.route('/api/units')
@login_required
def api_units():
    if not _can_access_unit_map(current_user):
        abort(403)
    scope_id = _unit_map_supervisor_filter(current_user)
    is_demo = bool(session.get('demo_mode'))

    # Build filtered user list based on viewer scope
    q = User.query.filter(User.active.is_(True), User.role.in_(_MAP_ROLES))
    if scope_id is not None:
        q = q.filter(User.supervisor_id == scope_id)
    active_users = q.order_by(User.last_name.asc(), User.first_name.asc()).all()

    # In demo mode, show all active officers even without assignments
    units = []
    for idx, officer in enumerate(active_users):
        assignment = (
            WatchAssignment.query
            .filter_by(officer_id=officer.id)
            .order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
            .first()
        )
        if assignment:
            status = assignment.status
        elif is_demo:
            status = _DEMO_STATUSES[idx % len(_DEMO_STATUSES)]
        else:
            status = 'Off Duty'
        if status in _OFF_DUTY_STATUSES:
            continue
        lat, lng = _resolve_location(assignment, idx) if assignment else _DEMO_SCATTER[idx % len(_DEMO_SCATTER)]
        units.append({
            'id': officer.id,
            'name': officer.display_name,
            'badge': officer.badge_employee_id or officer.officer_number or '',
            'role': getattr(officer, 'role_label', officer.role),
            'status': status,
            'color': _status_color(status),
            'location': (assignment.assignment_location or INSTALLATION_LABELS.get(officer.installation, 'MCLB Albany')) if assignment else 'MCLB Albany',
            'assignment_type': assignment.assignment_type if assignment else '',
            'lat': lat,
            'lng': lng,
            'location_fresh': bool(assignment and assignment.unit_lat),
        })
    return jsonify({'units': units, 'scope': 'all' if scope_id is None else 'supervised'})


@bp.route('/api/units/<int:officer_id>/status', methods=['POST'])
@login_required
def api_update_unit_status(officer_id):
    if not _can_access_unit_map(current_user):
        abort(403)
    new_status = (request.json or {}).get('status', '').strip()
    if new_status not in OFFICER_STATUSES:
        return jsonify({'error': 'Invalid status'}), 400
    officer = User.query.get_or_404(officer_id)
    # Scoped commanders can only update their own officers
    scope_id = _unit_map_supervisor_filter(current_user)
    if scope_id is not None and officer.supervisor_id != scope_id:
        return jsonify({'error': 'Not in your scope'}), 403
    assignment = (
        WatchAssignment.query
        .filter_by(officer_id=officer.id)
        .order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
        .first()
    )
    if not assignment:
        assignment = WatchAssignment(officer_id=officer.id, assignment_type='Patrol')
        db.session.add(assignment)
    assignment.status = new_status
    _audit('unit_status_changed', f'officer_id={officer.id}|status={new_status}')
    db.session.commit()
    return jsonify({'ok': True, 'status': new_status, 'color': _status_color(new_status)})


@bp.route('/api/unit-location', methods=['POST'])
@login_required
def api_update_unit_location():
    """Officer self-reports their GPS location from their device."""
    data = request.json or {}
    lat = data.get('lat')
    lng = data.get('lng')
    if not lat or not lng:
        return jsonify({'error': 'lat/lng required'}), 400
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid coordinates'}), 400
    assignment = (
        WatchAssignment.query
        .filter_by(officer_id=current_user.id)
        .order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
        .first()
    )
    if not assignment:
        assignment = WatchAssignment(officer_id=current_user.id, assignment_type='Patrol')
        db.session.add(assignment)
    assignment.unit_lat = lat
    assignment.unit_lng = lng
    assignment.location_updated_at = utcnow_naive()
    db.session.commit()
    return jsonify({'ok': True})


# ── Shift Sign-On / Sign-Off ───────────────────────────────────────────────

@bp.route('/sign-on', methods=['GET', 'POST'])
@login_required
def sign_on():
    """Any authenticated officer can check in to start their shift."""
    existing = (
        WatchAssignment.query
        .filter_by(officer_id=current_user.id)
        .order_by(WatchAssignment.updated_at.desc())
        .first()
    )
    is_on_duty = bool(existing and existing.status not in _OFF_DUTY_STATUSES)

    if request.method == 'POST':
        action = request.form.get('action', 'sign_on')

        if action == 'sign_off':
            if existing:
                existing.status = 'Off Duty'
                existing.updated_at = utcnow_naive()
                db.session.commit()
                _audit('shift_sign_off', 'self')
            flash('Shift ended. Stay safe out there.', 'success')
            return redirect(url_for('dashboard.dashboard'))

        location = (request.form.get('location') or '').strip()
        atype = (request.form.get('assignment_type') or ASSIGNMENT_TYPES[0]).strip()
        if atype not in ASSIGNMENT_TYPES:
            atype = ASSIGNMENT_TYPES[0]

        if existing:
            existing.status = 'On Duty'
            if location:
                existing.assignment_location = location
            existing.assignment_type = atype
            existing.updated_at = utcnow_naive()
        else:
            existing = WatchAssignment(
                officer_id=current_user.id,
                assignment_type=atype,
                assignment_location=location,
                status='On Duty',
            )
            db.session.add(existing)
        db.session.commit()
        _audit('shift_sign_on', f'type={atype}|location={location}')
        flash('Shift started. You are now visible on the unit map.', 'success')
        return redirect(url_for('dashboard.dashboard'))

    wcs = [u for u in User.query.filter(User.active.is_(True)).all()
           if getattr(u, 'has_role', lambda r: False)(ROLE_WATCH_COMMANDER)]

    return render_template(
        'watch_commander/sign_on.html',
        title='Shift Check-In',
        user=current_user,
        assignment=existing,
        is_on_duty=is_on_duty,
        assignment_types=ASSIGNMENT_TYPES,
        locations=sorted(_MCLB_LOCATIONS.keys()),
    )


# ── Close Shift (WC / Desk Sgt) ───────────────────────────────────────────

@bp.route('/api/close-shift', methods=['POST'])
@login_required
def api_close_shift():
    """Mark all on-duty units (in scope) as Off Duty for shift handoff."""
    if not _can_access_unit_map(current_user):
        abort(403)
    scope_id = _unit_map_supervisor_filter(current_user)

    q = (
        WatchAssignment.query
        .join(User, WatchAssignment.officer_id == User.id)
        .filter(
            User.active.is_(True),
            User.role.in_(_MAP_ROLES),
            WatchAssignment.status.notin_(list(_OFF_DUTY_STATUSES)),
        )
    )
    if scope_id is not None:
        q = q.filter(User.supervisor_id == scope_id)

    count = 0
    for a in q.all():
        a.status = 'Off Duty'
        a.updated_at = utcnow_naive()
        count += 1
    db.session.commit()
    _audit('close_shift', f'count={count}|scope={scope_id}')
    return jsonify({'ok': True, 'closed': count})


# ── Building Pin Management API ───────────────────────────────────────────────

@bp.route('/api/buildings', methods=['GET'])
@login_required
def api_buildings_list():
    if not _can_access_unit_map(current_user):
        abort(403)
    buildings = BaseBuilding.query.order_by(BaseBuilding.number).all()
    return jsonify([{
        'id': b.id,
        'number': b.number,
        'name': b.name or '',
        'lat': b.lat,
        'lng': b.lng,
        'category': b.category or '',
        'notes': b.notes or '',
    } for b in buildings])


@bp.route('/api/buildings', methods=['POST'])
@login_required
def api_buildings_create():
    if not _can_access_unit_map(current_user):
        abort(403)
    data = request.get_json(silent=True) or {}
    number = (data.get('number') or '').strip()
    lat = data.get('lat')
    lng = data.get('lng')
    if not number or lat is None or lng is None:
        return jsonify({'error': 'number, lat, and lng are required'}), 400
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return jsonify({'error': 'lat and lng must be numbers'}), 400
    b = BaseBuilding(
        number=number,
        name=(data.get('name') or '').strip() or None,
        lat=lat,
        lng=lng,
        category=(data.get('category') or '').strip() or None,
        notes=(data.get('notes') or '').strip() or None,
    )
    db.session.add(b)
    db.session.commit()
    return jsonify({'id': b.id, 'number': b.number, 'lat': b.lat, 'lng': b.lng}), 201


@bp.route('/api/buildings/<int:building_id>', methods=['PUT'])
@login_required
def api_buildings_update(building_id):
    if not _can_access_unit_map(current_user):
        abort(403)
    b = BaseBuilding.query.get_or_404(building_id)
    data = request.get_json(silent=True) or {}
    if 'number' in data:
        b.number = (data['number'] or '').strip() or b.number
    if 'name' in data:
        b.name = (data['name'] or '').strip() or None
    if 'lat' in data:
        try:
            b.lat = float(data['lat'])
        except (TypeError, ValueError):
            return jsonify({'error': 'lat must be a number'}), 400
    if 'lng' in data:
        try:
            b.lng = float(data['lng'])
        except (TypeError, ValueError):
            return jsonify({'error': 'lng must be a number'}), 400
    if 'category' in data:
        b.category = (data['category'] or '').strip() or None
    if 'notes' in data:
        b.notes = (data['notes'] or '').strip() or None
    b.updated_at = utcnow_naive()
    db.session.commit()
    return jsonify({'ok': True, 'id': b.id})


@bp.route('/api/buildings/<int:building_id>', methods=['DELETE'])
@login_required
def api_buildings_delete(building_id):
    if not _can_access_unit_map(current_user):
        abort(403)
    b = BaseBuilding.query.get_or_404(building_id)
    db.session.delete(b)
    db.session.commit()
    return jsonify({'ok': True})

