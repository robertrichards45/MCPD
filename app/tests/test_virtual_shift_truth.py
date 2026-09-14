import json

from app import create_app
from app.extensions import db
from app.fto_models import FTOScenarioRun
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.routes.scenario_variants import build_run_context
from app.simulator.evidence_engine import initialize_truth_and_evidence, tick_evidence
from app.simulator.scenario_truth import build_scenario_truth
from app.simulator.time_engine import apply_time_consequences
from app.simulator.world_state import ensure_world_state, observable_world


def _client(username='virtual-shift-ci'):
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(
                username=username,
                name='Virtual Shift CI Controller',
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


def test_virtual_shift_uses_same_seed_for_cad_and_assigned_run():
    _app, client = _client('virtual-shift-seed-ci')
    response = client.post(
        '/sentinel/fto-center/scenario-lab/shift/',
        data={'_csrf_token': 'test-token', 'action': 'start', 'unit_id': '214'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    shift_html = response.get_data(as_text=True)
    assert 'Sentinel — Virtual Shift' in shift_html
    assert 'CAD has assigned an active call' in shift_html

    with client.session_transaction() as s:
        shift = dict(s['sentinel_virtual_shift_v1'])
        scenario_id = shift['active_scenario_id']
        call_seed = shift['active_call_seed']
        dispatch_text = shift['active_dispatch_text']
        assert scenario_id
        assert call_seed
        assert dispatch_text
        assert scenario_id not in shift_html

    response = client.post(
        '/sentinel/fto-center/scenario-lab/shift/',
        data={'_csrf_token': 'test-token', 'action': 'respond'},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Sentinel — Simulation Mode' in html
    assert 'Shift CAD' in html
    assert 'New Training Run' not in html
    assert 'Run S00' not in html
    assert dispatch_text in html

    with client.session_transaction() as s:
        shift = s['sentinel_virtual_shift_v1']
        state = s['sentinel_scenario_lab_v2']
        assert state['scenario_id'] == scenario_id
        assert state['run_context']['seed'] == call_seed
        assert state['run_context']['dispatch_variant'] == dispatch_text
        assert shift['active_run_id'] == state['run_context']['run_id']
        assert state['shift_context']['shift_id'] == shift['shift_id']
        assert state['shift_context']['call_number'] == shift['call_index']


def test_completed_shift_call_updates_clock_history_and_dispatches_different_next_call():
    app, client = _client('virtual-shift-lifecycle-ci')
    client.post(
        '/sentinel/fto-center/scenario-lab/shift/',
        data={'_csrf_token': 'test-token', 'action': 'start', 'unit_id': '214'},
        follow_redirects=True,
    )
    client.post(
        '/sentinel/fto-center/scenario-lab/shift/',
        data={'_csrf_token': 'test-token', 'action': 'respond'},
        follow_redirects=True,
    )

    with client.session_transaction() as s:
        before = dict(s['sentinel_virtual_shift_v1'])
        run_id = before['active_run_id']
        first_scenario = before['active_scenario_id']
        first_dispatched = before['active_dispatched_minute']

    with app.app_context():
        run = FTOScenarioRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        state = json.loads(run.state_json)
        state['complete'] = True
        state['world']['clock'] = 6
        run.status = 'COMPLETED'
        run.state_json = json.dumps(state, sort_keys=True)
        db.session.commit()

    response = client.get('/sentinel/fto-center/scenario-lab/shift/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'copy you clear and available' in html

    with client.session_transaction() as s:
        shift = s['sentinel_virtual_shift_v1']
        assert shift['calls_completed'] == 1
        assert len(shift['history']) == 1
        completed = shift['history'][0]
        assert completed['run_id'] == run_id
        assert completed['duration_minutes'] == 6
        assert completed['dispatched_minute'] == first_dispatched
        assert completed['cleared_minute'] >= first_dispatched + 6
        assert shift['active_scenario_id']
        assert shift['active_scenario_id'] != first_scenario
        assert shift['active_run_id'] is None
        assert shift['clock_minutes'] > completed['cleared_minute']


def _context_for_video_expiry():
    for seed in range(100000001, 100000500):
        context = build_run_context('S004', seed=seed)
        if context['choices'].get('video') == 'video exists but has not been preserved yet':
            return context
    raise AssertionError('No deterministic video-expiry seed found in search range.')


def test_undiscovered_video_can_expire_without_tipping_trainee():
    context = _context_for_video_expiry()
    state = {'scenario_id': 'S004', 'run_context': context}
    truth = build_scenario_truth('S004', context)
    initialize_truth_and_evidence(state, 'S004', truth)
    world = ensure_world_state(state, 'S004')
    video = world['evidence']['retail_video']
    assert video['status'] == 'hidden'
    world['clock'] = int(video['expires_at'])

    tick_evidence(state)
    assert world['evidence']['retail_video']['status'] == 'lost'
    lost_events = [row for row in world['timeline'] if row['event_type'] == 'evidence_lost']
    assert lost_events
    assert lost_events[-1]['visible_to_trainee'] is False

    visible = observable_world(state)
    assert all(row['id'] != 'retail_video' for row in visible['evidence'])
    assert all('no longer available' not in row['summary'] for row in visible['timeline'])


def _context_for_departing_witness():
    for seed in range(100000001, 100000500):
        context = build_run_context('S006', seed=seed)
        if context['choices'].get('witness_pattern') == 'one employee may have seen the entire event but is about to leave':
            return context
    raise AssertionError('No deterministic departing-witness seed found in search range.')


def test_undiscovered_witness_can_leave_without_becoming_visible():
    context = _context_for_departing_witness()
    state = {'scenario_id': 'S006', 'run_context': context}
    truth = build_scenario_truth('S006', context)
    initialize_truth_and_evidence(state, 'S006', truth)
    world = ensure_world_state(state, 'S006')
    world['clock'] = 6

    apply_time_consequences(state)
    assert 'fullwitness' in world['departed_actor_ids']
    departure = [row for row in world['timeline'] if row['event_type'] == 'person_departed'][-1]
    assert departure['visible_to_trainee'] is False
    visible = observable_world(state)
    assert all(row['id'] != 'fullwitness' for row in visible['people'])
    assert all('leaves the scene' not in row['summary'] for row in visible['timeline'])
