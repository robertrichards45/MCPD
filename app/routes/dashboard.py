import json
import logging
from datetime import datetime

from flask import Blueprint, flash, render_template, redirect, url_for, make_response, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (
    Announcement,
    CleoReport,
    BOLOEntry,
    IncidentDraft,
    IncidentPacket,
    PACKET_APPROVAL_APPROVED,
    PACKET_APPROVAL_NEEDS_CORRECTION,
    PACKET_APPROVAL_PENDING,
    Report,
    ROLE_WATCH_COMMANDER,
    SavedForm,
    TrainingRoster,
    WatchAssignment,
    WatchApproval,
    WatchNote,
    WatchShift,
)
from ..permissions import can_access_assistant_operations, can_access_builder_mode
from .incident_command import _can_access_incident_command

bp = Blueprint('dashboard', __name__)
_log = logging.getLogger(__name__)

DEFAULT_DASHBOARD_CARD_IDS = [
    'law_lookup',
    'start_report',
    'dispatch_command_center',
    'incident_command',
    'forms_library',
    'orders_memos',
    'training',
    'saved_work',
    'accident_tools',
    'bodycam_mode',
    'bodycam_footage',
    'narrative_creator',
    'five_w_builder',
]

DEFAULT_DASHBOARD_PANEL_IDS = ['recent_reports', 'training_rosters', 'saved_work']


def _is_test_report_title(title: str) -> bool:
    return str(title or '').strip().lower().startswith(('stress report', 'test report ', 'mock stress report'))


def _production_report_query():
    return Report.query.filter(
        ~Report.title.ilike('Stress Report%'),
        ~Report.title.ilike('Test Report %'),
        ~Report.title.ilike('Mock Stress Report%'),
    )


def _request_prefers_mobile_home() -> bool:
    user_agent = str(getattr(request, 'user_agent', '') or '')
    blob = ' '.join(
        [
            user_agent,
            str(request.headers.get('User-Agent', '') or ''),
            str(request.headers.get('Sec-CH-UA-Mobile', '') or ''),
        ]
    ).lower()
    return any(token in blob for token in ('iphone', 'android', 'mobile', 'ipad'))


def _no_store_response(rendered):
    response = make_response(rendered)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _visible_announcements_query():
    scopes = {'ALL', current_user.normalized_role}
    if current_user.has_role(ROLE_WATCH_COMMANDER):
        scopes.add(ROLE_WATCH_COMMANDER)
    return Announcement.query.filter(
        Announcement.is_active.is_(True),
        Announcement.scope.in_(sorted(scopes)),
    )


def _safe_count(label, query):
    try:
        return query.count()
    except Exception as exc:
        db.session.rollback()
        _log.warning('Dashboard count failed for %s: %s', label, exc.__class__.__name__)
        return 0


def _safe_recent_announcements(query):
    try:
        return query.order_by(Announcement.created_at.desc(), Announcement.id.desc()).limit(3).all()
    except Exception as exc:
        db.session.rollback()
        _log.warning('Dashboard announcements failed: %s', exc.__class__.__name__)
        return []


def _dashboard_snapshot():
    visible_announcements = _visible_announcements_query()
    saved_forms_count = _safe_count('saved_forms', SavedForm.query.filter_by(officer_user_id=current_user.id))
    report_count = _safe_count('reports', _production_report_query().filter_by(owner_id=current_user.id))
    cleo_report_count = _safe_count('cleo_reports', CleoReport.query.filter_by(user_id=current_user.id))
    # Kept in the snapshot for template compatibility, but no longer counted on
    # every dashboard load because these values are not displayed by the page.
    orders_count = 0
    training_count = 0
    notice_count = _safe_count('announcements', visible_announcements)

    metrics = [
        {
            'label': 'Saved Forms',
            'value': saved_forms_count,
            'detail': 'Resume form drafts without digging through menus.',
        },
        {
            'label': 'Reports',
            'value': report_count,
            'detail': 'Case writeups and report shells tied to your account.',
        },
        {
            'label': 'Report Drafts',
            'value': cleo_report_count,
            'detail': 'Draft packets and review work still in motion.',
        },
        {
            'label': 'Live Notices',
            'value': notice_count,
            'detail': 'Command updates visible to your current scope.',
        },
    ]

    return {
        'metrics': metrics,
        'saved_forms_count': saved_forms_count,
        'report_count': report_count,
        'cleo_report_count': cleo_report_count,
        'orders_count': orders_count,
        'training_count': training_count,
        'notice_count': notice_count,
        'announcements': _safe_recent_announcements(visible_announcements),
        'readiness_items': _dashboard_readiness_items(
            saved_forms_count=saved_forms_count,
            report_count=report_count,
            cleo_report_count=cleo_report_count,
            notice_count=notice_count,
        ),
        'queue_items': _dashboard_queue_items(
            saved_forms_count=saved_forms_count,
            report_count=report_count,
            cleo_report_count=cleo_report_count,
            notice_count=notice_count,
        ),
        'live_ops': _dashboard_live_ops(
            saved_forms_count=saved_forms_count,
            report_count=report_count,
            notice_count=notice_count,
        ),
    }


def _safe_all(label, query, limit=None):
    try:
        if limit:
            query = query.limit(limit)
        return query.all()
    except Exception as exc:
        db.session.rollback()
        _log.warning('Dashboard query failed for %s: %s', label, exc.__class__.__name__)
        return []


def _safe_first(label, query):
    try:
        return query.first()
    except Exception as exc:
        db.session.rollback()
        _log.warning('Dashboard first failed for %s: %s', label, exc.__class__.__name__)
        return None


def _dashboard_live_ops(saved_forms_count, report_count, notice_count):
    """Build a First Due-style operating picture while respecting officer scope."""
    is_command = bool(current_user.can_manage_team())
    if is_command:
        drafts_query = IncidentDraft.query.filter_by(status='ACTIVE').order_by(IncidentDraft.updated_at.desc())
        packets_query = IncidentPacket.query.order_by(IncidentPacket.submitted_at.desc())
        assignments_query = WatchAssignment.query.order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())
    else:
        drafts_query = IncidentDraft.query.filter_by(officer_user_id=current_user.id, status='ACTIVE').order_by(IncidentDraft.updated_at.desc())
        packets_query = IncidentPacket.query.filter_by(officer_user_id=current_user.id).order_by(IncidentPacket.submitted_at.desc())
        assignments_query = WatchAssignment.query.filter_by(officer_id=current_user.id).order_by(WatchAssignment.updated_at.desc(), WatchAssignment.id.desc())

    drafts = _safe_all('live_ops_drafts', drafts_query, 8)
    packets = _safe_all('live_ops_packets', packets_query, 12)
    assignments = _safe_all('live_ops_assignments', assignments_query, 12)
    open_shift = _safe_first(
        'live_ops_shift',
        WatchShift.query.filter(WatchShift.status != 'CLOSED').order_by(WatchShift.created_at.desc()),
    ) if is_command else None
    active_bolos = _safe_all(
        'live_ops_bolos',
        BOLOEntry.query.filter_by(status='ACTIVE').order_by(BOLOEntry.created_at.desc()),
        4,
    ) if is_command else []
    active_rosters = _safe_count(
        'live_ops_training',
        TrainingRoster.query.filter(TrainingRoster.status.ilike('ACTIVE')),
    ) if is_command else 0
    pending_approvals = _safe_count('live_ops_approvals', WatchApproval.query.filter_by(status='PENDING')) if is_command else 0
    shift_notes = _safe_all('live_ops_shift_notes', WatchNote.query.order_by(WatchNote.created_at.desc()), 4) if is_command else []

    pending_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_PENDING]
    correction_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION]
    approved_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_APPROVED]

    feed = []
    for draft in drafts[:4]:
        feed.append({
            'type': 'Active Incident Draft',
            'label': draft.call_type or 'Incident draft',
            'location': draft.location or draft.summary or 'No location entered',
            'status': draft.status,
            'tone': 'primary',
            'endpoint': 'reports.list_reports',
        })
    for packet in pending_packets[:4]:
        feed.append({
            'type': 'Report Packet',
            'label': packet.call_type or 'Submitted packet',
            'location': packet.location or packet.summary or 'Supervisor review required',
            'status': 'Pending Review',
            'tone': 'warning',
            'endpoint': 'watch_commander.reports' if is_command else 'reports.list_reports',
        })
    for packet in correction_packets[:3]:
        feed.append({
            'type': 'Correction Needed',
            'label': packet.call_type or 'Returned packet',
            'location': packet.location or packet.supervisor_notes or 'Corrections requested',
            'status': 'Needs Correction',
            'tone': 'danger',
            'endpoint': 'reports.list_reports',
        })
    for bolo in active_bolos[:3]:
        feed.append({
            'type': 'BOLO / Alert',
            'label': bolo.subject_name or 'Active BOLO',
            'location': bolo.offense or bolo.description or 'Command alert',
            'status': bolo.threat_level or bolo.status,
            'tone': 'danger',
            'endpoint': 'bolo.bolo_board',
        })
    for note in shift_notes[:2]:
        feed.append({
            'type': note.note_type.replace('_', ' ').title(),
            'label': note.title,
            'location': note.body[:120],
            'status': note.priority,
            'tone': 'primary',
            'endpoint': 'watch_commander.blotter',
        })

    unit_rows = []
    for assignment in assignments[:8]:
        officer = getattr(assignment, 'officer', None)
        unit_rows.append({
            'name': officer.display_name if officer else current_user.display_name,
            'assignment': assignment.assignment_location or assignment.assignment_type or 'Assignment pending',
            'status': assignment.status or 'On Duty',
            'detail': assignment.notes or assignment.assignment_type or 'No notes',
            'tone': 'success' if (assignment.status or '').lower() in {'patrol', 'on duty', 'gate'} else 'primary',
        })
    if not unit_rows:
        unit_rows.append({
            'name': current_user.display_name,
            'assignment': current_user.section_unit or 'No current assignment entered',
            'status': 'Available' if not is_command else 'No visible units',
            'detail': 'Use Watch Commander shift tools to assign units.',
            'tone': 'primary',
        })

    total_packets = len(packets)
    alert_tiles = [
        {
            'label': 'Active Incidents',
            'value': len(drafts),
            'detail': 'Open drafts / active field work',
            'tone': 'primary',
            'endpoint': 'reports.list_reports',
        },
        {
            'label': 'Pending Review',
            'value': len(pending_packets),
            'detail': 'Packets waiting on supervisor action',
            'tone': 'warning' if pending_packets else 'success',
            'endpoint': 'watch_commander.reports' if is_command else 'reports.list_reports',
        },
        {
            'label': 'Corrections',
            'value': len(correction_packets),
            'detail': 'Returned report packets',
            'tone': 'danger' if correction_packets else 'success',
            'endpoint': 'reports.list_reports',
        },
        {
            'label': 'Command Alerts',
            'value': len(active_bolos) if is_command else notice_count,
            'detail': 'BOLOs / notices needing awareness',
            'tone': 'danger' if active_bolos else 'primary',
            'endpoint': 'bolo.bolo_board' if is_command else 'announcements.board',
        },
    ]

    analytics = [
        {
            'label': 'Report Clearance',
            'value': f'{round((len(approved_packets) / total_packets) * 100) if total_packets else 100}%',
            'detail': f'{len(approved_packets)} approved / {total_packets} recent packets',
        },
        {
            'label': 'Unit Visibility',
            'value': len(assignments),
            'detail': 'Assignments visible in current operating picture',
        },
        {
            'label': 'Saved Work Backlog',
            'value': saved_forms_count,
            'detail': 'Saved forms, drafts, and unfinished packets',
        },
        {
            'label': 'Training / Approvals',
            'value': active_rosters + pending_approvals if is_command else report_count,
            'detail': 'Command oversight items' if is_command else 'Your report workload',
        },
    ]

    preplan_layers = [
        {
            'label': 'Installation Map',
            'detail': 'MCLB Albany map, base points, and full-screen view.',
            'endpoint': 'dashboard.dashboard',
        },
        {
            'label': 'Unit / Assignment Layer',
            'detail': 'Officer status, patrol zones, gates, posts, and GPS-capable unit map.',
            'endpoint': 'watch_commander.unit_map' if is_command else 'mobile.home',
        },
        {
            'label': 'Incident / BOLO Layer',
            'detail': 'Active drafts, submitted packets, alerts, and command notes.',
            'endpoint': 'watch_commander.dashboard' if is_command else 'announcements.board',
        },
        {
            'label': 'Reports / Media Layer',
            'detail': 'Reports, bodycam footage, accident diagrams, and saved evidence photos.',
            'endpoint': 'reports.list_reports',
        },
    ]

    return {
        'is_command': is_command,
        'open_shift_label': f'{open_shift.shift_type} / {open_shift.status}' if open_shift else ('No open shift' if is_command else current_user.section_unit or 'Field view'),
        'alert_tiles': alert_tiles,
        'feed': feed[:10],
        'unit_rows': unit_rows,
        'analytics': analytics,
        'preplan_layers': preplan_layers,
    }


def _dashboard_card_catalog():
    cards = [
        {
            'id': 'law_lookup',
            'label': 'Law Lookup',
            'description': 'Search laws, UCMJ, and base orders',
            'icon': 'law',
            'endpoint': 'legal.legal_home',
        },
        {
            'id': 'start_report',
            'label': 'Start New Report',
            'description': 'Create an incident report or blotter',
            'icon': 'report',
            'endpoint': 'reports.new_report',
        },
        {
            'id': 'dispatch_command_center',
            'label': 'Dispatch / Command Center',
            'description': 'Live shift, unit status, active incidents, and radio-style command view',
            'icon': 'orders',
            'endpoint': 'dashboard.dispatch_command_center',
        },
        {
            'id': 'forms_library',
            'label': 'Forms Library',
            'description': 'Fill out, save, and manage forms',
            'icon': 'forms',
            'endpoint': 'forms.list_forms',
        },
        {
            'id': 'orders_memos',
            'label': 'Orders & Memos',
            'description': 'Search orders, memos, and references',
            'icon': 'orders',
            'endpoint': 'orders.reference_search',
        },
        {
            'id': 'training',
            'label': 'Training',
            'description': 'Rosters, sign-in, and qualifications',
            'icon': 'training',
            'endpoint': 'training.training_menu',
        },
        {
            'id': 'saved_work',
            'label': 'Saved Work',
            'description': 'Saved forms, drafts, and packets',
            'icon': 'saved',
            'endpoint': 'forms.saved_forms',
        },
        {
            'id': 'accident_tools',
            'label': 'Accident Tools',
            'description': 'Officer diagrams and investigator reconstruction',
            'icon': 'report',
            'endpoint': 'reports.accidents',
        },
        {
            'id': 'bodycam_mode',
            'label': 'Body Cam Mode',
            'description': 'Record video with transcript support',
            'icon': 'report',
            'endpoint': 'bodycam.new_recording',
        },
        {
            'id': 'bodycam_footage',
            'label': 'Bodycam Footage',
            'description': 'Review saved recordings and transcripts',
            'icon': 'saved',
            'endpoint': 'bodycam.library',
        },
        {
            'id': 'narrative_creator',
            'label': 'Narrative Creator',
            'description': 'Turn report facts into a draft narrative',
            'icon': 'forms',
            'endpoint': 'bodycam.narrative_tool',
        },
        {
            'id': 'five_w_builder',
            'label': '5W Builder',
            'description': 'Paste one notes block and extract the 5Ws',
            'icon': 'forms',
            'endpoint': 'bodycam.five_w_tool',
        },
        {
            'id': 'mobile_field_view',
            'label': 'Mobile Field View',
            'description': 'Open the phone/tablet field dashboard',
            'icon': 'training',
            'endpoint': 'mobile.home',
        },
    ]
    if _can_access_incident_command(current_user):
        cards.append({
            'id': 'incident_command',
            'label': 'Incident Command',
            'description': 'IC board, PAR/accountability, command log, and AAR snapshot',
            'icon': 'orders',
            'endpoint': 'incident_command.dashboard',
        })
    if can_access_builder_mode(current_user):
        cards.append({
            'id': 'site_builder',
            'label': 'Site Builder',
            'description': 'Owner-approved change request console',
            'icon': 'orders',
            'endpoint': 'admin.site_builder',
        })
    if current_user.can_manage_team():
        cards.extend([
            {
                'id': 'assistant_operations_tracker',
                'label': 'Assistant Ops Tracker',
                'description': 'Due-outs, training, inspections, and projects',
                'icon': 'orders',
                'endpoint': 'assistant_operations.dashboard',
            },
            {
                'id': 'watch_commander_hub',
                'label': 'Watch Commander Hub',
                'description': 'Shift, reports, approvals, officers, and briefing',
                'icon': 'orders',
                'endpoint': 'watch_commander.dashboard',
            },
            {
                'id': 'approve_assign_officers',
                'label': 'Approve / Assign Officers',
                'description': 'Activate accounts, edit roles, and assign watch',
                'icon': 'training',
                'endpoint': 'auth.manage_users',
            },
            {
                'id': 'stats_approvals',
                'label': 'Stats Approvals',
                'description': 'Approve officer stats and performance entries',
                'icon': 'report',
                'endpoint': 'performance.pending',
            },
            {
                'id': 'readiness_tracker',
                'label': 'Readiness Tracker',
                'description': 'Monitor team qualifications and expirations',
                'icon': 'training',
                'endpoint': 'qual_tracker.tracker_readiness',
            },
        ])
    elif can_access_assistant_operations(current_user):
        cards.extend([
            {
                'id': 'assistant_operations_tracker',
                'label': 'Assistant Ops Tracker',
                'description': 'Due-outs, training, inspections, and projects',
                'icon': 'orders',
                'endpoint': 'assistant_operations.dashboard',
            },
        ])
    return cards


def _dashboard_panel_catalog(snapshot):
    return [
        {
            'id': 'recent_reports',
            'title': 'Recent Reports',
            'view_all_endpoint': 'reports.list_reports',
            'items': [
                {'label': 'Reports Center', 'detail': snapshot['metrics'][0]['detail'] if snapshot['metrics'] else 'Open reports and packets', 'endpoint': 'reports.list_reports'},
                {'label': 'Bodycam Footage', 'detail': 'Recordings and transcripts', 'endpoint': 'bodycam.library'},
                {'label': 'Narrative Creator', 'detail': 'Standalone report writing tool', 'endpoint': 'bodycam.narrative_tool'},
                {'label': '5W Builder', 'detail': 'Who, what, when, where, and why summary', 'endpoint': 'bodycam.five_w_tool'},
                {'label': 'Accident Reconstruction', 'detail': 'Scene diagrams and crash reports', 'endpoint': 'reports.accident_reconstruction_list'},
            ],
        },
        {
            'id': 'training_rosters',
            'title': 'Training Rosters',
            'view_all_endpoint': 'training.training_menu',
            'items': [
                {'label': 'Training Center', 'detail': 'Assigned rosters and sign-offs', 'endpoint': 'training.training_menu'},
                {'label': 'Qualifications', 'detail': 'Personal qualification tracker', 'endpoint': 'qual_tracker.tracker_personal'},
                {'label': 'Officer Stats', 'detail': 'Performance and elements', 'endpoint': 'performance.my_stats'},
            ],
        },
        {
            'id': 'saved_work',
            'title': 'Saved Work',
            'view_all_endpoint': 'forms.saved_forms',
            'items': [
                {'label': 'Saved Forms', 'detail': f"{snapshot['saved_forms_count']} item{'' if snapshot['saved_forms_count'] == 1 else 's'}", 'endpoint': 'forms.saved_forms'},
                {'label': 'My Profile', 'detail': 'Contact info and emergency contacts', 'endpoint': 'officers.profile'},
                {'label': 'Command Notices', 'detail': 'Assigned notices and updates', 'endpoint': 'announcements.board'},
            ],
        },
        {
            'id': 'command_activity',
            'title': 'Command Activity',
            'view_all_endpoint': 'watch_commander.dashboard',
            'supervisor_only': True,
            'items': [
                {'label': 'Dispatch / Command Center', 'detail': 'Live units, active incidents, and radio-style operational view', 'endpoint': 'dashboard.dispatch_command_center'},
                {'label': 'Watch Commander Hub', 'detail': 'Shift supervision dashboard', 'endpoint': 'watch_commander.dashboard'},
                {'label': 'Assistant Ops Tracker', 'detail': 'Due-outs, training, inspections, and projects', 'endpoint': 'assistant_operations.dashboard'},
                {'label': 'Approvals Center', 'detail': 'Review pending supervisor actions', 'endpoint': 'watch_commander.approvals'},
                {'label': 'Shift Management', 'detail': 'Create shifts and assign officers', 'endpoint': 'watch_commander.shift'},
            ],
        },
    ]


def _dashboard_readiness_items(saved_forms_count, report_count, cleo_report_count, notice_count):
    items = [
        {
            'label': 'Field Reporting',
            'status': 'Operational',
            'value': report_count,
            'unit': 'active reports',
            'detail': 'Officer reports, packets, accident tools, and narrative support are online.',
            'tone': 'success',
            'endpoint': 'reports.list_reports',
        },
        {
            'label': 'Forms & Packets',
            'status': 'Ready',
            'value': saved_forms_count,
            'unit': 'saved items',
            'detail': 'PDF-backed forms, saved work, preview, download, and packet workflows.',
            'tone': 'primary',
            'endpoint': 'forms.list_forms',
        },
        {
            'label': 'Law / Orders Reference',
            'status': 'AI Assisted',
            'value': 'Live',
            'unit': 'reference search',
            'detail': 'Plain-language law lookup, orders, memorandums, and source review.',
            'tone': 'success',
            'endpoint': 'legal.legal_home',
        },
        {
            'label': 'Training & Readiness',
            'status': 'Monitor',
            'value': 'Roster',
            'unit': 'tracking',
            'detail': 'Training rosters, qualification tracking, signatures, and reminders.',
            'tone': 'warning',
            'endpoint': 'training.training_menu',
        },
    ]
    if current_user.can_manage_team():
        items.extend([
            {
                'label': 'Watch Command',
                'status': 'Supervisor',
                'value': notice_count,
                'unit': 'live notices',
                'detail': 'Shift supervision, assignments, approvals, briefing, and officer status.',
                'tone': 'primary',
                'endpoint': 'watch_commander.dashboard',
            },
            {
                'label': 'Command Tasking',
                'status': 'Tracked',
                'value': cleo_report_count,
                'unit': 'draft/review items',
                'detail': 'Assistant Ops due-outs, inspections, projects, and completion tracking.',
                'tone': 'success',
                'endpoint': 'assistant_operations.dashboard',
            },
        ])
    return items


def _dashboard_queue_items(saved_forms_count, report_count, cleo_report_count, notice_count):
    queues = [
        {
            'label': 'My Reports',
            'value': report_count,
            'detail': 'Open report center',
            'endpoint': 'reports.list_reports',
        },
        {
            'label': 'Saved Work',
            'value': saved_forms_count,
            'detail': 'Resume forms and packets',
            'endpoint': 'forms.saved_forms',
        },
        {
            'label': 'Notices',
            'value': notice_count,
            'detail': 'Command updates',
            'endpoint': 'announcements.board',
        },
    ]
    if current_user.can_manage_team():
        queues.extend([
            {
                'label': 'WC Reviews',
                'value': 'Open',
                'detail': 'Reports, forms, approvals',
                'endpoint': 'watch_commander.approvals',
            },
            {
                'label': 'Task Tracker',
                'value': 'Ops',
                'detail': 'Due-outs and projects',
                'endpoint': 'assistant_operations.dashboard',
            },
        ])
    else:
        queues.append({
            'label': 'Draft Packets',
            'value': cleo_report_count,
            'detail': 'Narrative and report drafts',
            'endpoint': 'reports.list_reports',
        })
    return queues


def _dispatch_demo_context():
    now = datetime.now().strftime('%H%M')
    dispatch_summary = {
        'current_time': now,
        'shift_name': 'Alpha Shift Command Net',
        'shift_status': 'Demo operational picture — sample data only',
    }
    dispatch_metrics = [
        {'label': 'Units Available', 'value': '7', 'detail': 'Patrol / K-9 / CVI sample availability'},
        {'label': 'Active Incidents', 'value': '3', 'detail': 'Open calls visible to command'},
        {'label': 'Pending Reports', 'value': '5', 'detail': 'Awaiting supervisor review'},
        {'label': 'Training Alerts', 'value': '4', 'detail': 'Due or overdue acknowledgements'},
        {'label': 'BOLOs', 'value': '2', 'detail': 'Active command notices'},
        {'label': 'Approvals', 'value': '6', 'detail': 'Reports, stats, and tasking'},
    ]
    unit_status = [
        {'name': 'Patrol 1', 'assignment': 'Main Gate / Radford Blvd', 'status': 'Available', 'state_class': ''},
        {'name': 'Patrol 2', 'assignment': 'Barracks parking lot larceny follow-up', 'status': 'On Call', 'state_class': 'busy'},
        {'name': 'Desk Sgt', 'assignment': 'Report review queue', 'status': 'Monitoring', 'state_class': ''},
        {'name': 'K-9 1', 'assignment': 'Available for sweep request', 'status': 'Ready', 'state_class': ''},
        {'name': 'CVI 1', 'assignment': 'Commercial vehicle inspection lane', 'status': 'Busy', 'state_class': 'busy'},
        {'name': 'SRT Element', 'assignment': 'Training readiness status', 'status': 'Standby', 'state_class': ''},
    ]
    active_incidents = [
        {'title': 'Larceny Report', 'detail': 'Barracks parking lot / report packet pending', 'priority': 'Routine', 'state_class': 'busy'},
        {'title': 'Gate Access Issue', 'detail': 'Main Gate DBIDS verification request', 'priority': 'Monitor', 'state_class': ''},
        {'title': 'BOLO Acknowledgement', 'detail': 'Two officers pending review acknowledgement', 'priority': 'Action', 'state_class': 'alert'},
    ]
    radio_summary = 'Alpha Net: Patrol 2 handling larceny follow-up. Desk Sgt monitoring packet queue. K-9 and SRT remain available. Command Center view is sample data only; verify all operational facts before action.'
    return {
        'dispatch_summary': dispatch_summary,
        'dispatch_metrics': dispatch_metrics,
        'unit_status': unit_status,
        'active_incidents': active_incidents,
        'radio_summary': radio_summary,
        'dispatch_mode_label': 'DEMO DATA',
        'dispatch_workflow_cards': _dispatch_workflow_cards(is_command=True),
        'dispatch_preplan_layers': _dispatch_preplan_layers(is_command=True),
    }


def _dispatch_workflow_cards(is_command):
    """Shortcut cards for a First Due-style command workflow."""
    if is_command:
        return [
            {
                'label': 'Call Intake',
                'detail': 'Start a packet, incident draft, or report workflow from the command board.',
                'endpoint': 'reports.new_report',
            },
            {
                'label': 'Assign Units',
                'detail': 'Update officer assignments, patrol zones, gate posts, and shift status.',
                'endpoint': 'watch_commander.officers',
            },
            {
                'label': 'Review Queue',
                'detail': 'Open submitted reports, saved work, corrections, and supervisor approvals.',
                'endpoint': 'watch_commander.approvals',
            },
            {
                'label': 'Shift Brief',
                'detail': 'Publish watch notes, BOLO reminders, safety notes, and assignment updates.',
                'endpoint': 'watch_commander.briefing',
            },
        ]
    return [
        {
            'label': 'Start Report',
            'detail': 'Create a new report or resume field reporting from your dashboard.',
            'endpoint': 'reports.new_report',
        },
        {
            'label': 'My Reports',
            'detail': 'Review active packets, drafts, and returned correction items.',
            'endpoint': 'reports.list_reports',
        },
        {
            'label': 'Law Lookup',
            'detail': 'Search approved references and add matching law/order notes to reports.',
            'endpoint': 'legal.legal_home',
        },
        {
            'label': 'Saved Work',
            'detail': 'Resume saved forms, report drafts, and unfinished packets.',
            'endpoint': 'forms.saved_forms',
        },
    ]


def _dispatch_preplan_layers(is_command):
    return [
        {
            'label': 'Installation Map',
            'detail': 'Base map, primary gates, road grid, and common response zones.',
            'endpoint': 'dashboard.dispatch_command_center',
        },
        {
            'label': 'Units / Assignments',
            'detail': 'Officer status, post assignment, patrol area, and live unit roster.',
            'endpoint': 'watch_commander.unit_map' if is_command else 'mobile.home',
        },
        {
            'label': 'Incidents / BOLOs',
            'detail': 'Active incident drafts, submitted packets, BOLOs, and command alerts.',
            'endpoint': 'watch_commander.dashboard' if is_command else 'announcements.board',
        },
        {
            'label': 'Reports / Media',
            'detail': 'Reports, accident diagrams, bodycam footage, saved forms, and photos.',
            'endpoint': 'reports.list_reports',
        },
    ]


def _dispatch_live_context():
    is_command = bool(current_user.can_manage_team())
    now = datetime.now().strftime('%H%M')
    if is_command:
        drafts = _safe_all(
            'dispatch_live_drafts',
            IncidentDraft.query.filter_by(status='ACTIVE').order_by(IncidentDraft.updated_at.desc()),
            20,
        )
        packets = _safe_all(
            'dispatch_live_packets',
            IncidentPacket.query.order_by(IncidentPacket.submitted_at.desc()),
            50,
        )
        assignments = _safe_all(
            'dispatch_live_assignments',
            WatchAssignment.query.filter(~WatchAssignment.status.in_(['Off Duty', 'Leave'])).order_by(
                WatchAssignment.updated_at.desc(),
                WatchAssignment.id.desc(),
            ),
            80,
        )
        active_bolos = _safe_all(
            'dispatch_live_bolos',
            BOLOEntry.query.filter_by(status='ACTIVE').order_by(BOLOEntry.created_at.desc()),
            12,
        )
        active_rosters = _safe_count(
            'dispatch_live_training_rosters',
            TrainingRoster.query.filter(TrainingRoster.status.ilike('ACTIVE')),
        )
        pending_approvals = _safe_count(
            'dispatch_live_approvals',
            WatchApproval.query.filter_by(status='PENDING'),
        )
        shift_notes = _safe_all(
            'dispatch_live_shift_notes',
            WatchNote.query.order_by(WatchNote.created_at.desc()),
            8,
        )
        open_shift = _safe_first(
            'dispatch_live_open_shift',
            WatchShift.query.filter(WatchShift.status != 'CLOSED').order_by(WatchShift.created_at.desc()),
        )
    else:
        drafts = _safe_all(
            'dispatch_live_user_drafts',
            IncidentDraft.query.filter_by(officer_user_id=current_user.id, status='ACTIVE').order_by(
                IncidentDraft.updated_at.desc()
            ),
            8,
        )
        packets = _safe_all(
            'dispatch_live_user_packets',
            IncidentPacket.query.filter_by(officer_user_id=current_user.id).order_by(IncidentPacket.submitted_at.desc()),
            20,
        )
        assignments = _safe_all(
            'dispatch_live_user_assignments',
            WatchAssignment.query.filter_by(officer_id=current_user.id).order_by(
                WatchAssignment.updated_at.desc(),
                WatchAssignment.id.desc(),
            ),
            10,
        )
        active_bolos = []
        active_rosters = 0
        pending_approvals = 0
        shift_notes = []
        open_shift = None

    pending_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_PENDING]
    correction_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION]
    approved_packets = [packet for packet in packets if packet.approval_status == PACKET_APPROVAL_APPROVED]

    dispatch_summary = {
        'current_time': now,
        'shift_name': f'{open_shift.shift_type} / {open_shift.status}' if open_shift else 'Live Operational View',
        'shift_status': 'Real-time data — unit positions update every 20s',
    }
    dispatch_metrics = [
        {
            'label': 'Units Visible',
            'value': len(assignments),
            'detail': 'Active unit/post assignments available to this view',
        },
        {
            'label': 'Active Incidents',
            'value': len(drafts),
            'detail': 'Open field drafts and active incident work',
        },
        {
            'label': 'Pending Reports',
            'value': len(pending_packets),
            'detail': 'Report packets waiting for supervisor review',
        },
        {
            'label': 'Corrections',
            'value': len(correction_packets),
            'detail': 'Returned packets needing officer action',
        },
        {
            'label': 'BOLOs',
            'value': len(active_bolos),
            'detail': 'Active alerts in the command picture',
        },
        {
            'label': 'Approvals',
            'value': pending_approvals,
            'detail': 'Watch Commander approval actions pending',
        },
    ]

    active_incidents = []
    for draft in drafts[:5]:
        active_incidents.append({
            'title': draft.call_type or 'Active Incident Draft',
            'detail': draft.location or draft.summary or 'Field draft missing location',
            'priority': 'Active',
            'state_class': 'busy',
        })
    for packet in pending_packets[:4]:
        active_incidents.append({
            'title': packet.call_type or 'Submitted Report Packet',
            'detail': packet.location or packet.summary or 'Supervisor review required',
            'priority': 'Review',
            'state_class': 'busy',
        })
    for packet in correction_packets[:3]:
        active_incidents.append({
            'title': packet.call_type or 'Correction Packet',
            'detail': packet.supervisor_notes or packet.location or 'Corrections requested',
            'priority': 'Correct',
            'state_class': 'alert',
        })
    for bolo in active_bolos[:3]:
        active_incidents.append({
            'title': bolo.subject_name or 'Active BOLO',
            'detail': bolo.offense or bolo.description or bolo.vehicle_description or 'Command alert',
            'priority': bolo.threat_level or 'BOLO',
            'state_class': 'alert',
        })
    for note in shift_notes[:2]:
        active_incidents.append({
            'title': note.title,
            'detail': note.body[:140],
            'priority': note.priority or 'Note',
            'state_class': '',
        })
    if not active_incidents:
        active_incidents.append({
            'title': 'No Active Incidents',
            'detail': 'No active incident drafts, BOLOs, or review alerts are visible right now.',
            'priority': 'Clear',
            'state_class': '',
        })

    total_packets = len(packets)
    clearance = round((len(approved_packets) / total_packets) * 100) if total_packets else 100
    radio_summary = (
        f"Live board: {len(assignments)} visible unit assignment(s), {len(drafts)} active incident draft(s), "
        f"{len(pending_packets)} packet(s) pending review, {len(correction_packets)} correction item(s), "
        f"{len(active_bolos)} active BOLO(s), and {pending_approvals} pending approval action(s). "
        f"Recent packet clearance is {clearance}%. Verify all operational facts before command action."
    )
    if active_rosters:
        radio_summary += f" Training oversight has {active_rosters} active roster(s) requiring monitoring."

    return {
        'dispatch_summary': dispatch_summary,
        'dispatch_metrics': dispatch_metrics,
        'active_incidents': active_incidents[:12],
        'radio_summary': radio_summary,
        'dispatch_mode_label': 'LIVE DATA',
        'dispatch_workflow_cards': _dispatch_workflow_cards(is_command=is_command),
        'dispatch_preplan_layers': _dispatch_preplan_layers(is_command=is_command),
    }


def _load_dashboard_preferences():
    raw = getattr(current_user, 'dashboard_preferences_json', None)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _ordered_visible_items(catalog, selected_ids, default_ids):
    allowed = {item['id']: item for item in catalog}
    ordered_ids = [item_id for item_id in selected_ids if item_id in allowed] if selected_ids else []
    if not ordered_ids:
        ordered_ids = [item_id for item_id in default_ids if item_id in allowed]
    return [allowed[item_id] for item_id in ordered_ids if item_id in allowed]


def _dashboard_preferences_context(snapshot=None):
    snapshot = snapshot or _dashboard_snapshot()
    prefs = _load_dashboard_preferences()
    card_catalog = _dashboard_card_catalog()
    panel_catalog = [
        panel for panel in _dashboard_panel_catalog(snapshot)
        if not panel.get('supervisor_only') or current_user.can_manage_team()
    ]
    selected_cards = prefs.get('cards') if isinstance(prefs.get('cards'), list) else []
    selected_panels = prefs.get('panels') if isinstance(prefs.get('panels'), list) else []
    return {
        'dashboard_card_catalog': card_catalog,
        'dashboard_panel_catalog': panel_catalog,
        'dashboard_cards': _ordered_visible_items(card_catalog, selected_cards, DEFAULT_DASHBOARD_CARD_IDS),
        'dashboard_panels': _ordered_visible_items(panel_catalog, selected_panels, DEFAULT_DASHBOARD_PANEL_IDS),
        'dashboard_selected_card_ids': selected_cards or [card['id'] for card in _ordered_visible_items(card_catalog, [], DEFAULT_DASHBOARD_CARD_IDS)],
        'dashboard_selected_panel_ids': selected_panels or [panel['id'] for panel in _ordered_visible_items(panel_catalog, [], DEFAULT_DASHBOARD_PANEL_IDS)],
    }


@bp.route('/dashboard')
@login_required
def dashboard():
    if _request_prefers_mobile_home():
        return redirect(url_for('mobile.home'))
    snapshot = _dashboard_snapshot()
    preferences_context = _dashboard_preferences_context(snapshot)
    return _no_store_response(
        render_template(
            'dashboard.html',
            user=current_user,
            dashboard_metrics=snapshot['metrics'],
            dashboard_saved_forms_count=snapshot['saved_forms_count'],
            dashboard_report_count=snapshot['report_count'],
            dashboard_cleo_report_count=snapshot['cleo_report_count'],
            dashboard_orders_count=snapshot['orders_count'],
            dashboard_training_count=snapshot['training_count'],
            dashboard_notice_count=snapshot['notice_count'],
            dashboard_announcements=snapshot['announcements'],
            dashboard_readiness_items=snapshot['readiness_items'],
            dashboard_queue_items=snapshot['queue_items'],
            dashboard_live_ops=snapshot['live_ops'],
            **preferences_context,
        )
    )


@bp.route('/dispatch')
@bp.route('/command-center')
@login_required
def dispatch_command_center():
    from ..routes.watch_commander import OFFICER_STATUSES
    demo = _demo_mode()
    ctx = {'demo': demo}
    if demo:
        ctx.update(_dispatch_demo_context())
    else:
        ctx.update(_dispatch_live_context())
    return _no_store_response(
        render_template(
            'dispatch_command_center.html',
            user=current_user,
            statuses=OFFICER_STATUSES,
            **ctx,
        )
    )


def _demo_mode():
    from flask import session as _s
    return bool(_s.get('demo_mode'))


@bp.route('/k9')
@login_required
def k9_dashboard():
    demo = _demo_mode()
    context = {
        'user': current_user,
        'team': [
            {'name': 'Sgt. Carter', 'partner': 'Rex', 'status': 'On Patrol', 'state_class': '', 'assignment': 'North Gate sweep'},
            {'name': 'Ofc. Davis',  'partner': 'Bruno', 'status': 'Available', 'state_class': '', 'assignment': 'Ready for deployment'},
            {'name': 'Ofc. Lewis',  'partner': 'Kira', 'status': 'Training', 'state_class': 'busy', 'assignment': 'Obedience refresher — K9 Compound'},
            {'name': 'Ofc. Nguyen', 'partner': 'Axel', 'status': 'On Patrol', 'state_class': '', 'assignment': 'Barracks area'},
            {'name': 'Ofc. Torres', 'partner': 'Shadow', 'status': 'Off Duty', 'state_class': 'standby', 'assignment': '—'},
        ] if demo else [],
        'metrics': [
            {'label': 'Teams on duty', 'value': '4', 'detail': '1 off duty'},
            {'label': 'Sweeps this shift', 'value': '3', 'detail': 'North Gate, Barracks, MCX'},
            {'label': 'Alerts issued', 'value': '0', 'detail': 'No active narcotics alerts'},
            {'label': 'Training hours (MTD)', 'value': '42', 'detail': '87% of monthly target'},
        ] if demo else [],
        'alerts': [
            {'title': 'Sweep Request — MCX Parking', 'detail': 'Requested by Desk Sgt at 1340', 'priority': 'Routine'},
            {'title': 'K9 Cert Renewal', 'detail': 'Kira due for annual cert — contact Kennel Master', 'priority': 'Admin'},
        ] if demo else [],
        'demo': demo,
    }
    return _no_store_response(render_template('unit_dashboards/k9.html', **context))


@bp.route('/cvi')
@login_required
def cvi_dashboard():
    demo = _demo_mode()
    context = {
        'user': current_user,
        'team': [
            {'name': 'Lt. Harper',  'status': 'Monitoring', 'state_class': '', 'post': 'CVI Station — Command'},
            {'name': 'Ofc. Mason',  'status': 'Inspecting', 'state_class': 'busy', 'post': 'Gate 2 Lane 1 — CMV inspection'},
            {'name': 'Ofc. Perry',  'status': 'Inspecting', 'state_class': 'busy', 'post': 'Gate 2 Lane 2'},
            {'name': 'Ofc. Quinn',  'status': 'Available', 'state_class': '', 'post': 'CVI Station — standby'},
            {'name': 'Ofc. Russell','status': 'Report Writing', 'state_class': 'busy', 'post': 'PMO — completing OOS paperwork'},
            {'name': 'Ofc. Sanders','status': 'Off Duty', 'state_class': 'standby', 'post': '—'},
        ] if demo else [],
        'metrics': [
            {'label': 'Inspections today', 'value': '14', 'detail': '2 OOS violations'},
            {'label': 'OOS vehicles', 'value': '2', 'detail': '1 resolved, 1 pending paperwork'},
            {'label': 'Officers on post', 'value': '5', 'detail': '1 off duty'},
            {'label': 'Avg inspection time', 'value': '18 min', 'detail': 'Below 25-min target'},
        ] if demo else [],
        'log': [
            {'time': '1312', 'entry': 'CMV — flatbed tractor, OOS: brake defect. Driver notified, paperwork initiated. Ofc. Russell.'},
            {'time': '1227', 'entry': 'CMV — tanker, passed inspection. No violations. Ofc. Mason.'},
            {'time': '1148', 'entry': 'POV — routine access check, cleared. Ofc. Perry.'},
            {'time': '1053', 'entry': 'CMV — box truck, OOS: expired registration. Vehicle secured Gate 2. Resolved 1138.'},
        ] if demo else [],
        'demo': demo,
    }
    return _no_store_response(render_template('unit_dashboards/cvi.html', **context))


@bp.route('/srt')
@login_required
def srt_dashboard():
    demo = _demo_mode()
    context = {
        'user': current_user,
        'team': [
            {'name': 'Lt. Lawson', 'role': 'SRT Commander', 'status': 'Standby', 'state_class': '', 'note': 'Command ready'},
            {'name': 'Ofc. Bishop', 'role': 'Breacher', 'status': 'Training', 'state_class': 'busy', 'note': 'CQB refresher'},
            {'name': 'Ofc. Cole',   'role': 'Sniper', 'status': 'Standby', 'state_class': '', 'note': 'Qualification current'},
            {'name': 'Ofc. Drake',  'role': 'Medic', 'status': 'Standby', 'state_class': '', 'note': 'TCCC cert current'},
            {'name': 'Ofc. Evans',  'role': 'Entry', 'status': 'Standby', 'state_class': '', 'note': 'Equipment inspected'},
            {'name': 'Ofc. Flynn',  'role': 'Entry', 'status': 'Leave', 'state_class': 'standby', 'note': 'Returns Friday'},
        ] if demo else [],
        'readiness': [
            {'item': 'Team qualification current', 'status': 'GO', 'ok': True},
            {'item': 'Equipment inventory verified', 'status': 'GO', 'ok': True},
            {'item': 'Command notification list current', 'status': 'GO', 'ok': True},
            {'item': 'CQB training — monthly requirement', 'status': 'IN PROGRESS', 'ok': None},
            {'item': 'Vehicle readiness check', 'status': 'GO', 'ok': True},
            {'item': 'Medical kit inspection', 'status': 'GO', 'ok': True},
        ] if demo else [],
        'metrics': [
            {'label': 'Members available', 'value': '5 / 6', 'detail': '1 on leave'},
            {'label': 'Readiness level', 'value': 'STANDBY', 'detail': 'Full deployment capable'},
            {'label': 'Last activation', 'value': '47 days', 'detail': 'Training exercise'},
            {'label': 'Next training', 'value': 'Thu 0800', 'detail': 'CQB — Range 3'},
        ] if demo else [],
        'demo': demo,
    }
    return _no_store_response(render_template('unit_dashboards/srt.html', **context))



@bp.route('/dashboard/customize', methods=['GET', 'POST'])
@login_required
def customize_dashboard():
    snapshot = _dashboard_snapshot()
    context = _dashboard_preferences_context(snapshot)
    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()
        if action == 'reset':
            current_user.dashboard_preferences_json = None
            db.session.commit()
            flash('Dashboard reset to the MCPD default layout.', 'success')
            return redirect(url_for('dashboard.dashboard'))

        allowed_card_ids = {card['id'] for card in context['dashboard_card_catalog']}
        allowed_panel_ids = {panel['id'] for panel in context['dashboard_panel_catalog']}
        selected_cards = [item for item in request.form.getlist('cards') if item in allowed_card_ids]
        selected_panels = [item for item in request.form.getlist('panels') if item in allowed_panel_ids]
        if not selected_cards:
            selected_cards = [item for item in DEFAULT_DASHBOARD_CARD_IDS if item in allowed_card_ids]
        if not selected_panels:
            selected_panels = [item for item in DEFAULT_DASHBOARD_PANEL_IDS if item in allowed_panel_ids]
        current_user.dashboard_preferences_json = json.dumps(
            {'cards': selected_cards, 'panels': selected_panels},
            sort_keys=True,
        )
        db.session.commit()
        flash('Dashboard layout saved.', 'success')
        return redirect(url_for('dashboard.dashboard'))

    return _no_store_response(render_template('dashboard_customize.html', user=current_user, **context))


@bp.route('/cleo')
@login_required
def cleo():
    return redirect(url_for('reports.list_reports'))


@bp.route('/diagrams')
@login_required
def diagrams():
    # Backwards-compatible alias: "Diagramming" was replaced by Reconstruction.
    return redirect(url_for('reconstruction.case_list'))
