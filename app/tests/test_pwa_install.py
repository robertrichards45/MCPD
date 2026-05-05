from app import create_app


def test_pwa_manifest_is_served_with_install_metadata():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    response = client.get('/manifest.webmanifest')

    assert response.status_code == 200
    assert response.mimetype == 'application/manifest+json'
    data = response.get_json()
    assert data['name'] == 'MCPD Portal'
    assert data['short_name'] == 'MCPD'
    assert data['display'] == 'standalone'
    assert data['theme_color'] == '#071b33'
    assert any(icon['sizes'] == '512x512' and 'maskable' in icon['purpose'] for icon in data['icons'])


def test_service_worker_is_served_from_root_scope():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    response = client.get('/service-worker.js')

    assert response.status_code == 200
    assert response.mimetype == 'application/javascript'
    assert response.headers['Service-Worker-Allowed'] == '/'
    assert 'mcpd-portal-shell' in response.get_data(as_text=True)


def test_login_page_exposes_pwa_links():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    response = client.get('/login')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'rel="manifest"' in html
    assert '/manifest.webmanifest' in html
    assert 'apple-mobile-web-app-capable' in html
    assert 'mcpd-apple-touch-icon.png' in html
