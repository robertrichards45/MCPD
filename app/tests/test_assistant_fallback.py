from app import create_app
from app.models import User
from app.services import ai_client


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
            session['_csrf_token'] = 'test-token'
    return client


def test_assistant_returns_local_report_help_when_ai_key_missing(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    client = _logged_in_client()
    response = client.post(
        '/api/assistant/ask',
        json={'message': 'How do I start a report?'},
        headers={'X-CSRFToken': 'test-token'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert payload['mode'] == 'local_fallback'
    assert 'Start Report' in payload['reply']
    assert '/reports/new' in payload['reply']


def test_assistant_returns_local_law_lookup_help_when_ai_key_missing(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    client = _logged_in_client()
    response = client.post(
        '/api/assistant/ask',
        json={'message': 'What charge applies if someone came back on base after being barred?'},
        headers={'X-CSRFToken': 'test-token'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert payload['mode'] == 'local_fallback'
    assert 'Law Lookup' in payload['reply']
    assert '/legal/search' in payload['reply']


def test_assistant_status_reports_missing_key_to_site_controller(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    client = _logged_in_client()
    response = client.get('/api/assistant/status')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True
    assert payload['openai']['configured'] is False
    assert payload['openai']['errorCode'] == 'missing_key'


def test_openai_key_status_uses_configured_model_without_exposing_key(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {'output_text': 'ok'}

    captured = {}

    def fake_post(_url, headers=None, data=None, timeout=None):
        captured['auth'] = headers.get('Authorization')
        captured['data'] = data
        captured['timeout'] = timeout
        return FakeResponse()

    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-secret-value')
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-test-model')
    monkeypatch.setattr(ai_client.requests, 'post', fake_post)

    status = ai_client.openai_key_status()

    assert status['ok'] is True
    assert status['configured'] is True
    assert status['model'] == 'gpt-test-model'
    assert 'sk-test-secret-value' not in str(status)
    assert captured['auth'] == 'Bearer sk-test-secret-value'
    assert '"model": "gpt-test-model"' in captured['data']


def test_openai_key_status_redacts_error_key_fragments(monkeypatch):
    class FakeResponse:
        status_code = 401

        def json(self):
            return {
                'error': {
                    'code': 'invalid_api_key',
                    'message': 'Incorrect API key provided: sk-proj-abc123456789SECRET.',
                }
            }

    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-secret-value')
    monkeypatch.setattr(ai_client.requests, 'post', lambda *args, **kwargs: FakeResponse())

    status = ai_client.openai_key_status()

    assert status['ok'] is False
    assert status['errorCode'] == 'invalid_api_key'
    assert '[redacted OpenAI key]' in status['message']
    assert 'sk-proj' not in status['message']


def test_openai_tts_uses_fast_default_model(monkeypatch):
    class FakeResponse:
        status_code = 200
        content = b'audio'

    captured = {}

    def fake_post(_url, headers=None, data=None, timeout=None):
        captured['data'] = data
        return FakeResponse()

    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-secret-value')
    monkeypatch.delenv('OPENAI_TTS_MODEL', raising=False)
    monkeypatch.setattr(ai_client.requests, 'post', fake_post)

    audio = ai_client.openai_tts('Test audio.', None, voice='coral')

    assert audio == b'audio'
    assert '"model": "tts-1"' in captured['data']
    assert '"speed": 0.95' in captured['data']


def test_openai_tts_accepts_safe_speed(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b'audio'

    def fake_post(_url, headers=None, data=None, timeout=None):
        captured['data'] = data
        return FakeResponse()

    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-secret-value')
    monkeypatch.setattr(ai_client.requests, 'post', fake_post)

    audio = ai_client.openai_tts('Test audio.', None, voice='coral', speed=1.18)

    assert audio == b'audio'
    assert '"speed": 1.18' in captured['data']
