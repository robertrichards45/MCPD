from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-location-voice-ci').first()
        if user is None:
            user = User(
                username='scenario-location-voice-ci',
                name='Scenario Location Voice CI',
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


def test_public_training_catalog_uses_handbook_facilities_without_sensitive_security_entries():
    from app.simulator.location_catalog import SAFE_TRAINING_FACILITIES

    values = set(SAFE_TRAINING_FACILITIES.values())
    assert 'Bldg. 7501 — Commissary' in values
    assert 'Bldg. 7960 — Fitness Center' in values
    assert 'Bldg. 7727 — Credit Union' in values
    assert 'Bldg. 7500 — Marine Corps Exchange' in values
    assert 'Bldg. 3500 — LOGCOM Headquarters' in values

    combined = ' | '.join(values)
    # Security-sensitive checklist entries must not be copied into the public catalog.
    for sensitive_number in ('5501', '3700', '3701', '7105', '5080', '5082'):
        assert f'Bldg. {sensitive_number}' not in combined


def test_dispatched_call_carries_same_handbook_building_into_run_context_and_text():
    from app.routes.scenario_variants import build_run_context

    context = build_run_context('S001', seed=123456789, previous_choices={})
    assert context['building_number']
    assert context['location_display'].startswith('Bldg. ')
    assert context['building_number'] in context['location_display']
    assert context['location_display'] in context['dispatch_variant']
    assert 'MCLB Albany' in context['dispatch_variant']


def test_dispatch_voice_endpoint_only_voices_active_scenario_dispatch(monkeypatch):
    app, client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')

    captured = {}

    def fake_audio(text):
        captured['text'] = text
        return b'fake-mp3-audio'

    import app.routes.scenario_shift as route
    monkeypatch.setattr(route, '_natural_dispatch_audio', fake_audio)

    response = client.get('/sentinel/fto-center/scenario-lab/shift/voice/dispatch')
    assert response.status_code == 200
    assert response.mimetype == 'audio/mpeg'
    assert response.data == b'fake-mp3-audio'
    assert captured['text']
    assert 'Unit 214' in captured['text']
    assert response.headers.get('X-Sentinel-Synthetic-Voice') == 'true'


def test_dispatch_voice_returns_browser_fallback_signal_when_server_tts_is_unavailable(monkeypatch):
    _app, client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')

    import app.routes.scenario_shift as route
    monkeypatch.setattr(route, '_natural_dispatch_audio', lambda _text: None)

    response = client.get('/sentinel/fto-center/scenario-lab/shift/voice/dispatch')
    assert response.status_code == 503
    assert response.headers.get('X-Sentinel-Voice-Fallback') == 'browser'


def test_dispatch_voice_ui_prefers_server_generated_audio():
    _app, client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Play Dispatch' in html

    # The global voice helper is loaded by base.html and should be responsible for
    # intercepting the dispatch buttons before the older browser TTS listener.
    voice_js = client.get('/static/js/voice_assistant.js')
    script = voice_js.get_data(as_text=True)
    assert '/sentinel/fto-center/scenario-lab/shift/voice/dispatch' in script
    assert 'playNaturalSentinelDispatch' in script
    assert 'AI-generated dispatcher voice' in script
