from app import create_app
from app.extensions import db
from app.fto_models import FTOScenarioRun
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.action_interpreter import interpret_action
from app.simulator.dispatch_engine import handle_radio_transmission
from app.simulator.world_state import advance_world_clock, apply_interpreted_actions, ensure_world_state


def _client(username='sim-platform-controller'):
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(
                username=username,
                name='Simulator Platform Controller',
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
    return app, client, user_id


def _types(text, channel='scene'):
    return {row['action_type'] for row in interpret_action(text, channel=channel, use_ai=False)}


def test_equivalent_backup_language_maps_to_same_canonical_action():
    phrases = (
        'I want another unit.',
        '214, send me a cover unit.',
        'Dispatch, start somebody else this way.',
        "I'm going to wait for backup before going inside.",
    )
    for phrase in phrases:
        assert 'request_backup' in _types(phrase, channel='radio' if '214' in phrase or 'Dispatch' in phrase else 'scene'), phrase


def test_negation_does_not_turn_discussion_into_enforcement_or_force():
    actions = _types("I don't have probable cause to arrest him, so I would not arrest him.")
    assert 'arrest' not in actions
    assert 'legal_assessment' in actions
    assert 'no_enforcement' in actions

    force_actions = _types('I would not shoot anyone because I have not seen a deadly threat.')
    assert 'deadly_force' not in force_actions

    search_actions = _types('I do not have authority to search the vehicle, so I will not search it.')
    assert 'search' not in search_actions
    assert 'legal_assessment' in search_actions


def test_synthetic_records_return_after_time_delay_and_remain_stable():
    state = {
        'scenario_id': 'S005',
        'run_context': {'seed': 123456789, 'run_id': 'S005-123456789'},
    }
    ensure_world_state(state, 'S005')
    text = '214, run Georgia OLN 123456789.'
    actions = interpret_action(text, channel='radio', use_ai=False)
    handle_radio_transmission(state, actions, text, state['run_context'])
    assert state['world']['records']
    stored = dict(state['world']['records'])
    apply_interpreted_actions(state, actions, raw_text=text, channel='radio')
    assert any(row.get('metadata', {}).get('type') == 'records' for row in state['world']['pending_radio'])
    advance_world_clock(state, 1)
    returns = [row for row in state['world']['radio_log'] if row.get('metadata', {}).get('type') == 'records']
    assert returns
    assert state['world']['records'] == stored
    assert all(row.get('synthetic') is True for row in state['world']['records'].values())


def test_simulation_mode_hides_evaluator_state_but_evaluator_mode_exposes_it():
    app, client, _user_id = _client('sim-mode-split-controller')
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S005')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Sentinel Virtual Patrol Simulator' in html
    assert 'Scene Risk' not in html
    assert 'Hidden World State' not in html
    assert 'Unresolved / missed' not in html

    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    response = client.get(f'/sentinel/fto-center/scenario-lab/evaluator/{run_id}')
    evaluator_html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Sentinel — FTO / Evaluator Mode' in evaluator_html
    assert 'Hidden World State' in evaluator_html
    assert 'Evaluator Evidence' in evaluator_html
    assert 'NPC Minds' in evaluator_html

    with app.app_context():
        run = FTOScenarioRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.status == 'ACTIVE'
        assert run.state_json


def test_instructor_can_pause_and_enable_coaching_without_changing_truth():
    _app, client, _user_id = _client('sim-control-controller')
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']
        seed = s['sentinel_scenario_lab_v2']['run_context']['seed']

    response = client.post(
        f'/sentinel/fto-center/scenario-lab/evaluator/{run_id}/control',
        data={'_csrf_token': 'test-token', 'control': 'pause'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'Resume Simulation' in response.get_data(as_text=True)

    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    paused_html = response.get_data(as_text=True)
    assert 'Paused by FTO.' in paused_html
    assert 'call state is preserved' in paused_html
    with client.session_transaction() as s:
        assert s['sentinel_scenario_lab_v2']['run_context']['seed'] == seed
        assert s['sentinel_scenario_lab_v2']['world']['paused'] is True

    client.post(
        f'/sentinel/fto-center/scenario-lab/evaluator/{run_id}/control',
        data={'_csrf_token': 'test-token', 'control': 'resume'},
        follow_redirects=True,
    )
    client.post(
        f'/sentinel/fto-center/scenario-lab/evaluator/{run_id}/control',
        data={'_csrf_token': 'test-token', 'control': 'coaching_on'},
        follow_redirects=True,
    )
    client.post(
        f'/sentinel/fto-center/scenario-lab/evaluator/{run_id}/control',
        data={
            '_csrf_token': 'test-token',
            'control': 'coach',
            'message': 'What fact do you still need before choosing a disposition?',
        },
        follow_redirects=True,
    )
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    html = response.get_data(as_text=True)
    assert 'FTO Coaching' in html
    assert 'What fact do you still need before choosing a disposition?' in html


def test_terminal_run_persists_after_action_review_and_replay_events():
    app, client, _user_id = _client('sim-review-controller')
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S001',
            'action': 'officer_action',
            'command_text': 'I shoot the person even though no deadly threat is presented.',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    review = client.get(f'/sentinel/fto-center/scenario-lab/review/{run_id}')
    html = review.get_data(as_text=True)
    assert review.status_code == 200
    assert 'Virtual Patrol Debrief' in html
    assert 'Call Timeline' in html
    assert 'Terminal Outcome' in html
    assert 'not an automatic DOR rating' in html

    with app.app_context():
        run = FTOScenarioRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.status == 'TERMINATED'
        assert run.events.count() >= 2
        snapshots = [event.world_snapshot_json for event in run.events.all()]
        assert all(snapshot for snapshot in snapshots)
