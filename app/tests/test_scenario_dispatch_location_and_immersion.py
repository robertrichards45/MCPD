from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.routes.scenario_variants import build_run_context
from app.simulator.location_catalog import CRASH_LOCATIONS, PUBLIC_MCLB_ROADS


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='dispatch-location-ci').first()
        if user is None:
            user = User(
                username='dispatch-location-ci',
                name='Dispatch Location CI Controller',
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


def test_dispatched_call_families_use_building_number_and_named_location():
    for scenario_id in ('S001', 'S002', 'S003', 'S004', 'S006'):
        context = build_run_context(scenario_id, seed=246813579)
        assert context['building_number']
        assert context['location_display'].startswith('Bldg.')
        assert context['building_number'] in context['dispatch_variant']
        assert 'MCLB Albany' in context['dispatch_variant']
        assert 'library public area' not in context['dispatch_variant'].lower()


def test_traffic_scenario_uses_specific_road_location_and_building_landmark():
    context = build_run_context('S005', seed=975318642)
    assert context['location_display']
    assert 'Bldg.' in context['location_display']
    assert context['location_display'] in context['dispatch_variant']
    assert 'MCLB Albany' in context['dispatch_variant']


def test_s007_crash_dispatch_uses_named_public_mclb_road():
    context = build_run_context('S007', seed=471728056, previous_choices={})
    assert context['location_display'] in CRASH_LOCATIONS
    assert context['location_name'] == context['location_display']
    assert context['location_display'] in context['dispatch_variant']
    assert any(road in context['location_display'] for road in PUBLIC_MCLB_ROADS)
    assert 'MCLB Albany' in context['dispatch_variant']
    assert 'Installation roadway / crash scene' not in context['dispatch_variant']
    assert 'respond to a vehicle crash aboard the installation' not in context['dispatch_variant'].lower()


def test_s007_live_page_renders_same_named_road_in_cad_and_dispatch():
    _app, client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S007')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    with client.session_transaction() as s:
        context = s['sentinel_scenario_lab_v2']['run_context']
        location = context['location_display']
        dispatch = context['dispatch_variant']
    assert location in CRASH_LOCATIONS
    assert location in dispatch
    assert location in html
    assert dispatch in html
    assert 'Installation roadway / crash scene' not in html


def test_virtual_patrol_renders_same_run_location_and_immersion_controls():
    _app, client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    with client.session_transaction() as s:
        context = s['sentinel_scenario_lab_v2']['run_context']
        location = context['location_display']
        building = context['building_number']
    assert location in html
    assert building in html
    assert 'Dynamic Scene Board' in html
    assert 'NPC Voice: On' in html
    assert 'Play Dispatch' in html
    assert 'Mic · Dictate' in html
    assert 'Immersive Mode' in html
