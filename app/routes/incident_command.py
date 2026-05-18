from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    AuditLog,
    BOLOEntry,
    IncidentDraft,
    IncidentPacket,
    OperationsTask,
    PACKET_APPROVAL_NEEDS_CORRECTION,
    PACKET_APPROVAL_PENDING,
    ROLE_ACCIDENT_INVESTIGATOR,
    ROLE_AID_LIEUTENANT,
    ROLE_ASSISTANT_OPERATIONS_OFFICER,
    ROLE_CVI_LIEUTENANT,
    ROLE_DESK_SGT,
    ROLE_KENNEL_MASTER,
    ROLE_K9_SERGEANT,
    ROLE_REPORT_REVIEWER,
    ROLE_SRT_COMMANDER,
    ROLE_WEBSITE_CONTROLLER,
    ROLE_WATCH_COMMANDER,
    WatchAssignment,
    WatchNote,
    WatchShift,
    utcnow_naive,
)
from ..permissions import can_manage_site, effective_role

bp = Blueprint('incident_command', __name__, url_prefix='/incident-command')

COMMAND_ROLES = {
    ROLE_WEBSITE_CONTROLLER,
    ROLE_ASSISTANT_OPERATIONS_OFFICER,
    ROLE_WATCH_COMMANDER,
    ROLE_DESK_SGT,
    ROLE_CVI_LIEUTENANT,
    ROLE_AID_LIEUTENANT,
    ROLE_SRT_COMMANDER,
    ROLE_KENNEL_MASTER,
    ROLE_K9_SERGEANT,
    ROLE_REPORT_REVIEWER,
    ROLE_ACCIDENT_INVESTIGATOR,
}
OPEN_TASK_STATUSES = {'Not Started', 'In Progress', 'Waiting on Personnel', 'Pending Review', 'Overdue'}
OFF_DUTY_STATUSES = {'Off Duty', 'Leave', 'Cancelled'}


def _can_access_incident_command(user) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return (
        effective_role(user) in COMMAND_ROLES
        or can_manage_site(user)
        or bool(getattr(user, 'builder_mode_access', False))
    )


def _require_incident_command():
    if not _can_access_incident_command(current_user):
        abort(403)


def _age_minutes(value):
    if not value:
        return 0
    return max(0, int((utcnow_naive() - value).total_seconds() // 60))


def _age_label(value):
    minutes = _age_minutes(value)
    if minutes < 1:
        return 'just now'
    if minutes < 60:
        return f'{minutes}m'
    hours = minutes // 60
    if hours < 24:
        return f'{hours}h {minutes % 60}m'
    return f'{hours // 24}d'


def _current_shift():
    return (
        WatchShift.query.filter(WatchShift.status != 'CLOSED')
        .order_by(WatchShift.created_at.desc(), WatchShift.id.desc())
        .first()
    )


def _active_assignments():
    return (
        WatchAssignment.query.filter(WatchAssignment.status.notin_(sorted(OFF_DUTY_STATUSES)))
        .order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
        .limit(120)
        .all()
    )


def _pending_packets():
    return (
        IncidentPacket.query.filter(IncidentPacket.approval_status.in_([PACKET_APPROVAL_PENDING, PACKET_APPROVAL_NEEDS_CORRECTION]))
        .order_by(IncidentPacket.submitted_at.desc())
        .limit(60)
        .all()
    )


def _open_tasks():
    return (
        OperationsTask.query.filter(OperationsTask.status.in_(sorted(OPEN_TASK_STATUSES)))
        .order_by(OperationsTask.is_overdue.desc(), OperationsTask.due_date.asc(), OperationsTask.priority.desc())
        .limit(40)
        .all()
    )


def _incident_rows(drafts, packets, bolos):
    rows = []
    for draft in drafts[:8]:
        rows.append({
            'type': 'Active Incident',
            'title': draft.call_type or 'Field incident',
            'location': draft.location or 'Location not entered',
            'status': draft.status or 'Active',
            'timer': _age_label(draft.updated_at or draft.created_at),
            'priority': 'Field Work',
            'tone': 'primary',
        })
    for packet in packets[:8]:
        tone = 'danger' if packet.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION else 'warning'
        rows.append({
            'type': 'Report Packet',
            'title': packet.call_type or 'Submitted packet',
            'location': packet.location or packet.summary or 'Awaiting review',
            'status': 'Needs Correction' if tone == 'danger' else 'Pending Review',
            'timer': _age_label(packet.submitted_at),
            'priority': 'Supervisor',
            'tone': tone,
        })
    for bolo in bolos[:4]:
        rows.append({
            'type': 'BOLO / Intel',
            'title': bolo.subject_name or 'Active BOLO',
            'location': bolo.offense or bolo.description or 'Command alert',
            'status': bolo.threat_level or bolo.status,
            'timer': _age_label(bolo.updated_at or bolo.created_at),
            'priority': 'Intel',
            'tone': 'danger' if bolo.threat_level in {'HIGH', 'ARMED'} else 'warning',
        })
    return rows[:14]


def _unit_rows(assignments):
    rows = []
    for assignment in assignments[:18]:
        officer = assignment.officer
        minutes_since_update = _age_minutes(assignment.location_updated_at or assignment.updated_at)
        rows.append({
            'name': officer.display_name if officer else 'Unassigned Unit',
            'assignment': assignment.assignment_type or 'Assignment',
            'location': assignment.assignment_location or 'Location pending',
            'status': assignment.status or 'On Duty',
            'par': 'PAR Due' if minutes_since_update >= 30 else 'PAR Current',
            'timer': f'{minutes_since_update}m',
            'notes': assignment.notes or 'No notes entered',
            'tone': 'danger' if minutes_since_update >= 45 else ('warning' if minutes_since_update >= 30 else 'success'),
        })
    return rows


def _status_counts(assignments):
    counts = {}
    for assignment in assignments:
        status = assignment.status or 'Unknown'
        counts[status] = counts.get(status, 0) + 1
    return [{'label': label, 'count': count} for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _accountability(assignments):
    total = len(assignments)
    if not total:
        return {'score': 100, 'current': 0, 'due': 0, 'stale': 0, 'total': 0}
    current = 0
    due = 0
    stale = 0
    for assignment in assignments:
        minutes = _age_minutes(assignment.location_updated_at or assignment.updated_at)
        if minutes < 30:
            current += 1
        elif minutes < 45:
            due += 1
        else:
            stale += 1
    return {
        'score': round((current / total) * 100),
        'current': current,
        'due': due,
        'stale': stale,
        'total': total,
    }


def _checklist(open_shift, assignments, incidents, packets, notes):
    checks = [
        ('Incident command established', bool(open_shift and open_shift.watch_commander_id), 'Assign or verify the IC/watch commander.'),
        ('Operational objective posted', any(note.note_type == 'incident_objective' for note in notes), 'Post the current command objective.'),
        ('Units assigned and visible', bool(assignments), 'Assign responders, posts, or staged resources.'),
        ('PAR / accountability checked', _accountability(assignments)['due'] == 0 and _accountability(assignments)['stale'] == 0, 'Run PAR for stale or due units.'),
        ('Reports / packets monitored', bool(packets) or not incidents, 'Review pending incident packets.'),
        ('Intel and BOLOs reviewed', True, 'Verify active BOLO/base order context.'),
        ('AAR notes started', any(note.note_type == 'after_action' for note in notes), 'Capture decisions and lessons learned.'),
    ]
    complete = sum(1 for _, done, _ in checks if done)
    return {
        'items_list': [{'label': label, 'done': done, 'detail': detail} for label, done, detail in checks],
        'percent': round((complete / len(checks)) * 100),
    }


def _command_log(notes, packets, tasks, bolos):
    rows = []
    for note in notes:
        rows.append({
            'time': note.created_at,
            'label': note.title,
            'detail': note.body,
            'source': note.note_type.replace('_', ' ').title(),
            'priority': note.priority,
        })
    for packet in packets[:8]:
        rows.append({
            'time': packet.submitted_at,
            'label': packet.call_type or 'Report packet',
            'detail': packet.summary or packet.location or 'Submitted for command review.',
            'source': 'Report Review',
            'priority': packet.approval_status,
        })
    for task in tasks[:8]:
        rows.append({
            'time': task.last_updated_date or task.created_date,
            'label': task.task_title,
            'detail': task.description or task.commander_notes or 'Operations tasking item.',
            'source': 'Tasking',
            'priority': task.priority,
        })
    for bolo in bolos[:6]:
        rows.append({
            'time': bolo.updated_at or bolo.created_at,
            'label': bolo.subject_name or 'BOLO',
            'detail': bolo.offense or bolo.description or 'Active BOLO/intel entry.',
            'source': 'BOLO',
            'priority': bolo.threat_level,
        })
    rows.sort(key=lambda row: row['time'] or utcnow_naive(), reverse=True)
    return rows[:18]


def _incident_start_time(open_shift, drafts, packets, notes):
    candidates = []
    if open_shift and open_shift.created_at:
        candidates.append(open_shift.created_at)
    candidates.extend([draft.created_at for draft in drafts if draft.created_at])
    candidates.extend([packet.submitted_at for packet in packets if packet.submitted_at])
    candidates.extend([note.created_at for note in notes if note.created_at])
    return min(candidates) if candidates else utcnow_naive()


def _note_exists(notes, *types):
    wanted = set(types)
    return any((note.note_type or '') in wanted for note in notes)


def _benchmark_timers(open_shift, assignments, packets, notes, incident_started_at):
    elapsed = _age_minutes(incident_started_at)
    accountability = _accountability(assignments)
    benchmark_defs = [
        {
            'label': 'IC Established',
            'due': 5,
            'done': bool(open_shift and open_shift.watch_commander_id),
            'detail': 'Confirm incident command / watch command ownership.',
        },
        {
            'label': 'Size-Up / Objective',
            'due': 10,
            'done': _note_exists(notes, 'incident_objective'),
            'detail': 'Post current objective, priorities, and known hazards.',
        },
        {
            'label': 'Perimeter / Staging',
            'due': 15,
            'done': any('perimeter' in (a.assignment_type or '').lower() or 'staging' in (a.assignment_location or '').lower() for a in assignments),
            'detail': 'Confirm traffic control, staging, and inner/outer perimeter.',
        },
        {
            'label': 'PAR Check',
            'due': 30,
            'done': accountability['due'] == 0 and accountability['stale'] == 0 and bool(assignments),
            'detail': 'Account for all assigned units and stale location updates.',
        },
        {
            'label': 'Supervisor Review',
            'due': 45,
            'done': any(packet.approval_status == PACKET_APPROVAL_PENDING for packet in packets) or _note_exists(notes, 'supervisor_notification'),
            'detail': 'Verify pending packets, supervisor notifications, and approvals.',
        },
        {
            'label': 'AAR Capture',
            'due': 60,
            'done': _note_exists(notes, 'after_action'),
            'detail': 'Begin after-action notes before details are lost.',
        },
    ]
    rows = []
    for item in benchmark_defs:
        remaining = item['due'] - elapsed
        if item['done']:
            state = 'complete'
            timer = 'Complete'
        elif remaining <= 0:
            state = 'overdue'
            timer = f'{abs(remaining)}m overdue'
        elif remaining <= 10:
            state = 'due'
            timer = f'{remaining}m left'
        else:
            state = 'pending'
            timer = f'{remaining}m left'
        rows.append({**item, 'state': state, 'timer': timer, 'elapsed': elapsed})
    return rows


def _division_board(assignments):
    divisions = [
        {
            'label': 'Command',
            'match': lambda a: (a.assignment_type or '').lower() in {'desk duty', 'watch command'} or 'command' in (a.notes or '').lower(),
            'lead': 'IC / Watch',
            'objective': 'Command, communications, notifications, and documentation.',
        },
        {
            'label': 'Operations',
            'match': lambda a: any(term in f"{a.assignment_type} {a.assignment_location}".lower() for term in ('patrol', 'response', 'special task')),
            'lead': 'Field Lead',
            'objective': 'Primary response, scene control, and officer safety.',
        },
        {
            'label': 'Perimeter / Traffic',
            'match': lambda a: any(term in f"{a.assignment_type} {a.assignment_location}".lower() for term in ('gate', 'traffic', 'perimeter', 'road', 'checkpoint')),
            'lead': 'Traffic / Gate',
            'objective': 'Access control, road closures, and traffic flow.',
        },
        {
            'label': 'Investigation',
            'match': lambda a: any(term in f"{a.assignment_type} {a.assignment_location} {a.notes}".lower() for term in ('investigation', 'follow-up', 'report', 'evidence')),
            'lead': 'Investigator',
            'objective': 'Facts, evidence, reports, photos, and witness tracking.',
        },
        {
            'label': 'Specialty / Support',
            'match': lambda a: any(term in f"{a.assignment_type} {a.assignment_location} {a.notes}".lower() for term in ('k9', 'k-9', 'srt', 'cvi', 'training', 'medical', 'staging')),
            'lead': 'Specialty Lead',
            'objective': 'Special capability, staging, medical, and mutual aid support.',
        },
    ]
    rows = []
    assigned_ids = set()
    for division in divisions:
        units = []
        for assignment in assignments:
            if assignment.id in assigned_ids:
                continue
            if division['match'](assignment):
                assigned_ids.add(assignment.id)
                units.append(assignment)
        rows.append({
            'label': division['label'],
            'lead': division['lead'],
            'objective': division['objective'],
            'count': len(units),
            'units': [
                {
                    'name': unit.officer.display_name if unit.officer else 'Unassigned',
                    'status': unit.status or 'On Duty',
                    'location': unit.assignment_location or unit.assignment_type or 'Location pending',
                }
                for unit in units[:5]
            ],
            'state': 'active' if units else 'empty',
        })
    unassigned = [assignment for assignment in assignments if assignment.id not in assigned_ids]
    if unassigned:
        rows.append({
            'label': 'Unassigned / Other',
            'lead': 'Needs Sorting',
            'objective': 'Review these units and place them into a command group.',
            'count': len(unassigned),
            'units': [
                {
                    'name': unit.officer.display_name if unit.officer else 'Unassigned',
                    'status': unit.status or 'On Duty',
                    'location': unit.assignment_location or unit.assignment_type or 'Location pending',
                }
                for unit in unassigned[:5]
            ],
            'state': 'warning',
        })
    return rows


def _risk_layers(bolos, packets, tasks, accountability):
    correction_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION]
    critical_tasks = [task for task in tasks if task.is_overdue or task.priority == 'Command Critical']
    armed_or_high = [bolo for bolo in bolos if bolo.threat_level in {'HIGH', 'ARMED'}]
    return [
        {
            'label': 'Officer Safety / BOLO',
            'value': len(armed_or_high),
            'tone': 'danger' if armed_or_high else 'success',
            'detail': 'High-risk BOLOs and command safety alerts.',
        },
        {
            'label': 'Accountability Risk',
            'value': accountability['due'] + accountability['stale'],
            'tone': 'danger' if accountability['stale'] else ('warning' if accountability['due'] else 'success'),
            'detail': 'Units needing PAR or stale location review.',
        },
        {
            'label': 'Report / Packet Risk',
            'value': len(correction_packets),
            'tone': 'warning' if correction_packets else 'success',
            'detail': 'Packets returned or requiring immediate command review.',
        },
        {
            'label': 'Tasking Risk',
            'value': len(critical_tasks),
            'tone': 'danger' if critical_tasks else 'success',
            'detail': 'Overdue or command-critical due-outs tied to readiness.',
        },
    ]


def _tactical_worksheet(assignments, incidents, bolos, packets, tasks):
    resource_gaps = []
    if not assignments:
        resource_gaps.append('No assigned response resources are visible.')
    if not any('staging' in (a.assignment_location or '').lower() for a in assignments):
        resource_gaps.append('Staging location is not documented.')
    if not any('traffic' in f"{a.assignment_type} {a.assignment_location}".lower() for a in assignments):
        resource_gaps.append('Traffic/perimeter control is not specifically assigned.')
    hazards = []
    hazards.extend([bolo.offense or bolo.description or bolo.subject_name for bolo in bolos[:3]])
    if any(packet.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION for packet in packets):
        hazards.append('One or more packets need correction before final review.')
    notifications = [
        'Watch Commander / Desk Sgt',
        'Dispatch / PMO Desk',
        'CID/AID or Accident Investigator if case facts require',
        'Fire/EMS or installation emergency services if safety conditions change',
    ]
    return {
        'priorities': [
            'Life safety and officer accountability',
            'Scene stabilization and perimeter control',
            'Evidence preservation and report/documentation capture',
        ],
        'hazards': hazards or ['No high-risk BOLO or packet hazard is currently visible.'],
        'resource_gaps': resource_gaps or ['No immediate resource gap detected from visible assignments.'],
        'notifications': notifications,
        'active_task_count': len(tasks),
        'active_incident_count': len(incidents),
    }


def _command_actions():
    return [
        {'label': 'Live Unit Map', 'detail': 'Open GPS/status map', 'endpoint': 'watch_commander.unit_map'},
        {'label': 'Assign Units', 'detail': 'Update shift resources', 'endpoint': 'watch_commander.officers'},
        {'label': 'Review Reports', 'detail': 'Open pending packets', 'endpoint': 'watch_commander.reports'},
        {'label': 'BOLO / Intel', 'detail': 'Review active alerts', 'endpoint': 'bolo.bolo_board'},
        {'label': 'Bodycam Library', 'detail': 'Review video/transcripts', 'endpoint': 'bodycam.library'},
        {'label': 'Assistant Ops', 'detail': 'Create follow-up tasking', 'endpoint': 'assistant_operations.dashboard'},
        {'label': 'Accident Tools', 'detail': 'Open crash diagram/reconstruction', 'endpoint': 'reports.accidents'},
        {'label': 'Shift Brief', 'detail': 'Publish command brief', 'endpoint': 'watch_commander.briefing'},
    ]


@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    _require_incident_command()
    open_shift = _current_shift()
    assignments = _active_assignments()
    packets = _pending_packets()
    drafts = IncidentDraft.query.filter_by(status='ACTIVE').order_by(IncidentDraft.updated_at.desc()).limit(24).all()
    bolos = BOLOEntry.query.filter_by(status='ACTIVE').order_by(BOLOEntry.updated_at.desc()).limit(12).all()
    tasks = _open_tasks()
    notes = (
        WatchNote.query.order_by(WatchNote.created_at.desc(), WatchNote.id.desc())
        .limit(30)
        .all()
    )
    incidents = _incident_rows(drafts, packets, bolos)
    units = _unit_rows(assignments)
    accountability = _accountability(assignments)
    checklist = _checklist(open_shift, assignments, incidents, packets, notes)
    incident_started_at = _incident_start_time(open_shift, drafts, packets, notes)
    overdue_tasks = [task for task in tasks if task.is_overdue or task.priority == 'Command Critical']
    metrics = [
        {'label': 'Active Incidents', 'value': len(incidents), 'detail': 'Drafts, pending packets, and BOLOs', 'tone': 'primary'},
        {'label': 'Assigned Units', 'value': len(assignments), 'detail': 'On-duty resources in the operating picture', 'tone': 'success'},
        {'label': 'Accountability', 'value': f"{accountability['score']}%", 'detail': f"{accountability['due'] + accountability['stale']} PAR checks due/stale", 'tone': 'danger' if accountability['stale'] else ('warning' if accountability['due'] else 'success')},
        {'label': 'Critical Tasking', 'value': len(overdue_tasks), 'detail': 'Overdue or command-critical items', 'tone': 'danger' if overdue_tasks else 'success'},
    ]
    return render_template(
        'incident_command/dashboard.html',
        title='Incident Command',
        user=current_user,
        open_shift=open_shift,
        metrics=metrics,
        incidents=incidents,
        units=units,
        status_counts=_status_counts(assignments),
        accountability=accountability,
        checklist=checklist,
        command_log=_command_log(notes, packets, tasks, bolos),
        benchmark_timers=_benchmark_timers(open_shift, assignments, packets, notes, incident_started_at),
        divisions=_division_board(assignments),
        risk_layers=_risk_layers(bolos, packets, tasks, accountability),
        worksheet=_tactical_worksheet(assignments, incidents, bolos, packets, tasks),
        command_actions=_command_actions(),
        tasks=tasks[:10],
        suggested_objectives=[
            'Stabilize scene, account for all personnel, and establish perimeter.',
            'Assign primary response, traffic control, investigator, and staging resources.',
            'Document decisions, evidence/media, safety hazards, and supervisor notifications.',
        ],
        next_par_due=utcnow_naive() + timedelta(minutes=30),
    )


@bp.post('/log')
@login_required
def add_log():
    _require_incident_command()
    title = (request.form.get('title') or '').strip()[:180]
    body = (request.form.get('body') or '').strip()
    note_type = (request.form.get('note_type') or 'incident_command').strip()[:60]
    priority = (request.form.get('priority') or 'Normal').strip()[:20]
    if not title or not body:
        flash('Add a title and command log note before saving.', 'error')
        return redirect(url_for('incident_command.dashboard'))
    shift = _current_shift()
    db.session.add(WatchNote(
        shift_id=shift.id if shift else None,
        created_by=current_user.id,
        note_type=note_type,
        title=title,
        body=body,
        priority=priority,
    ))
    db.session.add(AuditLog(
        actor_id=current_user.id,
        action='incident_command_log_added',
        details=f'{note_type}: {title}',
    ))
    db.session.commit()
    flash('Incident command log entry saved.', 'success')
    return redirect(url_for('incident_command.dashboard'))
