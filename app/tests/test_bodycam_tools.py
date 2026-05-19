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
        return app, client, user.id


def test_narrative_and_5w_pages_render_while_bodycam_stays_retired():
    _app, client, _user_id = _logged_in_client()

    for path, expected in [
        ('/tools/narrative', 'Narrative Creator'),
        ('/tools/5w', '5W Builder'),
        ('/bodycam/narrative', 'Narrative Creator'),
        ('/mobile', 'MCPD'),
        ('/mobile/tools/narrative', 'Narrative Creator'),
        ('/mobile/tools/5w', '5W Builder'),
    ]:
        response = client.get(path)
        if response.status_code in {301, 302, 303, 308}:
            response = client.get(response.headers['Location'])
        assert response.status_code == 200
        assert expected in response.get_data(as_text=True)

    for retired_path in ['/bodycam', '/bodycam/new', '/mobile/bodycam', '/mobile/bodycam/footage']:
        response = client.get(retired_path, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/dashboard')
    upload = client.post('/bodycam/upload', headers={'X-CSRFToken': 'test-token'}, follow_redirects=False)
    assert upload.status_code == 302
    assert upload.headers['Location'].endswith('/dashboard')


def test_mobile_more_exposes_narrative_tools_without_bodycam_links():
    _app, client, _user_id = _logged_in_client()

    more = client.get('/mobile/more').get_data(as_text=True)
    assert 'Narrative Creator' in more
    assert '5W Builder' in more
    assert 'Body Cam Mode' not in more
    assert 'Bodycam Footage' not in more
    assert '/mobile/bodycam' not in more
    assert '/mobile/tools/narrative' in more
    assert '/mobile/tools/5w' in more


def test_desktop_dashboard_exposes_narrative_tools_without_retired_tools():
    _app, client, _user_id = _logged_in_client()

    html = client.get('/dashboard').get_data(as_text=True)

    assert 'Narrative Creator' in html
    assert '5W Builder' in html
    assert 'Accident Tools' not in html
    assert 'Body Cam Mode' not in html
    assert 'Bodycam Footage' not in html
    assert '/reports/accidents' not in html
    assert '/bodycam/new' not in html
    assert '/tools/narrative' in html
    assert '/tools/5w' in html
