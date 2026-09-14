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
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return client


def test_weak_action_does_not_advance_but_evaluator_result_stays_hidden():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={'_csrf_token':'test-token','scenario_id':'S001','action':'officer_action','command_text':'I just handle it and move on.'}, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Virtual Patrol' in html
    assert 'Decision held' not in html
    assert 'FTO intervention' not in html
    assert 'Demonstrated' not in html
    assert 'Still unresolved' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['turn'] == 0
        assert state['revision_count'] >= 1
        assert state['last_feedback']['accepted'] is False
        assert state['world']['clock'] >= 1


def test_separate_natural_actions_accumulate_without_magic_paragraph():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    client.post('/sentinel/fto-center/scenario-lab/', data={'_csrf_token':'test-token','scenario_id':'S001','action':'radio','radio_text':'214, show me on scene.'}, follow_redirects=True)
    client.post('/sentinel/fto-center/scenario-lab/', data={'_csrf_token':'test-token','scenario_id':'S001','action':'officer_action','command_text':'I position where I can see the entrance and keep some distance.'}, follow_redirects=True)
    response = client.post('/sentinel/fto-center/scenario-lab/', data={'_csrf_token':'test-token','scenario_id':'S001','action':'officer_action','command_text':"I want to talk to the Staff Member first. Ma'am, tell me exactly what happened."}, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Decision accepted' not in html
    assert 'Current Scene' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['turn'] >= 1
        assert state['semantic_actions']['0']


def test_normal_evaluation_has_no_automated_hint_path():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={'_csrf_token':'test-token','scenario_id':'S003','action':'hint'}, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Evaluation runs do not provide automated hints' in html
    assert 'FTO Coaching Locked' not in html
    with client.session_transaction() as s:
        assert s['sentinel_scenario_lab_v2']['hint_count'] == 0
        assert s['sentinel_scenario_lab_v2']['world']['coaching_mode'] is False


def test_live_simulation_hides_internal_engine_and_legal_research():
    client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S005')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    for hidden_label in ('Scene Risk','Core Phases Cleared','Branch Events','Immediate FTO Feedback','Still unresolved','Complaint exposure','Force review','Legal / Policy Research Unlocked','Training Objective'):
        assert hidden_label not in html
    assert 'CAD / Dispatch' in html
    assert 'Current Scene' in html
    assert 'Radio' in html
    assert 'Officer Action' in html
    assert 'People / Resources' in html
    assert 'Information / Evidence' in html
