from app import create_app
from app.extensions import db
from app.models import (
    AuditLog,
    ROLE_PATROL_OFFICER,
    ROLE_WATCH_COMMANDER,
    User,
    WatchNote,
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


def test_incident_command_dashboard_loads_and_officer_blocked():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('ic_wc_route_test', ROLE_WATCH_COMMANDER)
        officer = _user('ic_officer_route_test', ROLE_PATROL_OFFICER)

        _app, wc_client = _client_for(wc)
        response = wc_client.get('/incident-command/dashboard')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Incident Command' in html
        assert 'Command-grade incident control board' in html
        assert 'Command / PAR Timers' in html
        assert 'Divisions / Groups' in html
        assert 'Tactical Worksheet' in html
        assert 'Command Threat Picture' in html

        _app, officer_client = _client_for(officer)
        response = officer_client.get('/incident-command/dashboard')
        assert response.status_code == 403


def test_incident_command_log_entry_creates_note_and_audit():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        wc = _user('ic_wc_log_test', ROLE_WATCH_COMMANDER)
        _app, client = _client_for(wc)

        response = client.post(
            '/incident-command/log',
            data={
                'note_type': 'incident_objective',
                'priority': 'Command Critical',
                'title': 'Set inner perimeter',
                'body': 'Inner perimeter established around the scene. PAR due in 30 minutes.',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert WatchNote.query.filter_by(title='Set inner perimeter', note_type='incident_objective').first() is not None
        assert AuditLog.query.filter_by(action='incident_command_log_added').first() is not None
