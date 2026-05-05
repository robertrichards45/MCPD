from app import create_app
from app.extensions import db
from app.models import User


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


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


def _text_response(response):
    try:
        return response.get_data(as_text=True)
    finally:
        response.close()


def test_mobile_officer_flow_routes_render():
    client = _logged_in_client()
    try:
        paths = [
            '/mobile/home',
            '/mobile/incident/start',
            '/mobile/incident/basics',
            '/mobile/incident/recommended-forms',
            '/mobile/incident/persons',
            '/mobile/incident/statute',
            '/mobile/incident/checklist',
            '/mobile/incident/facts',
            '/mobile/incident/narrative-review',
            '/mobile/incident/statements',
            '/mobile/incident/domestic-supplemental',
            '/mobile/incident/packet-review',
            '/mobile/incident/send-packet',
        ]

        for path in paths:
            response = client.get(path)
            try:
                assert response.status_code == 200, path
            finally:
                response.close()
    finally:
        _dispose_app(client.application)


def test_mobile_login_allows_camera_permission_policy_for_self():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    try:
        response = client.get('/login')
        try:
            assert response.status_code == 200
            assert response.headers.get('Permissions-Policy') == 'camera=(self), microphone=(), geolocation=(), payment=(), usb=()'
        finally:
            response.close()
    finally:
        _dispose_app(app)


def test_login_page_has_one_primary_sign_in_path():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    try:
        response = client.get('/login')
        try:
            html = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Sign In' in html
            assert 'Manager Login' not in html
            assert 'Login with Name' not in html
            assert 'Create Account' not in html
            assert 'Need access?' in html
        finally:
            response.close()
    finally:
        _dispose_app(app)


def test_mobile_officer_flow_pages_include_updated_mobile_assets():
    client = _logged_in_client()
    try:
        home = _text_response(client.get('/mobile/home'))
        forms = _text_response(client.get('/mobile/incident/recommended-forms'))
        domestic = _text_response(client.get('/mobile/incident/domestic-supplemental'))
        runtime = _text_response(client.get('/static/mobile/incident-core.js?v=2026-04-24-mobile-live-scanner-1'))

        assert 'MCPD' in home
        assert 'Law Lookup' in home
        assert 'Start Report' in home or 'Continue Report' in home
        assert 'Forms' in home
        assert 'Orders' in home
        assert 'Training' in home
        assert 'Saved' in home
        assert 'Officer Stats' in home
        assert 'Contact Info' in home
        assert '<svg viewBox="0 0 24 24">' in home
        assert 'Shift Workflow' not in home
        assert 'Command Radar' not in home
        assert 'Resume Mission' not in home
        assert 'Reports Center' not in home
        assert 'Paperwork Navigator' not in home
        assert 'Admin / Desktop Tools' not in home
        assert 'data-mobile-incident-page="selected-forms"' in forms
        assert '2026-05-04-draft-sync-1' in domestic
        assert '/static/vendor/zxing-browser.min.js' in domestic
        assert 'mobile-domestic-schema-data' in domestic
        assert 'data-id-scan-raw' in runtime
        assert 'data-id-scan-file' in runtime
        assert 'Use Scan Text' in runtime
    finally:
        _dispose_app(client.application)


def test_mobile_runtime_uses_guided_statement_and_domestic_flows():
    client = _logged_in_client()
    try:
        runtime = _text_response(client.get('/static/mobile/incident-core.js?v=2026-04-24-mobile-live-scanner-1'))

        assert "const steps = ['person', 'details', 'content'];" in runtime
        assert 'Choose who is giving the statement' in runtime
        assert 'buildDomesticGuidedSteps' in runtime
        assert 'Response details' in runtime
        assert 'Who was involved' in runtime
        assert 'Victim statements' in runtime
        assert 'Suspect statements' in runtime
        assert 'Second injury documentation' in runtime
        assert 'domesticRadioGroupKey(field) === groupKey' in runtime
        assert 'jsonScriptCache' in runtime
        assert 'scanInput.addEventListener(\'paste\'' in runtime
        assert 'window.ZXingBrowser' in runtime
        assert 'BrowserPDF417Reader' in runtime
        assert 'decodeFromVideoDevice' in runtime
        assert 'data-id-live-video' in runtime
        assert 'Open Live ID Scanner' in runtime
        assert 'openCaptureFallback' in runtime
    finally:
        _dispose_app(client.application)
