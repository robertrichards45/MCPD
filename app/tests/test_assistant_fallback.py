from app import create_app
from app.models import User


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
