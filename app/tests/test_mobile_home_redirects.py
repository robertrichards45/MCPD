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
    assert 'Welcome back' in html
    assert 'Start New Report' in html
    assert 'Forms Library' in html


def test_mobile_home_rebuild_has_only_primary_field_actions():
    client = _logged_in_client()
    response = client.get('/mobile/home')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'MCPD' in html
    assert 'Law Lookup' in html
    assert 'Start Report' in html
    assert 'Officer Stats' in html
    assert 'Contact Info' in html
    assert 'Edit' in html
    assert '/mobile/stats' in html
    assert '/mobile/contact' in html
    assert 'Operations Board' not in html
    assert 'Shift Workflow' not in html
    assert 'Command Radar' not in html
    assert 'Resume The Mission' not in html


def test_mobile_home_menu_link_opens_more_tools():
    client = _logged_in_client()
    response = client.get('/mobile/home')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '/mobile/more' in html

    more_response = client.get('/mobile/more')
    assert more_response.status_code == 200
    assert 'More tools' in more_response.get_data(as_text=True)


def test_mobile_stats_and_contact_pages_work_without_desktop_shell():
    client = _logged_in_client()

    stats_response = client.get('/mobile/stats')
    assert stats_response.status_code == 200
    stats_html = stats_response.get_data(as_text=True)
    assert 'My Stats' in stats_html
    assert 'Reports' in stats_html
    assert 'Saved Forms' in stats_html
    assert 'Desktop Dashboard' not in stats_html

    contact_response = client.get('/mobile/contact')
    assert contact_response.status_code == 200
    contact_html = contact_response.get_data(as_text=True)
    assert 'Contact Info' in contact_html
    assert 'Save Contact Info' in contact_html
    assert 'name="phone_number"' in contact_html
    assert 'name="email"' in contact_html
