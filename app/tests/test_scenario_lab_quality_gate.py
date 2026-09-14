from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-gate-ci').first()
        if user is None:
            user = User(username='scenario-gate-ci', name='Scenario Gate CI Controller', role=ROLE_WEBSITE_CONTROLLER, active=True, pending_approval=False)
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return client


def test_weak_answer_does_not_advance():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'act',
        'response_text': 'I just handle it and move on.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Decision 1 of 4' in html
    assert 'Decision held' in html or 'FTO intervention' in html
    assert 'A staff member meets you outside' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['turn'] == 0
        assert state['revision_count'] == 1


def test_stage_specific_answer_advances_and_releases_new_facts():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'act',
        'response_text': 'I advise dispatch I am on scene, maintain safe distance, contact the reporting staff member for initial facts, and request another unit if risk warrants it.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Decision accepted' in html
    assert 'Decision 2 of 4' in html
    assert 'A staff member meets you outside' in html


def test_coaching_is_locked_until_sustained_effort():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S003', 'action': 'hint'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Coaching is still locked' in html
    with client.session_transaction() as s:
        assert s['sentinel_scenario_lab_v2']['hint_count'] == 0

    for _ in range(3):
        client.post('/sentinel/fto-center/scenario-lab/', data={
            '_csrf_token': 'test-token', 'scenario_id': 'S003', 'action': 'act',
            'response_text': 'I am not sure what to do here, so I would deal with it somehow.'
        }, follow_redirects=True)

    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S003', 'action': 'hint'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'FTO coaching question' in html
    assert 'Decision 1 of 4' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['turn'] == 0
        assert state['hint_count'] == 1


def test_finish_cannot_bypass_remaining_decisions():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S006', 'action': 'finish'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Complete every decision point before finishing' in html
    assert 'Decision 1 of 4' in html
    assert 'FTO Coaching Review' not in html
