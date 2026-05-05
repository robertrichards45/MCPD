import base64
import json
import os
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import ReconstructionCase, Report, ReportAttachment, User


TINY_PNG = (
    "data:image/png;base64,"
    + base64.b64encode(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )
    ).decode("ascii")
)


def _logged_in_client():
    db_fd, db_path = tempfile.mkstemp(prefix="mcpd-reconstruction-diagram-", suffix=".db")
    os.close(db_fd)
    os.environ["MCPD_DATABASE_URL"] = f"sqlite:///{Path(db_path).as_posix()}"
    os.environ["REQUIRE_PERSISTENT_DATABASE"] = "0"
    app = create_app()
    app.config["TESTING"] = True
    app.config["_TEST_DB_PATH"] = db_path
    with app.app_context():
        db.create_all()
        user = User(
            username="reconstruction-diagram-test",
            name="Reconstruction Diagram Test Officer",
            role="website_controller",
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


def test_professional_scene_diagram_replaces_legacy_cartoon_tool():
    client = _logged_in_client()
    try:
        with client.application.app_context():
            user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
            case = ReconstructionCase(title="Crash Diagram Test", created_by=user.id)
            db.session.add(case)
            db.session.commit()
            case_id = case.id

        response = client.get(f"/reconstruction/{case_id}")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Report / Courtroom Diagram Workspace" in html
        assert "Rear-End" in html
        assert "Point of Impact" in html
        assert "Animal Marker" in html
        assert "Show editing grid" in html
        assert "Snap objects to grid" in html
        assert "Deer" not in html
        assert "Drag Items" not in html
        assert "cartoon" not in html.lower()
    finally:
        _dispose_app(client.application)


def test_diagram_from_report_saves_exports_and_appears_in_packet():
    client = _logged_in_client()
    try:
        with client.application.app_context():
            user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
            report = Report(title="Traffic Accident Diagram Test", owner_id=user.id, status="DRAFT")
            db.session.add(report)
            db.session.commit()
            report_id = report.id

        create_response = client.get(f"/reports/{report_id}/scene-diagram", follow_redirects=False)
        assert create_response.status_code in {302, 303}

        with client.application.app_context():
            case = ReconstructionCase.query.filter_by(report_id=report_id).first()
            assert case is not None
            case_id = case.id

        payload = {
            "version": 2,
            "diagramType": "crash_scene",
            "scenarioType": "rear_end",
            "mode": "report",
            "objects": [
                {"object_id": "v1", "object_type": "vehicle", "label": "V1", "x": 380, "y": 300, "width": 92, "height": 42, "rotation": 0, "layer": "vehicles"},
                {"object_id": "poi", "object_type": "poi", "label": "POI", "x": 470, "y": 300, "width": 44, "height": 44, "rotation": 0, "layer": "evidence", "notes": "rear bumper contact"},
            ],
        }
        save_response = client.post(f"/reconstruction/{case_id}/diagram.json", data=json.dumps(payload), content_type="application/json")
        assert save_response.status_code == 200

        export_response = client.post(f"/reconstruction/{case_id}/export-png", json={"dataUrl": TINY_PNG})
        assert export_response.status_code == 200
        assert export_response.get_json()["attachedToReport"] is True

        with client.application.app_context():
            case = db.session.get(ReconstructionCase, case_id)
            assert case.scenario_type == "rear_end"
            assert case.rendered_png_path
            assert case.attached_to_report is True
            assert ReportAttachment.query.filter_by(report_id=report_id, page_key="scene-diagram").first() is not None

        detail_response = client.get(f"/reports/{report_id}")
        detail_html = detail_response.get_data(as_text=True)
        assert detail_response.status_code == 200
        assert "Scene Diagram" in detail_html
        assert f"Diagram #{case_id}" in detail_html
        assert "Remove Attachment" in detail_html
        assert "rear bumper contact" in detail_html

        packet_response = client.get(f"/reports/{report_id}/packet/download")
        assert packet_response.status_code == 200
        assert packet_response.headers["Content-Type"].startswith("application/pdf")

        detach_response = client.post(f"/reconstruction/{case_id}/detach-from-report", follow_redirects=False)
        assert detach_response.status_code in {302, 303}
        with client.application.app_context():
            case = db.session.get(ReconstructionCase, case_id)
            assert case.attached_to_report is False
            assert ReportAttachment.query.filter_by(report_id=report_id, page_key="scene-diagram").first() is None
    finally:
        _dispose_app(client.application)


def test_report_type_can_require_scene_diagram_before_submit(monkeypatch, tmp_path):
    monkeypatch.setenv("MCPD_CALL_TYPE_RULES_PATH", str(tmp_path / "call_type_rules.json"))
    client = _logged_in_client()
    try:
        from app.services.call_type_rules import save_call_type_rules

        with client.application.app_context():
            save_call_type_rules({
                "traffic-accident": {
                    "title": "Traffic Accident",
                    "slug": "traffic-accident",
                    "diagramAllowed": True,
                    "diagramRequired": True,
                    "diagramModes": ["report"],
                    "diagramScenarios": ["rear_end"],
                    "active": True,
                }
            })
            user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
            report = Report(
                title="Required Diagram Test",
                owner_id=user.id,
                status="DRAFT",
                call_type_slug="traffic-accident",
                facts_text="V1 struck V2 from the rear.",
                narrative_text="V1 struck V2 from the rear.",
            )
            db.session.add(report)
            db.session.commit()
            report_id = report.id

        response = client.post(f"/reports/{report_id}/submit", follow_redirects=True)
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "attached scene diagram" in body

        detail_response = client.get(f"/reports/{report_id}")
        detail_html = detail_response.get_data(as_text=True)
        assert "This report type requires a scene diagram" in detail_html
    finally:
        _dispose_app(client.application)
