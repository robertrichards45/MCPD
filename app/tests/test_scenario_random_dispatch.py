from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.routes.scenario_lab import SCENARIOS


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-random-ci').first()
        if user is None:
            user = User(
                username='scenario-random-ci',
                name='Scenario Random CI Controller',
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


def _random_call(client):
    response = client.post(
        '/sentinel/fto-center/scenario-lab/shift/launch',
        data={'_csrf_token': 'test-token', 'mode': 'random'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        launch = s['sentinel_scenario_launch_mode_v1']
        deck = list(s.get('sentinel_scenario_random_deck_v1') or [])
    return response, state, launch, deck


def test_random_call_is_server_selected_blind_and_not_current_scenario():
    _app, client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')

    response, state, launch, _deck = _random_call(client)
    html = response.get_data(as_text=True)

    assert state['scenario_id'] in SCENARIOS
    if len(SCENARIOS) > 1:
        assert state['scenario_id'] != 'S001'
    assert launch['mode'] == 'random'
    assert launch['scenario_id'] == state['scenario_id']
    assert 'BLIND DISPATCH' in html
    assert 'Blind Call Is Active' in html
    assert 'Play Dispatch' in html
    assert 'Immersive Mode' in html
    assert 'Mic · Dictate' in html


def test_random_dispatch_deck_does_not_repeat_until_drawn_pool_is_consumed():
    _app, client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')

    draw_count = min(6, len(SCENARIOS))
    draws = []
    deck_sizes = []
    for _ in range(draw_count):
        _response, state, launch, deck = _random_call(client)
        draws.append(state['scenario_id'])
        deck_sizes.append(len(deck))
        assert launch['mode'] == 'random'

    assert len(draws) == len(set(draws))
    if len(SCENARIOS) > 1:
        assert all(left != right for left, right in zip(draws, draws[1:]))
    assert deck_sizes == sorted(deck_sizes, reverse=True)


def test_targeted_launch_clears_blind_mode_and_starts_requested_family():
    _app, client = _client()
    _random_call(client)
    requested = next(iter(SCENARIOS.keys()))

    response = client.post(
        '/sentinel/fto-center/scenario-lab/shift/launch',
        data={'_csrf_token': 'test-token', 'mode': 'selected', 'scenario_id': requested},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        launch = s['sentinel_scenario_launch_mode_v1']

    assert state['scenario_id'] == requested
    assert launch == {'mode': 'selected', 'scenario_id': requested}
    assert 'BLIND DISPATCH' not in response.get_data(as_text=True)
