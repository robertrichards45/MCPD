from app import create_app
from app.models import User


def _client():
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


def test_retired_desktop_modules_redirect_to_safe_pages():
    client = _client()

    forms = client.get('/forms', follow_redirects=False)
    assert forms.status_code == 302
    assert forms.headers['Location'].endswith('/forms/saved')

    bodycam = client.get('/bodycam', follow_redirects=False)
    assert bodycam.status_code == 302
    assert bodycam.headers['Location'].endswith('/dashboard')

    accidents = client.get('/reports/accidents', follow_redirects=False)
    assert accidents.status_code == 302
    assert accidents.headers['Location'].endswith('/reports')

    report_builder = client.get('/reports/new', follow_redirects=False)
    assert report_builder.status_code == 302
    assert report_builder.headers['Location'].endswith('/reports')

def test_narrative_creator_and_5w_builder_are_available():
    client = _client()

    narrative = client.get('/tools/narrative')
    assert narrative.status_code == 200
    assert 'Narrative Creator' in narrative.get_data(as_text=True)

    five_w = client.get('/tools/5w')
    assert five_w.status_code == 200
    assert '5W Builder' in five_w.get_data(as_text=True)


def test_retired_mobile_report_builder_redirects_home():
    client = _client()

    response = client.get('/mobile/incident/start', follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/mobile/home')
