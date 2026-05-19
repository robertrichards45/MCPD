import json
import secrets
from datetime import timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user

from ..extensions import db
from ..models import (
    ROLE_ACCIDENT_INVESTIGATOR,
    ROLE_AID_LIEUTENANT,
    ROLE_AID_OFFICER,
    ROLE_ASSISTANT_OPERATIONS_OFFICER,
    ROLE_CVI_LIEUTENANT,
    ROLE_CVI_OFFICER,
    ROLE_DESK_SGT,
    ROLE_FORMS_MANAGER,
    ROLE_K9_OFFICER,
    ROLE_K9_SERGEANT,
    ROLE_KENNEL_MASTER,
    ROLE_LABELS,
    ROLE_PATROL_OFFICER,
    ROLE_REPORT_REVIEWER,
    ROLE_SRT_COMMANDER,
    ROLE_SRT_OFFICER,
    ROLE_TRAINING_MANAGER,
    ROLE_WATCH_COMMANDER,
    ROLE_WEBSITE_CONTROLLER,
    AccidentReconstruction,
    DemoRecord,
    Form,
    IncidentDraft,
    IncidentPacket,
    OperationsTask,
    PACKET_APPROVAL_APPROVED,
    PACKET_APPROVAL_NEEDS_CORRECTION,
    PACKET_APPROVAL_PENDING,
    Report,
    Role,
    SavedForm,
    ShiftBrief,
    TrainingRoster,
    TrainingSignature,
    User,
    UserRole,
    WatchApproval,
    WatchAssignment,
    WatchNote,
    WatchShift,
    utcnow_naive,
)
from ..permissions import is_site_owner

bp = Blueprint('demo', __name__, url_prefix='/demo')

DEMO_PASSWORD = 'DemoOnly123!'

DEMO_SHIFT_STAFFING = {
    'Alpha Shift': [
        ('demo.alpha.adams', 'Lt.', 'Adams', ROLE_WATCH_COMMANDER, 'Watch Commander'),
        ('demo.alpha.brooks', 'Sgt.', 'Brooks', ROLE_DESK_SGT, 'Desk Sergeant'),
        ('demo.alpha.carter', 'Ofc.', 'Carter', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.alpha.daniels', 'Ofc.', 'Daniels', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.alpha.ellis', 'Ofc.', 'Ellis', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.alpha.foster', 'Ofc.', 'Foster', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.alpha.grant', 'Ofc.', 'Grant', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.alpha.hayes', 'Ofc.', 'Hayes', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.alpha.irwin', 'Ofc.', 'Irwin', ROLE_PATROL_OFFICER, 'Officer'),
    ],
    'Bravo Shift': [
        ('demo.bravo.bennett', 'Lt.', 'Bennett', ROLE_WATCH_COMMANDER, 'Watch Commander'),
        ('demo.bravo.collins', 'Sgt.', 'Collins', ROLE_DESK_SGT, 'Desk Sergeant'),
        ('demo.bravo.davis', 'Ofc.', 'Davis', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.bravo.evans', 'Ofc.', 'Evans', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.bravo.fisher', 'Ofc.', 'Fisher', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.bravo.greene', 'Ofc.', 'Greene', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.bravo.howard', 'Ofc.', 'Howard', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.bravo.jenkins', 'Ofc.', 'Jenkins', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.bravo.king', 'Ofc.', 'King', ROLE_PATROL_OFFICER, 'Officer'),
    ],
    'Charlie Shift': [
        ('demo.charlie.cooper', 'Lt.', 'Cooper', ROLE_WATCH_COMMANDER, 'Watch Commander'),
        ('demo.charlie.diaz', 'Sgt.', 'Diaz', ROLE_DESK_SGT, 'Desk Sergeant'),
        ('demo.charlie.lewis', 'Ofc.', 'Lewis', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.charlie.mitchell', 'Ofc.', 'Mitchell', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.charlie.nelson', 'Ofc.', 'Nelson', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.charlie.owens', 'Ofc.', 'Owens', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.charlie.parker', 'Ofc.', 'Parker', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.charlie.reed', 'Ofc.', 'Reed', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.charlie.stone', 'Ofc.', 'Stone', ROLE_PATROL_OFFICER, 'Officer'),
    ],
    'Delta Shift': [
        ('demo.delta.douglas', 'Lt.', 'Douglas', ROLE_WATCH_COMMANDER, 'Watch Commander'),
        ('demo.delta.edwards', 'Sgt.', 'Edwards', ROLE_DESK_SGT, 'Desk Sergeant'),
        ('demo.delta.turner', 'Ofc.', 'Turner', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.delta.walker', 'Ofc.', 'Walker', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.delta.young', 'Ofc.', 'Young', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.delta.bailey', 'Ofc.', 'Bailey', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.delta.morris', 'Ofc.', 'Morris', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.delta.powell', 'Ofc.', 'Powell', ROLE_PATROL_OFFICER, 'Officer'),
        ('demo.delta.ross', 'Ofc.', 'Ross', ROLE_PATROL_OFFICER, 'Officer'),
    ],
}

DEMO_SECTION_STAFFING = {
    'CVI': [
        ('demo.cvi.harper', 'Lt.', 'Harper', ROLE_CVI_LIEUTENANT, 'CVI Lieutenant'),
        ('demo.cvi.mason', 'Ofc.', 'Mason', ROLE_CVI_OFFICER, 'CVI Officer'),
        ('demo.cvi.perry', 'Ofc.', 'Perry', ROLE_CVI_OFFICER, 'CVI Officer'),
        ('demo.cvi.quinn', 'Ofc.', 'Quinn', ROLE_CVI_OFFICER, 'CVI Officer'),
        ('demo.cvi.russell', 'Ofc.', 'Russell', ROLE_CVI_OFFICER, 'CVI Officer'),
        ('demo.cvi.sanders', 'Ofc.', 'Sanders', ROLE_CVI_OFFICER, 'CVI Officer'),
    ],
    'AID': [
        ('demo.aid.morgan', 'Lt.', 'Morgan', ROLE_AID_LIEUTENANT, 'AID Lieutenant'),
        ('demo.aid.bryant', 'Ofc.', 'Bryant', ROLE_AID_OFFICER, 'AID Officer'),
        ('demo.aid.coleman', 'Ofc.', 'Coleman', ROLE_AID_OFFICER, 'AID Officer'),
    ],
    'SRT': [
        ('demo.srt.lawson', 'Lt.', 'Lawson', ROLE_SRT_COMMANDER, 'SRT Commander'),
        ('demo.srt.bishop', 'Ofc.', 'Bishop', ROLE_SRT_OFFICER, 'SRT Officer'),
        ('demo.srt.cross', 'Ofc.', 'Cross', ROLE_SRT_OFFICER, 'SRT Officer'),
        ('demo.srt.fields', 'Ofc.', 'Fields', ROLE_SRT_OFFICER, 'SRT Officer'),
        ('demo.srt.graves', 'Ofc.', 'Graves', ROLE_SRT_OFFICER, 'SRT Officer'),
        ('demo.srt.norton', 'Ofc.', 'Norton', ROLE_SRT_OFFICER, 'SRT Officer'),
    ],
    'K-9': [
        ('demo.k9.kennedy', 'Lt.', 'Kennedy', ROLE_KENNEL_MASTER, 'Kennel Master'),
        ('demo.k9.porter', 'Sgt.', 'Porter', ROLE_K9_SERGEANT, 'K9 Sergeant'),
        ('demo.k9.archer', 'Ofc.', 'Archer', ROLE_K9_OFFICER, 'K9 Officer'),
        ('demo.k9.blake', 'Ofc.', 'Blake', ROLE_K9_OFFICER, 'K9 Officer'),
        ('demo.k9.chase', 'Ofc.', 'Chase', ROLE_K9_OFFICER, 'K9 Officer'),
        ('demo.k9.dalton', 'Ofc.', 'Dalton', ROLE_K9_OFFICER, 'K9 Officer'),
        ('demo.k9.mercer', 'Ofc.', 'Mercer', ROLE_K9_OFFICER, 'K9 Officer'),
        ('demo.k9.vaughn', 'Ofc.', 'Vaughn', ROLE_K9_OFFICER, 'K9 Officer'),
    ],
}

DEMO_ADMIN_USERS = [
    ('demo.admin.controller', 'Capt.', 'Rivers', ROLE_WEBSITE_CONTROLLER, 'Admin'),
    ('demo.assistant.ops', 'Lt.', 'Marlow', ROLE_ASSISTANT_OPERATIONS_OFFICER, 'Assistant Operations Officer'),
    ('demo.training.manager', 'Sgt.', 'Nolan', ROLE_TRAINING_MANAGER, 'Training Manager'),
    ('demo.report.reviewer', 'Sgt.', 'Hale', ROLE_REPORT_REVIEWER, 'Report Reviewer'),
]

WORKFLOW_LAUNCHERS = [
    ('law-lookup', 'Law Lookup Demo', '/demo/law-lookup', 'Plain-language legal/reference examples using approved sample records.'),
    ('completed-reports', 'Completed Report Samples', '/demo/report-samples', 'View and print two fully completed, approved incident reports with all fields and paperwork.'),
    ('watch-commander', 'Watch Commander Demo', '/watch-commander/dashboard', 'Shift command, approvals, saved work, assignments, and briefing.'),
    ('desk-sgt', 'Desk Sgt Demo', '/demo/workflows/desk-sgt', 'Report review queue, blotter checks, and correction-note examples.'),
    ('training', 'Training Demo', '/watch-commander/training', 'Roster completion and overdue signature tracking.'),
    ('cvi', 'CVI Demo', '/demo/workflows/cvi', 'Commercial vehicle inspection activity and daily summary.'),
    ('aid', 'AID Demo', '/demo/workflows/aid', 'Administrative investigation case tracking and follow-up assignments.'),
    ('srt', 'SRT Demo', '/demo/workflows/srt', 'SRT readiness, training, equipment, and after-action examples.'),
    ('k9', 'K-9 Demo', '/demo/workflows/k9', 'K-9 deployment, training, and kennel maintenance examples.'),
    ('admin', 'Admin Demo', '/demo/workflows/admin', 'User, role, reference data, and system settings demonstration.'),
]

DEMO_LAW_RESULTS = [
    {
        'query': 'trespassing on federal installation',
        'citation': '18 USC 1382',
        'title': 'Entering military, naval, or Coast Guard property',
        'source_type': 'Federal',
        'why': 'Matches unauthorized entry or remaining on a military installation after notice.',
        'excerpt': 'Sample summary: federal installation access violations may support removal or charging review.',
    },
    {
        'query': 'barred person returned to base',
        'citation': 'MCLB Albany Order 5530.1',
        'title': 'Installation Access Control',
        'source_type': 'Base Orders',
        'why': 'Relates to barred-person access control and gate response procedures.',
        'excerpt': 'Sample excerpt: personnel barred by written notice are denied access and law enforcement is notified.',
    },
    {
        'query': 'domestic disturbance involving spouse',
        'citation': 'O.C.G.A. 16-5-20 / Base DV Response Memo',
        'title': 'Simple Battery and Domestic Response Checklist',
        'source_type': 'Georgia / Memo',
        'why': 'Matches spouse/domestic relationship, disturbance facts, and supplemental documentation need.',
        'excerpt': 'Sample excerpt: document relationship, injury/no-injury status, statements, and command notification.',
    },
    {
        'query': 'minor traffic accident in parking lot',
        'citation': 'DD Form 1408 / Accident Response SOP',
        'title': 'Traffic Accident Reporting and Diagram Requirements',
        'source_type': 'Base Orders',
        'why': 'Matches minor collision, parking lot location, driver information, and diagram workflow.',
        'excerpt': 'Sample excerpt: complete exchange, diagram, photos, and supervisor notification if government vehicle involved.',
    },
    {
        'query': 'stolen property from vehicle',
        'citation': 'O.C.G.A. 16-8-2',
        'title': 'Theft by Taking',
        'source_type': 'Georgia',
        'why': 'Matches property taken from a vehicle and report narrative elements.',
        'excerpt': 'Sample excerpt: identify property, ownership, value, location, and known suspect information if available.',
    },
]


def _can_control_demo():
    if is_site_owner(current_user):
        return True
    controller_id = session.get('demo_controller_id')
    controller = db.session.get(User, controller_id) if controller_id else None
    return bool(controller and is_site_owner(controller) and getattr(current_user, 'is_demo', False))


def _require_demo_controller():
    if not _can_control_demo():
        abort(403)


def _require_site_owner():
    if not is_site_owner(current_user):
        abort(403)


def _clear_demo_session():
    session.pop('demo_mode', None)
    session.pop('demo_batch_id', None)
    session.pop('demo_viewing_as', None)
    session.pop('demo_controller_id', None)


def _seed_roles():
    existing = {role.key: role for role in Role.query.all()}
    for role_key, label in ROLE_LABELS.items():
        if role_key not in existing:
            db.session.add(Role(key=role_key, label=label))
    db.session.flush()


def _apply_role(user, role_key):
    role = Role.query.filter_by(key=role_key).first()
    if role and role not in user.roles:
        user.roles.append(role)


def _demo_user(username, rank, last_name, role_key, section, batch_id):
    first_name = rank.replace('.', '')
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        user.set_password(DEMO_PASSWORD)
    user.first_name = first_name
    user.last_name = last_name
    user.display_name_override = f'{rank} {last_name}'
    user.email = f'{username}@demo.local'
    user.role = role_key
    user.active = True
    user.pending_approval = False
    user.installation = 'MCLB_ALBANY'
    user.section_unit = section
    user.is_demo = True
    user.demo_batch_id = batch_id
    _apply_role(user, role_key)
    db.session.add(user)
    return user


def _demo_record(batch_id, record_type, title, status='Active', summary='', payload=None, route=None, owner=None):
    row = DemoRecord(
        record_type=record_type,
        title=title,
        status=status,
        summary=summary,
        payload_json=json.dumps(payload or {}),
        source_route=route,
        owner_user_id=getattr(owner, 'id', None),
        is_demo=True,
        demo_batch_id=batch_id,
    )
    db.session.add(row)
    return row


def _delete_demo_rows():
    demo_user_ids = [user.id for user in User.query.filter_by(is_demo=True).all()]
    if demo_user_ids:
        UserRole.query.filter(UserRole.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
    models = [
        DemoRecord,
        TrainingSignature,
        SavedForm,
        OperationsTask,
        WatchApproval,
        WatchNote,
        WatchAssignment,
        ShiftBrief,
        WatchShift,
        AccidentReconstruction,
        IncidentPacket,
        IncidentDraft,
        Report,
        TrainingRoster,
        Form,
        User,
    ]
    deleted = {}
    for model in models:
        count = model.query.filter_by(is_demo=True).delete(synchronize_session=False)
        deleted[model.__name__] = count
    db.session.commit()
    _clear_demo_session()
    return deleted


def _create_staff(batch_id):
    _seed_roles()
    users = {}
    for shift, rows in DEMO_SHIFT_STAFFING.items():
        for row in rows:
            username, rank, last_name, role_key, _label = row
            user = _demo_user(username, rank, last_name, role_key, section=shift, batch_id=batch_id)
            users[username] = user
    for section, rows in DEMO_SECTION_STAFFING.items():
        for row in rows:
            username, rank, last_name, role_key, _label = row
            user = _demo_user(username, rank, last_name, role_key, section=section, batch_id=batch_id)
            users[username] = user
    for row in DEMO_ADMIN_USERS:
        username, rank, last_name, role_key, _label = row
        user = _demo_user(username, rank, last_name, role_key, section='Command Staff', batch_id=batch_id)
        users[username] = user
    db.session.flush()
    return users


def _create_shift_data(batch_id, users):
    today = utcnow_naive().date()
    assignments = ['Patrol Zone', 'Gate Post', 'Report Writing', 'Training', 'RAM / Security Check']
    for idx, (shift, rows) in enumerate(DEMO_SHIFT_STAFFING.items()):
        wc = users[rows[0][0]]
        desk = users[rows[1][0]]
        shift_row = WatchShift(
            shift_date=today.isoformat(),
            shift_type=shift,
            watch_commander_id=wc.id,
            desk_sergeant_id=desk.id,
            status='OPEN',
            start_time='0600' if idx % 2 == 0 else '1800',
            end_time='1800' if idx % 2 == 0 else '0600',
            notes=f'Demo {shift} operations with gate, patrol, and report-writing coverage.',
            is_demo=True,
            demo_batch_id=batch_id,
        )
        db.session.add(shift_row)
        db.session.flush()
        for officer_idx, row in enumerate(rows):
            user = users[row[0]]
            db.session.add(WatchAssignment(
                shift_id=shift_row.id,
                officer_id=user.id,
                assignment_type=assignments[officer_idx % len(assignments)],
                assignment_location=f'{shift} Post {officer_idx + 1}',
                status=['On Duty', 'Patrol', 'Gate', 'Report Writing', 'Training'][officer_idx % 5],
                start_time=shift_row.start_time,
                end_time=shift_row.end_time,
                notes='Demo assignment only.',
                is_demo=True,
                demo_batch_id=batch_id,
            ))
        db.session.add(WatchNote(
            shift_id=shift_row.id,
            created_by=wc.id,
            note_type='shift_note',
            title=f'{shift} demo watch note',
            body='Sample note: verify gate relief, pending reports, training reminders, and BOLO status.',
            priority='Normal',
            is_demo=True,
            demo_batch_id=batch_id,
        ))
        db.session.add(ShiftBrief(
            shift_id=shift_row.id,
            created_by=wc.id,
            title=f'{shift} Shift Brief',
            body='Demo brief: safety reminder, gate posture, report corrections, and training suspense items.',
            status='PUBLISHED',
            is_demo=True,
            demo_batch_id=batch_id,
        ))


def _create_reports_forms_training(batch_id, users):
    officer = users['demo.alpha.carter']
    wc = users['demo.alpha.adams']
    desk = users['demo.alpha.brooks']
    scenarios = [
        ('Larceny from barracks parking lot', 'DRAFT', 'Saved draft report with parties and facts started.'),
        ('Larceny from barracks parking lot', 'SUBMITTED', 'Submitted packet awaiting supervisor review.'),
        ('Larceny from barracks parking lot', 'NEEDS_CORRECTION', 'Returned for missing property value and witness statement.'),
        ('Larceny from barracks parking lot', 'APPROVED', 'Approved demonstration report packet.'),
    ]
    for idx, (title, status, summary) in enumerate(scenarios, start=1):
        report = Report(title=f'DEMO-{idx}: {title}', owner_id=officer.id, status=status, is_demo=True, demo_batch_id=batch_id)
        db.session.add(report)
        packet_status = {
            'DRAFT': PACKET_APPROVAL_PENDING,
            'SUBMITTED': PACKET_APPROVAL_PENDING,
            'NEEDS_CORRECTION': PACKET_APPROVAL_NEEDS_CORRECTION,
            'APPROVED': PACKET_APPROVAL_APPROVED,
        }[status]
        db.session.add(IncidentPacket(
            officer_user_id=officer.id,
            call_type='Larceny',
            occurred_date=utcnow_naive().date().isoformat(),
            location='Demo barracks parking lot',
            summary=summary,
            form_count=0,
            statement_count=2,
            packet_json=json.dumps({'parties': ['Reporting person', 'Witness'], 'facts': summary}),
            validation_json=json.dumps({'missing': [] if status == 'APPROVED' else ['Property value confirmation']}),
            approval_status=packet_status,
            reviewer_user_id=wc.id if status in {'NEEDS_CORRECTION', 'APPROVED'} else None,
            supervisor_notes='Demo correction note: verify value, serial number, and parking lot camera check.' if status == 'NEEDS_CORRECTION' else '',
            is_demo=True,
            demo_batch_id=batch_id,
        ))

    roster_titles = ['Use of Force Refresher', 'Domestic Disturbance Response', 'DBIDS Scanner Refresher', 'Medical Response/AED']
    training_users = [user for user in users.values() if user.section_unit in {'Alpha Shift', 'Bravo Shift'}][:15]
    for idx, title in enumerate(roster_titles, start=1):
        roster = TrainingRoster(
            title=f'DEMO {title}',
            description='Demonstration roster showing signed, unsigned, overdue, and completion-percentage examples.',
            file_path_original=f'demo/training/{idx}.pdf',
            uploaded_by=users['demo.training.manager'].id,
            status='ACTIVE',
            is_demo=True,
            demo_batch_id=batch_id,
        )
        db.session.add(roster)
        db.session.flush()
        for signer in training_users[: 8 + (idx % 4)]:
            db.session.add(TrainingSignature(
                roster_id=roster.id,
                user_id=signer.id,
                signature_path='demo/signatures/sample.png',
                comment='Demo signature only.',
                is_demo=True,
                demo_batch_id=batch_id,
            ))

    db.session.add(WatchApproval(
        target_type='Report',
        target_id=None,
        requested_by=officer.id,
        reviewed_by=wc.id,
        status='PENDING',
        comments='Demo report packet pending Watch Commander review.',
        is_demo=True,
        demo_batch_id=batch_id,
    ))


def _create_section_workflows(batch_id, users):
    section_payloads = {
        'cvi': [
            ('Commercial vehicle inspection log', '24 inspections completed; 3 follow-up notes pending.'),
            ('Truck entry issue', 'Demo truck denied entry pending credential verification.'),
            ('Daily CVI summary', 'Gate flow steady; one DBIDS mismatch escalated.'),
        ],
        'aid': [
            ('Administrative investigation case', 'Open case with interview and document review tasks.'),
            ('Follow-up assignment', 'Investigator assigned to collect witness statement.'),
            ('Case awaiting review', 'Demo case ready for lieutenant review.'),
        ],
        'srt': [
            ('SRT training roster', 'Team movement refresher at 83% completion.'),
            ('Equipment check', 'Ballistic shields and breaching kit logged serviceable.'),
            ('After-action note', 'Pending AAR from simulated call-out.'),
        ],
        'k9': [
            ('K-9 deployment log', 'Narcotics sweep support completed at Gate 2.'),
            ('Vehicle search assistance', 'Demo search record attached to patrol case.'),
            ('Kennel maintenance note', 'Climate control check and sanitation logged.'),
        ],
        'desk-sgt': [
            ('Report review queue', 'Two packets pending initial Desk Sgt review.'),
            ('Correction note example', 'Return report for missing witness information.'),
            ('Approved blotter entry', 'Demo blotter entry reviewed and approved.'),
        ],
        'admin': [
            ('User management', 'Approve, disable, transfer, and role assignment demonstration.'),
            ('Reference data management', 'Forms, law sources, and orders controlled by authorized users.'),
            ('Builder request tracking', 'Demo change requests staged for Site Owner approval.'),
        ],
        'builder': [
            ('Add new larceny report template', 'Proposed'),
            ('Improve law lookup result ranking', 'Needs Review'),
            ('Add K-9 deployment log', 'Approved'),
        ],
    }
    owners = {
        'cvi': users['demo.cvi.harper'],
        'aid': users['demo.aid.morgan'],
        'srt': users['demo.srt.lawson'],
        'k9': users['demo.k9.kennedy'],
        'desk-sgt': users['demo.alpha.brooks'],
        'admin': users['demo.admin.controller'],
        'builder': users['demo.admin.controller'],
    }
    for record_type, rows in section_payloads.items():
        for title, summary in rows:
            _demo_record(batch_id, record_type, title, 'Active', summary, {'sample': True}, owner=owners[record_type])
    for row in DEMO_LAW_RESULTS:
        _demo_record(batch_id, 'law_lookup', row['title'], row['source_type'], row['why'], row, '/demo/law-lookup')

    _demo_record(batch_id, 'dashboard_metric', 'Command Overview Metrics', 'Loaded', '36 patrol officers, 6 CVI, 3 AID, 6 SRT, 8 K-9, 18 reports this week, 87% training completion.', {
        'patrol_officers': 36,
        'cvi_personnel': 6,
        'aid_personnel': 3,
        'srt_personnel': 6,
        'k9_personnel': 8,
        'reports_this_week': 18,
        'pending_review': 5,
        'returned_for_correction': 3,
        'training_completion': 87,
        'saved_work_items': 9,
        'open_approvals': 4,
    })


def _create_accidents_and_tasks(batch_id, users):
    officer = users['demo.bravo.davis']
    investigator = users['demo.accident.investigator']
    for idx, title in enumerate(['Simple Officer Accident Diagram', 'Investigator Reconstruction Case'], start=1):
        db.session.add(AccidentReconstruction(
            incident_number=f'DEMO-ACC-{idx:03d}',
            title=f'DEMO {title}',
            location='Demo north parking lot',
            date_time=utcnow_naive() - timedelta(days=idx),
            officer_id=investigator.id if idx == 2 else officer.id,
            status='PENDING_REVIEW' if idx == 1 else 'DRAFT',
            weather='Clear',
            road_surface='Dry asphalt',
            notes='Demo accident case with direction of travel, vehicle/object entries, impact marker, and review status.',
            diagram_data_json=json.dumps({'vehicles': ['V1 sedan northbound', 'V2 pickup eastbound'], 'legend': True, 'demo': True}),
            is_demo=True,
            demo_batch_id=batch_id,
        ))

    required_users = [users['demo.alpha.adams'], users['demo.bravo.bennett'], users['demo.charlie.cooper'], users['demo.delta.douglas']]
    task = OperationsTask(
        task_id=f'OPS-DEMO-{secrets.token_hex(3).upper()}',
        task_title='Command due-out: verify watch readiness binder',
        task_category='Inspection',
        description='Demo Assistant Operations task assigned to all watch commanders with completion tracked by named commanders.',
        assigned_watch='All Watches',
        assignment_target='ALL_WATCH_COMMANDERS',
        assigned_user_ids_json=json.dumps([user.id for user in required_users]),
        assigned_user_names=', '.join(user.display_name for user in required_users),
        assigned_lead_id=users['demo.assistant.ops'].id,
        assigned_lead_name=users['demo.assistant.ops'].display_name,
        completion_target='WATCH_COMMANDERS',
        required_user_ids_json=json.dumps([user.id for user in required_users]),
        required_user_names=', '.join(user.display_name for user in required_users),
        created_by_id=users['demo.assistant.ops'].id,
        due_date=utcnow_naive() + timedelta(days=5),
        priority='Command Critical',
        status='In Progress',
        total_personnel_required=len(required_users),
        personnel_completed=3,
        personnel_pending=1,
        percent_complete=75,
        days_until_due=5,
        commander_notes='Demo command tracker item for completion graph demonstration.',
        last_updated_by_id=users['demo.assistant.ops'].id,
        is_demo=True,
        demo_batch_id=batch_id,
    )
    db.session.add(task)


def _load_demo_data():
    _delete_demo_rows()
    batch_id = f'MCPD-DEMO-{utcnow_naive().strftime("%Y%m%d%H%M%S")}-{secrets.token_hex(3)}'
    users = _create_staff(batch_id)
    _create_shift_data(batch_id, users)
    _create_reports_forms_training(batch_id, users)
    _create_section_workflows(batch_id, users)
    db.session.commit()
    session['demo_mode'] = True
    session['demo_batch_id'] = batch_id
    session['demo_controller_id'] = current_user.id
    return batch_id


def _demo_counts():
    return {
        'users': User.query.filter_by(is_demo=True).count(),
        'shifts': WatchShift.query.filter_by(is_demo=True).count(),
        'assignments': WatchAssignment.query.filter_by(is_demo=True).count(),
        'reports': Report.query.filter_by(is_demo=True).count() + IncidentPacket.query.filter_by(is_demo=True).count(),
        'forms': 0,
        'training': TrainingRoster.query.filter_by(is_demo=True).count(),
        'approvals': WatchApproval.query.filter_by(is_demo=True).count(),
        'accidents': 0,
        'workflows': DemoRecord.query.filter_by(is_demo=True).count(),
    }


@bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    _require_site_owner()
    if request.method == 'POST':
        batch_id = _load_demo_data()
        flash('MCPD demo data loaded. Use the demo user switcher to click through each role.', 'success')
        return redirect(url_for('demo.dashboard', batch_id=batch_id))
    return render_template('demo/setup.html', title='Load MCPD Demo Data', user=current_user, counts=_demo_counts())


@bp.post('/toggle')
@login_required
def toggle():
    if session.get('demo_mode'):
        _require_site_owner()
        _clear_demo_session()
        flash('Demo Mode turned off. Demo data remains available until you reset it.', 'success')
        return redirect(url_for('dashboard.dashboard'))

    _require_site_owner()
    batch_id = session.get('demo_batch_id')
    if not DemoRecord.query.filter_by(is_demo=True).first():
        batch_id = _load_demo_data()
    else:
        latest = DemoRecord.query.filter_by(is_demo=True).order_by(DemoRecord.created_at.desc()).first()
        batch_id = latest.demo_batch_id if latest else f'MCPD-DEMO-{utcnow_naive().strftime("%Y%m%d%H%M%S")}'
        session['demo_mode'] = True
        session['demo_batch_id'] = batch_id
        session['demo_controller_id'] = current_user.id
    flash('Demo Mode turned on. Sample data only.', 'success')
    return redirect(url_for('demo.dashboard'))


@bp.post('/reset')
@login_required
def reset():
    _require_site_owner()
    deleted = _delete_demo_rows()
    flash('Demo data reset complete. Real records were not touched.', 'success')
    return redirect(url_for('demo.setup', deleted=json.dumps(deleted)))


@bp.route('/dashboard')
@login_required
def dashboard():
    _require_demo_controller()
    staff_sections = {
        **{shift: rows for shift, rows in DEMO_SHIFT_STAFFING.items()},
        **{section: rows for section, rows in DEMO_SECTION_STAFFING.items()},
    }
    return render_template(
        'demo/dashboard.html',
        title='MCPD Demo Dashboard',
        user=current_user,
        counts=_demo_counts(),
        staff_sections=staff_sections,
        launchers=WORKFLOW_LAUNCHERS,
        batch_id=session.get('demo_batch_id'),
    )


@bp.route('/users')
@login_required
def users():
    _require_demo_controller()
    rows = User.query.filter_by(is_demo=True).order_by(User.section_unit.asc(), User.role.asc(), User.last_name.asc()).all()
    return render_template('demo/users.html', title='Demo Users', user=current_user, demo_users=rows, password=DEMO_PASSWORD)


@bp.post('/impersonate/<int:user_id>')
@login_required
def impersonate(user_id):
    _require_demo_controller()
    target = db.session.get(User, user_id)
    if not target or not target.is_demo:
        abort(404)
    controller_id = session.get('demo_controller_id') or current_user.id
    batch_id = session.get('demo_batch_id') or target.demo_batch_id
    login_user(target)
    session['demo_mode'] = True
    session['demo_controller_id'] = controller_id
    session['demo_batch_id'] = batch_id
    session['demo_viewing_as'] = f'{target.display_name} / {target.role_label}'
    flash(f'DEMO MODE: now viewing as {target.display_name}.', 'success')
    return redirect(url_for('dashboard.dashboard'))


@bp.post('/return-admin')
@login_required
def return_admin():
    controller_id = session.get('demo_controller_id')
    admin = db.session.get(User, controller_id) if controller_id else None
    if not admin or not is_site_owner(admin):
        abort(403)
    login_user(admin)
    session['demo_mode'] = True
    session['demo_controller_id'] = admin.id
    session.pop('demo_viewing_as', None)
    flash('Returned to the demo controller account.', 'success')
    return redirect(url_for('demo.dashboard'))


@bp.route('/workflows')
@login_required
def workflows():
    _require_demo_controller()
    return render_template('demo/workflows.html', title='Demo Workflow Launcher', user=current_user, launchers=WORKFLOW_LAUNCHERS)


@bp.route('/workflows/<record_type>')
@login_required
def workflow_detail(record_type):
    _require_demo_controller()
    rows = DemoRecord.query.filter_by(is_demo=True, record_type=record_type).order_by(DemoRecord.created_at.desc()).all()
    if not rows:
        abort(404)
    return render_template('demo/workflow_detail.html', title=f'Demo {record_type.upper()}', user=current_user, record_type=record_type, rows=rows)


@bp.route('/law-lookup')
@login_required
def law_lookup():
    _require_demo_controller()
    query = (request.args.get('q') or '').strip().lower()
    rows = DemoRecord.query.filter_by(is_demo=True, record_type='law_lookup').order_by(DemoRecord.title.asc()).all()
    results = []
    for row in rows:
        payload = json.loads(row.payload_json or '{}')
        haystack = ' '.join(str(payload.get(key, '')) for key in ('query', 'citation', 'title', 'why', 'excerpt')).lower()
        if not query or query in haystack:
            results.append(payload)
    return render_template('demo/law_lookup.html', title='Demo Law Lookup', user=current_user, query=query, results=results, examples=DEMO_LAW_RESULTS)


DEMO_SAMPLE_REPORTS = [
    {
        'id': 'demo-1',
        'incident_number': 'MCPD-2026-00141',
        'call_type': 'Domestic Disturbance',
        'occurred_date': '2026-05-12',
        'occurred_time': '20:47',
        'reported_time': '20:49',
        'location': 'Building 2200, MCLB Albany, GA',
        'disposition': 'Separated parties; subject transported to PMO for processing',
        'status': 'APPROVED',
        'officer': 'Ofc. Carter',
        'badge': 'MCPD-114',
        'supervisor': 'Sgt. Brooks',
        'parties': [
            {'role': 'Victim', 'name': 'Jane M. Doe', 'dob': '1994-03-11', 'id_type': 'Military ID', 'id_number': '2212-0311-A', 'phone': '(229) 555-0102', 'address': 'BEQ Bldg 2215 Rm 104, MCLB Albany'},
            {'role': 'Suspect', 'name': 'John R. Smith', 'dob': '1991-07-22', 'id_type': 'Military ID', 'id_number': '1918-0722-B', 'phone': '(229) 555-0178', 'address': 'BEQ Bldg 2215 Rm 106, MCLB Albany'},
            {'role': 'Witness', 'name': 'Cpl. Mark A. Lewis', 'dob': '1998-01-05', 'id_type': 'Military ID', 'id_number': '3041-0105-C', 'phone': '(229) 555-0135', 'address': 'BEQ Bldg 2215 Rm 110, MCLB Albany'},
        ],
        'narrative': (
            'On 2026-05-12 at approximately 2047 hours, this officer responded to a domestic disturbance call at Building 2200, '
            'MCLB Albany, GA, in reference to a verbal dispute that had escalated to a physical altercation. '
            'Upon arrival at 2051 hours, this officer was met by Cpl. Lewis who stated he had heard shouting and sounds of '
            'a physical struggle from Room 104 approximately ten minutes prior and called the PMO dispatch line at 2049 hours.\n\n'
            'This officer knocked on the door of Room 104 and was answered by Jane M. Doe, who appeared visibly distressed, '
            'had a red mark consistent with a slap on her left cheek, and was crying. Doe stated that John R. Smith had '
            'come to her room, began arguing about personal matters, and struck her on the face with an open hand. '
            'Smith was located in the hallway near the stairwell exit and was cooperative. Smith stated the altercation '
            'was verbal only and denied striking Doe. Parties were separated and interviewed independently.\n\n'
            'Supervisor Sgt. Brooks was notified at 2058 hours. Based on observable injury to Doe and conflicting statements, '
            'Smith was identified as the primary physical aggressor. Smith was transported to the PMO for further processing. '
            'Doe was offered medical assistance and declined. A civilian witness statement was obtained from Cpl. Lewis.\n\n'
            'Evidence: photographs taken of victim injury (attached, File Ref: MCPD-2026-00141-PHO-01 through 04). '
            'No weapons were involved. Scene was cleared at 2137 hours.'
        ),
        'paperwork': [
            {'form': 'Incident Report', 'completed': True},
            {'form': 'Witness Statement — Cpl. Lewis', 'completed': True},
            {'form': 'Victim Statement — Doe, Jane M.', 'completed': True},
            {'form': 'Use of Force Report', 'completed': False, 'note': 'Not applicable — no force used'},
            {'form': 'Evidence Form (Photographs)', 'completed': True},
        ],
        'supervisor_notes': 'Reviewed. Narrative complete and consistent with physical evidence. Approved for record.',
        'approved_by': 'Sgt. Brooks',
        'approved_date': '2026-05-12',
    },
    {
        'id': 'demo-2',
        'incident_number': 'MCPD-2026-00137',
        'call_type': 'Traffic Accident',
        'occurred_date': '2026-05-11',
        'occurred_time': '14:22',
        'reported_time': '14:24',
        'location': 'Main Gate Parking Lot C, MCLB Albany, GA',
        'disposition': 'No injuries; vehicles documented; one vehicle towed',
        'status': 'APPROVED',
        'officer': 'Ofc. Daniels',
        'badge': 'MCPD-107',
        'supervisor': 'Lt. Adams',
        'parties': [
            {'role': 'Driver 1', 'name': 'SSgt. Robert T. Hill', 'dob': '1988-09-14', 'id_type': 'Military ID', 'id_number': '0912-0914-D', 'phone': '(229) 555-0144', 'address': 'Housing Area, MCLB Albany'},
            {'role': 'Driver 2', 'name': 'Emily R. Pearson', 'dob': '1995-04-30', 'id_type': 'GA DL', 'id_number': 'GA-047-221-904', 'phone': '(229) 555-0199', 'address': '114 Warehouse Rd, Albany, GA 31701'},
            {'role': 'Witness', 'name': 'Ofc. Nguyen', 'dob': '', 'id_type': 'MCPD Badge', 'id_number': 'MCPD-112', 'phone': '', 'address': 'PMO, MCLB Albany'},
        ],
        'narrative': (
            'On 2026-05-11 at approximately 1422 hours, this officer responded to the Main Gate Parking Lot C, MCLB Albany, '
            'in reference to a two-vehicle traffic accident. Upon arrival at 1427 hours, this officer observed a gray 2019 '
            'Chevrolet Tahoe (GA plate: RZQ-4821) and a blue 2022 Honda Civic (GA plate: LKP-0093) in contact near the '
            'parking lot exit lane. Both vehicles sustained front-end damage.\n\n'
            'SSgt. Hill stated he was pulling forward out of a parking space and did not see the approaching Civic. '
            'Pearson stated she had the right of way in the exit lane and had no time to stop. No injuries were reported '
            'by either party. Ofc. Nguyen, who was on gate duty, observed the collision and confirmed the account of Pearson.\n\n'
            'A DD Form 1408 was completed for both operators. Photographs of damage and road position were taken '
            '(File Ref: MCPD-2026-00137-PHO-01 through 08). SSgt. Hill\'s vehicle was determined to be not drivable '
            'and was towed by Base Motor Transport. A vehicle impound form was completed. '
            'Supervisor Lt. Adams was notified at 1435 hours. Scene was cleared at 1519 hours.'
        ),
        'paperwork': [
            {'form': 'Incident/Accident Report', 'completed': True},
            {'form': 'DD Form 1408 — Driver 1', 'completed': True},
            {'form': 'DD Form 1408 — Driver 2', 'completed': True},
            {'form': 'Witness Statement — Ofc. Nguyen', 'completed': True},
            {'form': 'Vehicle Impound Form — SSgt. Hill Tahoe', 'completed': True},
            {'form': 'Evidence Form (Photographs)', 'completed': True},
        ],
        'supervisor_notes': 'Report complete. Diagram attached. No force. Vehicle tow confirmed. Approved.',
        'approved_by': 'Lt. Adams',
        'approved_date': '2026-05-11',
    },
]


@bp.route('/report-samples')
@login_required
def report_samples():
    _require_demo_controller()
    return render_template('demo/report_samples.html', title='Demo Report Samples', user=current_user, reports=DEMO_SAMPLE_REPORTS)


@bp.route('/report-samples/<report_id>')
@login_required
def report_sample_detail(report_id):
    _require_demo_controller()
    report = next((r for r in DEMO_SAMPLE_REPORTS if r['id'] == report_id), None)
    if not report:
        abort(404)
    return render_template('demo/report_sample_detail.html', title=f'Demo Report — {report["incident_number"]}', user=current_user, report=report)


@bp.route('/api/law-lookup')
@login_required
def law_lookup_api():
    _require_demo_controller()
    query = (request.args.get('q') or '').strip().lower()
    rows = DemoRecord.query.filter_by(is_demo=True, record_type='law_lookup').order_by(DemoRecord.title.asc()).all()
    results = []
    for row in rows:
        payload = json.loads(row.payload_json or '{}')
        haystack = ' '.join(str(payload.get(key, '')) for key in ('query', 'citation', 'title', 'why', 'excerpt')).lower()
        if not query or query in haystack:
            results.append(payload)
    return jsonify({'ok': True, 'query': query, 'results': results})
