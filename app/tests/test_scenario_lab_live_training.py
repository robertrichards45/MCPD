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
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user.id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return client


def test_live_contact_answers_without_clearing_call_phase():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'ask_actor',
        'actor_id': 'dispatch',
        'question_text': 'Has a weapon been reported?'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'No confirmed weapon information has been developed.' in html
    assert 'Arrival' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['turn'] == 0
        assert state['actor_interactions'] == 1
        assert state['engine']['clock'] >= 1
        assert 'Has a weapon been reported?' not in str(state)


def test_future_actor_is_not_available_early():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'ask_actor',
        'actor_id': 'subject',
        'question_text': 'Tell me what happened.'
    }, follow_redirects=True)
    assert 'not available in the current call state' in response.get_data(as_text=True)


def test_restart_same_scenario_family_changes_fact_pattern():
    client = _client()
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
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'act',
        'response_text': 'I shoot the person immediately even though no deadly threat has been presented.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Terminal Training Outcome' in html
    assert 'Exercise terminated' in html
    assert 'Immediate FTO alert required' in html
    assert 'Continue to Next Scenario' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['terminated'] is True
        assert state['complete'] is True
        assert state['fto_alert'] is True


def test_terminal_outcome_moves_to_next_scenario_with_new_run():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'act',
        'response_text': 'I shoot the person even though there is no deadly threat.'
    }, follow_redirects=True)
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'next'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Suspicious Vehicle at Main Gate' in html
    assert 'Run Identifier' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['scenario_id'] == 'S002'
        assert state['terminated'] is False
        assert state['run_context']['run_id'].startswith('S002-')
