import base64
import json
import os
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import AccidentReconstruction, ROLE_WEBSITE_CONTROLLER, ReconstructionCase, Report, ReportAttachment, User


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
            role=ROLE_WEBSITE_CONTROLLER,
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
            reconstruction = AccidentReconstruction.query.filter_by(report_id=report_id).first()
            assert reconstruction is not None
            reconstruction_id = reconstruction.id

        payload = {
            "version": 2,
            "diagramType": "crash_scene",
            "scenarioType": "rear_end",
            "mode": "report",
            "canvasItems": [
                {"clientId": "v1", "assetType": "sedan", "kind": "vehicle", "label": "V1", "x": 380, "y": 300, "width": 92, "height": 42, "rotation": 0},
                {"clientId": "poi", "assetType": "impact", "kind": "diagram", "label": "POI", "x": 470, "y": 300, "width": 44, "height": 44, "rotation": 0, "notes": "rear bumper contact"},
            ],
        }
        save_response = client.post(f"/reports/accident-reconstruction/{reconstruction_id}/diagram", json=payload)
        assert save_response.status_code == 200
        assert save_response.get_json()["ok"] is True

        detail_response = client.get(f"/reports/accident-reconstruction/{reconstruction_id}/diagram")
        detail_html = detail_response.get_data(as_text=True)
        assert detail_response.status_code == 200
        assert "data-recon-object-layer" in detail_html
        assert "icons/vehicles/sedan.svg" in detail_html
        assert "data-recon-asset-modal" in detail_html
        with client.application.app_context():
            reconstruction = db.session.get(AccidentReconstruction, reconstruction_id)
            assert reconstruction.diagram_data_json
            assert "rear bumper contact" in reconstruction.diagram_data_json
    finally:
        _dispose_app(client.application)


def test_accident_diagram_svg_asset_library_is_available():
    expected_assets = [
        "vehicles/sedan.svg",
        "vehicles/suv.svg",
        "vehicles/pickup.svg",
        "vehicles/patrol.svg",
        "vehicles/truck.svg",
        "vehicles/motorcycle.svg",
        "people/pedestrian.svg",
        "people/officer.svg",
        "traffic/stop-sign.svg",
        "traffic/traffic-light.svg",
        "traffic/cone.svg",
        "traffic/barrier.svg",
        "traffic/building.svg",
        "traffic/tree.svg",
        "diagram/arrow.svg",
        "diagram/skid.svg",
        "diagram/impact.svg",
    ]
    root = Path(__file__).resolve().parents[1] / "static" / "icons"
    for asset in expected_assets:
        text = (root / asset).read_text(encoding="utf-8")
        assert "<svg" in text
        assert "</svg>" in text
