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


def test_retired_desktop_modules_redirect_to_supported_workflows():
    client = _client()

    forms = client.get('/forms')
    assert forms.status_code == 200
    assert 'Forms Library' in forms.get_data(as_text=True)

    bodycam = client.get('/bodycam', follow_redirects=False)
    assert bodycam.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in bodycam.headers['Location']

    report_builder = client.get('/reports/new', follow_redirects=False)
    assert report_builder.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in report_builder.headers['Location']

    cleoc = client.get('/cleo/reports', follow_redirects=False)
    assert cleoc.status_code in {301, 302, 303, 307, 308}
    assert '/reports' in cleoc.headers['Location']

    watch = client.get('/watch-commander/dashboard', follow_redirects=False)
    assert watch.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in watch.headers['Location']

    assistant_ops = client.get('/assistant-operations', follow_redirects=False)
    assert assistant_ops.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in assistant_ops.headers['Location']

    messages = client.get('/notifications/inbox', follow_redirects=False)
    assert messages.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in messages.headers['Location']


def test_retired_mobile_entry_points_redirect_to_narrative_creator():
    client = _client()

    mobile_report = client.get('/mobile/incident/start', follow_redirects=False)
    assert mobile_report.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in mobile_report.headers['Location']

    mobile_bodycam = client.get('/mobile/bodycam', follow_redirects=False)
    assert mobile_bodycam.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in mobile_bodycam.headers['Location']

    mobile_bodycam_library = client.get('/mobile/bodycam/footage', follow_redirects=False)
    assert mobile_bodycam_library.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in mobile_bodycam_library.headers['Location']


def test_narrative_creator_sentinel_and_accident_tools_are_available():
    client = _client()

    narrative = client.get('/tools/narrative')
    assert narrative.status_code == 200
    assert 'Narrative Creator' in narrative.get_data(as_text=True)
    assert 'Open Sentinel Inspector' in narrative.get_data(as_text=True)

    inspector = client.get('/sentinel/report-inspector')
    assert inspector.status_code == 200
    assert 'Report Quality Inspector' in inspector.get_data(as_text=True)

    fto = client.get('/sentinel/fto-instructor')
    assert fto.status_code == 200
    assert 'AI FTO Instructor' in fto.get_data(as_text=True)

    five_w = client.get('/tools/5w')
    assert five_w.status_code == 200
    assert '5W Builder' in five_w.get_data(as_text=True)

    accidents = client.get('/reports/accidents')
    assert accidents.status_code == 200
    assert 'Crash packet review' in accidents.get_data(as_text=True)


def test_retired_navigation_is_not_visible_on_dashboard():
    client = _client()
    html = client.get('/dashboard').get_data(as_text=True)

    assert 'Body Cam Mode' not in html
    assert 'Bodycam Footage' not in html
    assert 'Start New Report' not in html
    assert 'CLEOC Reports' not in html
    assert '>Messages' not in html
    assert 'Watch Commander Hub' not in html
    assert 'Command Due-Out Tracker' not in html
    assert 'MCLB Albany — Installation Map' not in html
    assert '/sentinel/report-inspector' in html
    assert '/sentinel/fto-instructor' in html
