from app import create_app
from app.models import User
from app.routes import auth, dashboard


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
    return client


def test_mobile_request_prefers_mobile_home_in_auth_context():
    app = create_app()
    with app.test_request_context('/login', headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'}):
        assert auth._request_prefers_mobile_home() is True


def test_desktop_request_does_not_prefer_mobile_home_in_auth_context():
    app = create_app()
    with app.test_request_context('/login', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}):
        assert auth._request_prefers_mobile_home() is False


def test_dashboard_redirects_mobile_user_agents_to_mobile_home():
    client = _logged_in_client()
    response = client.get(
        '/dashboard',
        headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/mobile/home')


def test_dashboard_keeps_desktop_user_agents_on_desktop_dashboard():
    client = _logged_in_client()
    response = client.get(
        '/dashboard',
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
        follow_redirects=False,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'MCPD Command Desk' in html
    assert 'Choose the work. Move fast. Stay grounded.' in html


def test_mobile_home_rebuild_has_only_primary_field_actions():
    client = _logged_in_client()
    response = client.get('/mobile/home')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'MCPD Portal' in html
    assert 'Ready to start a call?' in html
    assert 'Start New Incident' in html
    assert 'Continue Incident' in html
    assert 'Laws / Orders' in html
    assert 'Quick Reference' in html
    assert 'Operations Board' not in html
    assert 'Shift Workflow' not in html
    assert 'Command Radar' not in html
    assert 'Resume The Mission' not in html
