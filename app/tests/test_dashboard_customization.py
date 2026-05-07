from app import create_app
from app.extensions import db
from app.models import User


def _client_with_user():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
        assert user is not None
        user.dashboard_preferences_json = None
        db.session.commit()
        user_id = user.id
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    return client, user_id


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def test_dashboard_customize_page_loads():
    client, _ = _client_with_user()
    try:
        response = client.get("/dashboard/customize")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Customize Dashboard" in html
        assert "Quick Action Cards" in html
        assert "Dashboard Panels" in html
        assert "Start New Report" in html
    finally:
        _dispose_app(client.application)


def test_user_can_save_dashboard_card_and_panel_preferences():
    client, user_id = _client_with_user()
    try:
        response = client.post(
            "/dashboard/customize",
            data={
                "action": "save",
                "cards": ["start_report", "forms_library"],
                "panels": ["saved_work"],
            },
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}

        dashboard = client.get("/dashboard")
        html = dashboard.get_data(as_text=True)
        assert dashboard.status_code == 200
        assert "Start New Report" in html
        assert "Forms Library" in html
        assert "<strong>Law Lookup</strong>" not in html
        assert "Saved Work" in html
        assert "Training Rosters" not in html

        with client.application.app_context():
            user = db.session.get(User, user_id)
            assert "start_report" in (user.dashboard_preferences_json or "")
    finally:
        with client.application.app_context():
            user = db.session.get(User, user_id)
            if user:
                user.dashboard_preferences_json = None
                db.session.commit()
        _dispose_app(client.application)


def test_user_can_reset_dashboard_preferences():
    client, user_id = _client_with_user()
    try:
        with client.application.app_context():
            user = db.session.get(User, user_id)
            user.dashboard_preferences_json = '{"cards":["start_report"],"panels":["saved_work"]}'
            db.session.commit()

        response = client.post("/dashboard/customize", data={"action": "reset"}, follow_redirects=False)
        assert response.status_code in {302, 303}

        with client.application.app_context():
            user = db.session.get(User, user_id)
            assert user.dashboard_preferences_json is None
    finally:
        with client.application.app_context():
            user = db.session.get(User, user_id)
            if user:
                user.dashboard_preferences_json = None
                db.session.commit()
        _dispose_app(client.application)
