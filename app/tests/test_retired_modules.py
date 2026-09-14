from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='retired-modules-ci').first()
        if user is None:
            user = User(
                username='retired-modules-ci',
                name='Retired Modules CI',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
                builder_mode_access=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
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

    shift_checkin = client.get('/watch-commander/sign-on', follow_redirects=False)
    assert shift_checkin.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in shift_checkin.headers['Location']

    incident_command = client.get('/incident-command', follow_redirects=False)
    assert incident_command.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in incident_command.headers['Location']

    assistant_ops = client.get('/assistant-operations', follow_redirects=False)
    assert assistant_ops.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in assistant_ops.headers['Location']

    messages = client.get('/notifications/inbox', follow_redirects=False)
    assert messages.status_code in {301, 302, 303, 307, 308}
    assert '/dashboard' in messages.headers['Location']


def test_retired_bodycam_mobile_entry_points_redirect_to_narrative_creator():
    client = _client()

    mobile_bodycam = client.get('/mobile/bodycam', follow_redirects=False)
    assert mobile_bodycam.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in mobile_bodycam.headers['Location']

    mobile_bodycam_library = client.get('/mobile/bodycam/footage', follow_redirects=False)
    assert mobile_bodycam_library.status_code in {301, 302, 303, 307, 308}
    assert '/tools/narrative' in mobile_bodycam_library.headers['Location']


def test_internal_mobile_packet_route_is_not_advertised_as_start_report():
    client = _client()
    mobile_more = client.get('/mobile/more').get_data(as_text=True)
    assert '>Start Report<' not in mobile_more
    assert 'Narrative Creator' in mobile_more
    assert 'Report Quality Review' in mobile_more


def test_narrative_creator_sentinel_fto_center_and_accident_tools_are_available():
    client = _client()

    narrative = client.get('/tools/narrative')
    narrative_html = narrative.get_data(as_text=True)
    assert narrative.status_code == 200
    assert 'Narrative Creator' in narrative_html
    assert 'Full Report Quality Review' in narrative_html
    assert 'Sentinel Side Panel' in narrative_html

    inspector = client.get('/sentinel/report-inspector')
    assert inspector.status_code == 200
    assert 'Report Quality Inspector' in inspector.get_data(as_text=True)

    fto = client.get('/sentinel/fto-center')
    assert fto.status_code == 200
    assert 'FTO Center' in fto.get_data(as_text=True)
    assert 'Scenario Lab' in fto.get_data(as_text=True)

    old_fto = client.get('/sentinel/fto-instructor', follow_redirects=False)
    assert old_fto.status_code in {301, 302, 303, 307, 308}
    assert '/sentinel/fto-center' in old_fto.headers['Location']

    five_w = client.get('/tools/5w')
    assert five_w.status_code == 200
    assert '5W Builder' in five_w.get_data(as_text=True)

    accidents = client.get('/reports/accidents')
    assert accidents.status_code == 200
    assert 'Guided Crash Intake' in accidents.get_data(as_text=True)
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
    assert 'Watch Dashboard' not in html
    assert 'Live Response Board' not in html
    assert 'Command Due-Out Tracker' not in html
    assert 'MCLB Albany — Installation Map' not in html
    assert 'Incident Command' not in html
    assert 'Shift Check-In' not in html
    assert 'Check In' not in html
    assert 'Location sharing is OFF' not in html
    assert '/sentinel/report-inspector' in html
    assert '/sentinel/fto-center' in html
    assert 'Narrative Creator' in html
    assert 'Personnel &amp; Account Approval' in html


def test_personnel_page_prioritizes_account_workflow_and_hides_retired_mock_report_controls():
    client = _client()
    response = client.get('/admin/users')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Personnel &amp; Account Management' in html
    assert 'New Account Requests' in html
    assert 'Create Account' in html
    assert 'Approve &amp; Activate' in html or '0 Pending' in html
    assert 'Can review mock reports' not in html
    assert 'Grant mock report review access' not in html
