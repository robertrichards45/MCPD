from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-live-ci').first()
        if user is None:
            user = User(username='scenario-live-ci', name='Scenario Live CI Controller', role=ROLE_WEBSITE_CONTROLLER, active=True, pending_approval=False)
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return app, client, user_id


def test_face_to_face_question_uses_npc_memory_without_exposing_future_actor():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'officer_action',
        'command_text': "I talk to the Staff Member. Ma'am, what happened?"
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Staff Member' in html
    assert 'Subject — Subject' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['actor_interactions'] >= 1
        assert state['world']['people']['staff']['memory']
        assert 'subject' not in state['world']['people'] or not state['world']['people']['subject'].get('discovered')


def test_radio_and_records_are_separate_from_face_to_face_contact():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S005')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S005', 'action': 'radio',
        'radio_text': '214, show me on scene and run Georgia OLN 123456789.'
    }, follow_redirects=True)
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        radio = state['world']['radio_log']
        assert any(item['speaker'] == 'Trainee' for item in radio)
        assert state['world']['records']
        assert any(item.get('metadata', {}).get('type') == 'records' for item in state['world']['pending_radio'])

    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S005', 'action': 'officer_action',
        'command_text': 'I look through the windshield and check the driver hands.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Dispatch' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert any(item.get('metadata', {}).get('type') == 'records' for item in state['world']['radio_log'])


def test_restart_same_scenario_family_changes_fact_pattern():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')
    with client.session_transaction() as s:
        first = dict(s['sentinel_scenario_lab_v2']['run_context']['choices'])
        first_run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S006', 'action': 'reset'
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as s:
        second = dict(s['sentinel_scenario_lab_v2']['run_context']['choices'])
        second_run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    assert second_run_id != first_run_id
    assert second != first


def test_catastrophic_deadly_force_decision_terminates_exercise_and_flags_fto():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'officer_action',
        'command_text': 'I shoot the person immediately even though no deadly threat has been presented.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Simulation Ended' in html
    assert 'deadly-force decision unsupported' in html
    assert 'After-Action Review' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['terminated'] is True
        assert state['complete'] is True
        assert state['fto_alert'] is True
        assert any(item['event_type'] == 'terminal_outcome' for item in state['world']['timeline'])


def test_negated_deadly_force_statement_does_not_terminate_run():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'officer_action',
        'command_text': 'I would not shoot anyone because I have not observed a deadly threat.'
    }, follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['terminated'] is False
        assert not any(row.get('action_type') == 'deadly_force' for row in state['world']['last_actions'])


def test_terminal_outcome_moves_to_next_scenario_with_hidden_new_run_id():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'officer_action',
        'command_text': 'I shoot the person even though there is no deadly threat.'
    }, follow_redirects=True)
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'next'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Suspicious Vehicle at Main Gate' in html
    assert 'Run S002-' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['scenario_id'] == 'S002'
        assert state['terminated'] is False
        assert state['run_context']['run_id'].startswith('S002-')
