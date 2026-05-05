import os
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import AccidentReconstruction, ROLE_PATROL_OFFICER, ROLE_WEBSITE_CONTROLLER, User


def _client_for_role(role=ROLE_WEBSITE_CONTROLLER):
    db_fd, db_path = tempfile.mkstemp(prefix="mcpd-accident-tools-", suffix=".db")
    os.close(db_fd)
    os.environ["MCPD_DATABASE_URL"] = f"sqlite:///{Path(db_path).as_posix()}"
    os.environ["REQUIRE_PERSISTENT_DATABASE"] = "0"
    app = create_app()
    app.config["TESTING"] = True
    app.config["_TEST_DB_PATH"] = db_path
    with app.app_context():
        db.create_all()
        user = User(
            username=f"accident-tools-{role.lower()}",
            name="Accident Tools Test User",
            role=role,
            active=True,
            password_hash="not-used-in-session-test",
        )
        db.session.add(user)
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
    return client


def _dispose(client):
    app = client.application
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    db_path = app.config.get("_TEST_DB_PATH")
    if db_path:
        try:
            os.remove(db_path)
        except FileNotFoundError:
            pass


def test_accident_tools_buttons_route_to_separate_workflows():
    client = _client_for_role()
    try:
        response = client.get("/reports/accidents")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'href="/reports/accidents/officer-diagram/new"' in html
        assert 'href="/reports/accidents/reconstruction/new"' in html
    finally:
        _dispose(client)


def test_officer_diagram_and_reconstruction_pages_are_not_the_same():
    client = _client_for_role()
    try:
        officer_response = client.get("/reports/accidents/officer-diagram/new", follow_redirects=True)
        officer_html = officer_response.get_data(as_text=True)
        assert officer_response.status_code == 200
        assert "Officer Accident Diagram" in officer_html
        assert "Vehicle Dynamics" not in officer_html
        assert "Generate Report" not in officer_html

        reconstruction_response = client.get("/reports/accidents/reconstruction/new", follow_redirects=True)
        reconstruction_html = reconstruction_response.get_data(as_text=True)
        assert reconstruction_response.status_code == 200
        assert "Accident Investigator Reconstruction" in reconstruction_html
        assert "Vehicle Dynamics" in reconstruction_html
        assert "Measurements" in reconstruction_html
        assert officer_html != reconstruction_html
    finally:
        _dispose(client)


def test_patrol_officer_cannot_open_advanced_reconstruction():
    client = _client_for_role(ROLE_PATROL_OFFICER)
    try:
        officer_response = client.get("/reports/accidents/officer-diagram/new", follow_redirects=True)
        assert officer_response.status_code == 200
        assert "Officer Accident Diagram" in officer_response.get_data(as_text=True)

        advanced_response = client.get("/reports/accidents/reconstruction/new")
        assert advanced_response.status_code == 403
    finally:
        _dispose(client)


def test_recent_cases_identify_type_and_route_to_correct_tool():
    client = _client_for_role()
    try:
        with client.application.app_context():
            user = User.query.first()
            officer = AccidentReconstruction(
                title="Quick crash sketch",
                officer_id=user.id,
                status="OFFICER_DIAGRAM",
            )
            investigator = AccidentReconstruction(
                title="Detailed crash reconstruction",
                officer_id=user.id,
                status="DRAFT",
            )
            db.session.add_all([officer, investigator])
            db.session.commit()
            officer_id = officer.id
            investigator_id = investigator.id

        response = client.get("/reports/accidents")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Officer Diagram" in html
        assert "Investigator Reconstruction" in html
        assert f"/reports/accidents/officer-diagram/{officer_id}" in html
        assert f"/reports/accidents/reconstruction/{investigator_id}" in html
    finally:
        _dispose(client)
