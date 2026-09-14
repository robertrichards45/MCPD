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


def test_bodycam_surfaces_are_retired_but_narrative_tools_remain():
    _app, client, _user_id = _logged_in_client()

    for path in ('/bodycam', '/bodycam/new', '/mobile/bodycam', '/mobile/bodycam/footage', '/bodycam/narrative'):
        response = client.get(path, follow_redirects=False)
        assert response.status_code in {301, 302, 303, 307, 308}
        assert '/tools/narrative' in response.headers['Location']

    for path, expected in [
        ('/tools/narrative', 'Narrative Creator'),
        ('/tools/5w', '5W Builder'),
        ('/mobile/tools/narrative', 'Narrative Creator'),
        ('/mobile/tools/5w', '5W Builder'),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.get_data(as_text=True)


def test_bodycam_upload_endpoint_is_retired():
    _app, client, _user_id = _logged_in_client()
    response = client.post('/bodycam/upload', follow_redirects=False)
    assert response.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in response.headers['Location']


def test_mobile_more_keeps_narrative_tools_but_hides_bodycam():
    _app, client, _user_id = _logged_in_client()
    more = client.get('/mobile/more').get_data(as_text=True)

    assert 'Narrative Creator' in more
    assert '5W Builder' in more
    assert 'Body Cam Mode' not in more
    assert 'Bodycam Footage' not in more
    assert '/mobile/tools/narrative' in more
    assert '/mobile/tools/5w' in more


def test_desktop_dashboard_exposes_supported_field_tools():
    _app, client, _user_id = _logged_in_client()
    html = client.get('/dashboard').get_data(as_text=True)

    assert 'Narrative Creator' in html
    assert '5W Builder' in html
    assert 'Accident Tools' in html
    assert 'Body Cam Mode' not in html
    assert 'Bodycam Footage' not in html
    assert '/reports/accidents' in html
    assert '/sentinel/report-inspector' in html
