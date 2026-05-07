from app import create_app


def _prod_client():
    app = create_app()
    app.config.update(
        APP_ENV='prod',
        FORCE_HTTPS=True,
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )
    return app.test_client()


def test_www_domain_get_redirects_to_apex_permanently():
    client = _prod_client()

    response = client.get('/login', base_url='https://www.mclbpd.com')

    assert response.status_code == 301
    assert response.headers['Location'] == 'https://mclbpd.com/login'


def test_www_domain_login_post_preserves_method_and_body():
    client = _prod_client()

    response = client.post(
        '/admin/login',
        base_url='https://www.mclbpd.com',
        data={'username': 'robertrichards', 'password': 'example'},
    )

    assert response.status_code == 308
    assert response.headers['Location'] == 'https://mclbpd.com/admin/login'


def test_http_login_post_preserves_method_when_forced_to_https():
    client = _prod_client()

    response = client.post(
        '/admin/login',
        base_url='http://mclbpd.com',
        headers={'X-Forwarded-Proto': 'http'},
        data={'username': 'robertrichards', 'password': 'example'},
    )

    assert response.status_code == 308
    assert response.headers['Location'] == 'https://mclbpd.com/admin/login'


def test_cloudflare_https_signal_is_treated_as_secure():
    client = _prod_client()

    response = client.get(
        '/tls-check',
        base_url='http://mclbpd.com',
        headers={'Cf-Visitor': '{"scheme":"https"}'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['external_scheme'] == 'https'
    assert payload['external_is_secure'] is True


def test_railway_defaults_to_production_safe_config(monkeypatch):
    import importlib
    import app.config as config_module

    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.delenv('TRUST_PROXY', raising=False)
    monkeypatch.delenv('FORCE_HTTPS', raising=False)
    monkeypatch.delenv('SESSION_COOKIE_SECURE', raising=False)
    monkeypatch.delenv('HSTS_ENABLED', raising=False)
    monkeypatch.delenv('APP_DOMAIN', raising=False)
    monkeypatch.setenv('RAILWAY_PROJECT_ID', 'project-test')
    monkeypatch.setenv('RAILWAY_PUBLIC_DOMAIN', 'mcpd-production.up.railway.app')

    reloaded = importlib.reload(config_module)

    assert reloaded.Config.APP_ENV == 'prod'
    assert reloaded.Config.TRUST_PROXY is True
    assert reloaded.Config.FORCE_HTTPS is True
    assert reloaded.Config.SESSION_COOKIE_SECURE is True
    assert reloaded.Config.HSTS_ENABLED is True
    assert reloaded.Config.APP_DOMAIN == 'mcpd-production.up.railway.app'

    importlib.reload(config_module)


def test_admin_bootstrap_strips_invisible_password_whitespace(monkeypatch, tmp_path):
    from app import create_app
    from app.models import User

    db_path = tmp_path / 'admin-bootstrap.db'
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv('REQUIRE_PERSISTENT_DATABASE', '0')
    monkeypatch.setenv('ADMIN_USERNAME', ' robertrichards ')
    monkeypatch.setenv('ADMIN_PASSWORD', ' Stonecold1! \n')

    app = create_app()

    with app.app_context():
        user = User.query.filter_by(username='robertrichards').first()
        assert user is not None
        assert user.active is True
        assert user.check_password('Stonecold1!')


def test_production_login_does_not_show_limited_write_notice_by_default(monkeypatch, tmp_path):
    db_path = tmp_path / 'prod-login.db'
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv('REQUIRE_PERSISTENT_DATABASE', '0')
    monkeypatch.setenv('APP_ENV', 'prod')
    monkeypatch.delenv('PORTAL_WRITE_LIMITED_MODE', raising=False)

    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get('/login', base_url='https://mclbpd.com')

    assert response.status_code == 200
    assert b'Running in limited write mode' not in response.data


def test_reset_login_device_clears_browser_state(monkeypatch, tmp_path):
    db_path = tmp_path / 'reset-login.db'
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv('REQUIRE_PERSISTENT_DATABASE', '0')

    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get('/login/reset-device', base_url='https://mclbpd.com')

    assert response.status_code == 200
    assert 'Clear-Site-Data' in response.headers
    assert '"cookies"' in response.headers['Clear-Site-Data']
    assert '"storage"' in response.headers['Clear-Site-Data']
    assert b'getRegistrations' in response.data


def test_service_worker_is_not_browser_cached():
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get('/service-worker.js', base_url='https://mclbpd.com')

    assert response.status_code == 200
    assert 'no-store' in response.headers.get('Cache-Control', '')
