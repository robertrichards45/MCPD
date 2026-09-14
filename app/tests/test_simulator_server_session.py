import json

from app import create_app
from app.extensions import db
from app.fto_models import FTOScenarioRun
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SIMULATOR_SERVER_BACKED_SESSION'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-server-session-ci').first()
        if user is None:
            user = User(
                username='scenario-server-session-ci',
                name='Scenario Server Session CI',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return app, client


def test_active_simulator_world_is_db_backed_and_session_stays_small():
    app, client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    assert response.status_code == 200

    with client.session_transaction() as s:
        handle = dict(s['sentinel_scenario_lab_v2'])
        assert handle['_sentinel_server_state'] is True
        assert handle['scenario_id'] == 'S003'
        assert handle['run_id'].startswith('S003-')
        assert 'world' not in handle
        assert 'dialogue' not in handle
        run_id = handle['run_id']

    with app.app_context():
        run = FTOScenarioRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        saved = json.loads(run.state_json)
        assert saved['scenario_id'] == 'S003'
        assert saved['world']['truth']['scenario_id'] == 'S003'

    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S003',
            'action': 'radio',
            'radio_text': '214, show me on scene.',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with client.session_transaction() as s:
        handle = dict(s['sentinel_scenario_lab_v2'])
        assert handle['_sentinel_server_state'] is True
        assert handle['run_id'] == run_id
        assert 'world' not in handle

    with app.app_context():
        run = FTOScenarioRun.query.filter_by(run_id=run_id).first()
        saved = json.loads(run.state_json)
        assert saved['world']['officer']['location'] == 'scene'
        assert any(row.get('speaker') == 'Trainee' for row in saved['world']['radio_log'])


def test_missing_server_run_handle_starts_a_new_run():
    _app, client = _client()
    with client.session_transaction() as s:
        s['sentinel_scenario_lab_v2'] = {
            '_sentinel_server_state': True,
            'scenario_id': 'S001',
            'run_id': 'S001-999999999',
        }

    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    assert response.status_code == 200
    with client.session_transaction() as s:
        handle = dict(s['sentinel_scenario_lab_v2'])
        assert handle['_sentinel_server_state'] is True
        assert handle['scenario_id'] == 'S001'
        assert handle['run_id'] != 'S001-999999999'
