from app import create_app
from app.extensions import db
from app.models import (
    AccidentReconstruction,
    DemoRecord,
    IncidentPacket,
    ROLE_WEBSITE_CONTROLLER,
    TrainingRoster,
    User,
    WatchAssignment,
    WatchShift,
)


def _demo_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REQUIRE_PERSISTENT_DATABASE", "0")
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        admin = User(
            username="robertrichards",
            role=ROLE_WEBSITE_CONTROLLER,
            active=True,
            pending_approval=False,
            first_name="Demo",
            last_name="Controller",
        )
        admin.set_password("x")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(admin_id)
        session["_fresh"] = True
    return client, admin_id


def test_demo_setup_loads_resets_and_keeps_real_user(monkeypatch):
    client, _admin_id = _demo_client(monkeypatch)

    setup_page = client.get("/demo/setup")
    assert setup_page.status_code == 200
    assert "Load MCPD Demo Data" in setup_page.get_data(as_text=True)

    loaded = client.post("/demo/setup", follow_redirects=True)
    assert loaded.status_code == 200
    html = loaded.get_data(as_text=True)
    assert "Alpha Shift" in html
    assert "CVI" in html
    assert "K-9" in html

    with client.application.app_context():
        assert User.query.filter_by(is_demo=True).count() >= 59
        assert WatchShift.query.filter_by(is_demo=True).count() == 4
        assert WatchAssignment.query.filter_by(is_demo=True).count() >= 36
        assert IncidentPacket.query.filter_by(is_demo=True).count() == 4
        assert TrainingRoster.query.filter_by(is_demo=True).count() == 5
        assert AccidentReconstruction.query.filter_by(is_demo=True).count() == 2
        assert DemoRecord.query.filter_by(is_demo=True, record_type="law_lookup").count() == 5

    reset = client.post("/demo/reset", follow_redirects=False)
    assert reset.status_code in {302, 303}
    with client.application.app_context():
        assert User.query.filter_by(is_demo=True).count() == 0
        assert DemoRecord.query.filter_by(is_demo=True).count() == 0
        assert User.query.filter_by(username="robertrichards").count() == 1


def test_demo_user_switcher_and_law_lookup(monkeypatch):
    client, _admin_id = _demo_client(monkeypatch)
    client.post("/demo/setup", follow_redirects=True)

    users_page = client.get("/demo/users")
    assert users_page.status_code == 200
    assert "Lt. Adams" in users_page.get_data(as_text=True)

    law_page = client.get("/demo/law-lookup?q=barred")
    assert law_page.status_code == 200
    assert "Installation Access Control" in law_page.get_data(as_text=True)

    api = client.get("/demo/api/law-lookup?q=traffic")
    assert api.status_code == 200
    assert api.get_json()["results"]

    with client.application.app_context():
        demo_user = User.query.filter_by(username="demo.alpha.carter").first()
        assert demo_user is not None
        demo_user_id = demo_user.id

    switched = client.post(f"/demo/impersonate/{demo_user_id}", follow_redirects=False)
    assert switched.status_code in {302, 303}
    workflow = client.get("/demo/workflows/cvi")
    assert workflow.status_code == 200
    assert "Commercial vehicle inspection log" in workflow.get_data(as_text=True)


def test_demo_toggle_is_site_owner_only(monkeypatch):
    client, _admin_id = _demo_client(monkeypatch)

    turned_on = client.post("/demo/toggle", follow_redirects=True)
    assert turned_on.status_code == 200
    assert "DEMO MODE" in turned_on.get_data(as_text=True)

    turned_off = client.post("/demo/toggle", follow_redirects=False)
    assert turned_off.status_code in {302, 303}

    app = client.application
    with app.app_context():
        non_owner = User(
            username="not_the_owner",
            role=ROLE_WEBSITE_CONTROLLER,
            active=True,
            pending_approval=False,
            first_name="Other",
            last_name="Admin",
        )
        non_owner.set_password("x")
        db.session.add(non_owner)
        db.session.commit()
        non_owner_id = non_owner.id

    other_client = app.test_client()
    with other_client.session_transaction() as session:
        session["_user_id"] = str(non_owner_id)
        session["_fresh"] = True

    assert other_client.get("/demo/setup").status_code == 403
    assert other_client.post("/demo/toggle").status_code == 403


def test_demo_records_are_hidden_from_normal_pages_when_demo_is_off(monkeypatch):
    client, _admin_id = _demo_client(monkeypatch)
    client.post("/demo/setup", follow_redirects=True)
    client.post("/demo/toggle", follow_redirects=False)

    forms_page = client.get("/forms")
    assert forms_page.status_code == 200
    assert "DEMO Statement form" not in forms_page.get_data(as_text=True)

    users_page = client.get("/admin/users")
    assert users_page.status_code == 200
    html = users_page.get_data(as_text=True)
    assert "demo.alpha.carter" not in html
    assert "Ofc. Carter" not in html
