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


def test_restored_desktop_modules_load():
    client = _client()

    forms = client.get('/forms')
    assert forms.status_code == 200
    assert 'Forms Library' in forms.get_data(as_text=True)

    bodycam = client.get('/bodycam')
    assert bodycam.status_code == 200
    assert 'Bodycam Footage' in bodycam.get_data(as_text=True)

    accidents = client.get('/reports/accidents')
    assert accidents.status_code == 200
    assert 'Accident Tools' in accidents.get_data(as_text=True)

    report_builder = client.get('/reports/new')
    assert report_builder.status_code == 200

    cleoc = client.get('/cleo/reports')
    assert cleoc.status_code == 200

def test_narrative_creator_and_5w_builder_are_available():
    client = _client()

    narrative = client.get('/tools/narrative')
    assert narrative.status_code == 200
    assert 'Narrative Creator' in narrative.get_data(as_text=True)

    five_w = client.get('/tools/5w')
    assert five_w.status_code == 200
    assert '5W Builder' in five_w.get_data(as_text=True)


def test_restored_mobile_report_builder_loads():
    client = _client()

    response = client.get('/mobile/incident/start', follow_redirects=False)
    assert response.status_code == 200
