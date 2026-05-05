import os
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Form, User


def _logged_in_client():
    db_fd, db_path = tempfile.mkstemp(prefix="mcpd-ui-stabilization-", suffix=".db")
    os.close(db_fd)
    os.environ["MCPD_DATABASE_URL"] = f"sqlite:///{Path(db_path).as_posix()}"
    os.environ["REQUIRE_PERSISTENT_DATABASE"] = "0"
    app = create_app()
    app.config["TESTING"] = True
    app.config["_TEST_DB_PATH"] = db_path
    with app.app_context():
        db.create_all()
        user = User(
            username="ui-stabilization",
            name="UI Stabilization Officer",
            role="website_controller",
            active=True,
            password_hash="not-used-in-session-test",
        )
        form = Form(
            title="UI Stabilization Form",
            category="Test",
            file_path="forms/ui-stabilization.pdf",
            is_active=True,
        )
        db.session.add_all([user, form])
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
    return client


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    db_path = app.config.get("_TEST_DB_PATH")
    if db_path:
        try:
            os.remove(db_path)
        except FileNotFoundError:
            pass


def test_mobile_home_uses_bundled_inline_icons_for_tiles():
    client = _logged_in_client()
    try:
        response = client.get("/mobile/home")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'class="mcpd-mobile-tile-icon"' in html
        assert html.count('class="mcpd-mobile-tile-icon"') == 6
        assert "Law Lookup" in html
        assert "Start Report" in html or "Continue Report" in html
        assert "Training" in html
    finally:
        _dispose_app(client.application)


def test_normal_pages_do_not_show_mobile_debug_markers():
    client = _logged_in_client()
    try:
        for path in ["/forms", "/legal/search", "/orders"]:
            response = client.get(path, follow_redirects=True)
            html = response.get_data(as_text=True)
            assert response.status_code == 200
            assert "MCPD MOBILE" not in html
            assert "mobile-version-marker" not in html
    finally:
        _dispose_app(client.application)


def test_pwa_and_static_assets_load_for_clean_railway_deploy():
    client = _logged_in_client()
    try:
        paths = [
            "/static/css/app.css",
            "/static/js/app.js",
            "/static/js/assistant.js",
            "/static/icons/mcpd-icon.svg",
            "/static/icons/mcpd-icon-192.png",
            "/static/icons/mcpd-icon-512.png",
            "/static/icons/mcpd-apple-touch-icon.png",
            "/manifest.webmanifest",
            "/service-worker.js",
        ]
        for path in paths:
            response = client.get(path)
            assert response.status_code == 200, path
            assert response.data, path
    finally:
        _dispose_app(client.application)


def test_forms_fill_layout_has_stabilized_actions_when_form_exists():
    client = _logged_in_client()
    try:
        with client.application.app_context():
            form = Form.query.filter_by(is_active=True).first()
            assert form is not None
            form_id = form.id
        response = client.get(f"/forms/{form_id}/fill")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "forms-fill-layout" in html
        assert "forms-fill-side" in html
        assert "form-action-footer" in html
        assert "Blank Preview" in html
        assert "Blank Download" in html
    finally:
        _dispose_app(client.application)
