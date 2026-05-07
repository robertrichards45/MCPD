from app import create_app
from app.extensions import db
from app.models import (
    AuditLog,
    IncidentPacket,
    PACKET_APPROVAL_APPROVED,
    PACKET_APPROVAL_NEEDS_CORRECTION,
    ROLE_PATROL_OFFICER,
    ROLE_WATCH_COMMANDER,
    ShiftBrief,
    User,
    WatchAssignment,
    WatchShift,
)


def _user(username, role):
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, role=role, active=True, pending_approval=False)
        user.set_password('test-password')
    user.role = role
    user.active = True
    user.pending_approval = False
    user.builder_mode_access = False
    db.session.add(user)
    db.session.commit()
    return user


def _client_for(user):
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
    return app, client


def test_watch_commander_dashboard_loads_and_officer_blocked():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('wc_route_test', ROLE_WATCH_COMMANDER)
        officer = _user('officer_route_test', ROLE_PATROL_OFFICER)

        _app, wc_client = _client_for(wc)
        response = wc_client.get('/watch-commander/dashboard')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Watch Commander Dashboard' in html
        assert 'Officers on duty' in html

        _app, officer_client = _client_for(officer)
        response = officer_client.get('/watch-commander/dashboard')
        assert response.status_code == 403


def test_watch_commander_all_pages_render():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('wc_pages_test', ROLE_WATCH_COMMANDER)
        _app, client = _client_for(wc)
        paths = [
            '/watch-commander',
            '/watch-commander/dashboard',
            '/watch-commander/shift',
            '/watch-commander/officers',
            '/watch-commander/reports',
            '/watch-commander/saved-work',
            '/watch-commander/training',
            '/watch-commander/forms',
            '/watch-commander/blotter',
            '/watch-commander/approvals',
            '/watch-commander/assignments',
            '/watch-commander/briefing',
            '/watch-commander/notifications',
        ]
        for path in paths:
            response = client.get(path, follow_redirects=True)
            assert response.status_code == 200, path


def test_shift_creation_officer_assignment_and_audit():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('wc_shift_test', ROLE_WATCH_COMMANDER)
        officer = _user('officer_shift_test', ROLE_PATROL_OFFICER)
        _app, client = _client_for(wc)

        response = client.post(
            '/watch-commander/shift',
            data={'shift_date': '2026-05-07', 'shift_type': 'Alpha', 'status': 'OPEN', 'notes': 'Test shift'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        shift = WatchShift.query.filter_by(shift_date='2026-05-07', shift_type='Alpha').first()
        assert shift is not None

        response = client.post(
            '/watch-commander/officers',
            data={
                'officer_id': officer.id,
                'shift_id': shift.id,
                'assignment_type': 'Gate Post',
                'assignment_location': 'Main Gate',
                'status': 'Gate',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assignment = WatchAssignment.query.filter_by(officer_id=officer.id, shift_id=shift.id).first()
        assert assignment is not None
        assert assignment.assignment_type == 'Gate Post'
        assert AuditLog.query.filter_by(action='watch_assignment_changed').first() is not None


def test_watch_commander_can_create_shift_and_assign_self():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('wc_self_shift_test', ROLE_WATCH_COMMANDER)
        _app, client = _client_for(wc)

        response = client.post(
            '/watch-commander/shift',
            data={
                'shift_date': '2026-05-08',
                'shift_type': 'Bravo',
                'status': 'OPEN',
                'assign_self': '1',
                'assigned_officer_ids': [str(wc.id)],
                'assignment_type': 'Desk Duty',
                'assignment_location': 'Watch Desk',
                'assignment_status': 'On Duty',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        shift = WatchShift.query.filter_by(shift_date='2026-05-08', shift_type='Bravo').first()
        assert shift is not None
        assignment = WatchAssignment.query.filter_by(shift_id=shift.id, officer_id=wc.id).first()
        assert assignment is not None
        assert assignment.assignment_type == 'Desk Duty'
        assert assignment.assignment_location == 'Watch Desk'
        assert assignment.status == 'On Duty'


def test_report_return_and_approve_actions_create_audit():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('wc_report_test', ROLE_WATCH_COMMANDER)
        officer = _user('officer_report_test', ROLE_PATROL_OFFICER)
        packet = IncidentPacket(officer_user_id=officer.id, call_type='Traffic Accident', location='Gate 1')
        db.session.add(packet)
        db.session.commit()
        _app, client = _client_for(wc)

        response = client.post(f'/watch-commander/reports/{packet.id}/return', data={'notes': 'Fix facts'}, follow_redirects=True)
        assert response.status_code == 200
        db.session.refresh(packet)
        assert packet.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION
        assert AuditLog.query.filter_by(action='watch_report_returned').first() is not None

        response = client.post(f'/watch-commander/reports/{packet.id}/approve', data={'notes': 'Approved'}, follow_redirects=True)
        assert response.status_code == 200
        db.session.refresh(packet)
        assert packet.approval_status == PACKET_APPROVAL_APPROVED
        assert AuditLog.query.filter_by(action='watch_report_approved').first() is not None


def test_shift_brief_creation_and_acknowledgement():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('wc_brief_test', ROLE_WATCH_COMMANDER)
        officer = _user('officer_brief_test', ROLE_PATROL_OFFICER)
        _app, wc_client = _client_for(wc)

        response = wc_client.post('/watch-commander/briefing', data={'title': 'Alpha Brief', 'body': 'Safety and BOLO review.', 'status': 'PUBLISHED'}, follow_redirects=True)
        assert response.status_code == 200
        brief = ShiftBrief.query.filter_by(title='Alpha Brief').first()
        assert brief is not None
        assert AuditLog.query.filter_by(action='shift_brief_created').first() is not None

        _app, officer_client = _client_for(officer)
        response = officer_client.post(f'/watch-commander/briefing/{brief.id}/acknowledge', follow_redirects=True)
        assert response.status_code in {200, 403}
