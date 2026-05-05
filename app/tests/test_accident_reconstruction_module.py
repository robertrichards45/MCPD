import json
from io import BytesIO

from app import create_app
from app.extensions import db
from app.models import (
    AccidentReconstruction,
    ReconstructionMeasurement,
    ReconstructionMedia,
    ReconstructionObject,
    ReconstructionTimelineItem,
    ReconstructionVehicle,
    Report,
    User,
)


def _logged_in_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
    return client


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _cleanup_reconstruction(reconstruction_id):
    if not reconstruction_id:
        return
    ReconstructionTimelineItem.query.filter_by(reconstruction_id=reconstruction_id).delete()
    ReconstructionMedia.query.filter_by(reconstruction_id=reconstruction_id).delete()
    ReconstructionMeasurement.query.filter_by(reconstruction_id=reconstruction_id).delete()
    ReconstructionObject.query.filter_by(reconstruction_id=reconstruction_id).delete()
    ReconstructionVehicle.query.filter_by(reconstruction_id=reconstruction_id).delete()
    AccidentReconstruction.query.filter_by(id=reconstruction_id).delete()
    db.session.commit()


def test_accident_reconstruction_create_detail_diagram_save_and_export():
    client = _logged_in_client()
    reconstruction_id = None
    try:
        create_response = client.post(
            "/reports/accident-reconstruction/new",
            data={
                "incident_number": "AR-TEST-001",
                "title": "Two vehicle intersection crash",
                "location": "Exchange Ave / Smith St",
                "date_time": "2026-05-04T14:32",
                "weather": "Clear",
                "road_surface": "Dry",
                "notes": "V1 entered the intersection and contacted V2 at the marked point of impact.",
            },
            follow_redirects=False,
        )
        assert create_response.status_code in {302, 303}

        with client.application.app_context():
            row = AccidentReconstruction.query.filter_by(incident_number="AR-TEST-001").first()
            assert row is not None
            reconstruction_id = row.id

        detail_response = client.get(f"/reports/accident-reconstruction/{reconstruction_id}")
        detail_html = detail_response.get_data(as_text=True)
        assert detail_response.status_code == 200
        assert "Scene Diagram" in detail_html
        assert "Vehicle Dynamics" in detail_html
        assert "Calculations are estimates and must be verified by trained personnel." in detail_html

        vehicle_response = client.post(
            f"/reports/accident-reconstruction/{reconstruction_id}/vehicle",
            data={
                "label": "V1",
                "type": "Sedan",
                "direction": "Eastbound",
                "pre_crash_speed": "35",
                "impact_speed": "28",
                "post_crash_speed": "5",
            },
            follow_redirects=False,
        )
        assert vehicle_response.status_code in {302, 303}

        measurement_response = client.post(
            f"/reports/accident-reconstruction/{reconstruction_id}/measurement",
            data={
                "measurement_type": "skid mark length",
                "label": "Skid 1",
                "value": "48",
                "units": "ft",
                "start_x": "200",
                "start_y": "240",
                "end_x": "300",
                "end_y": "260",
            },
            follow_redirects=False,
        )
        assert measurement_response.status_code in {302, 303}

        timeline_response = client.post(
            f"/reports/accident-reconstruction/{reconstruction_id}/timeline",
            data={"event_time": "14:32:18", "event_type": "impact", "description": "V1 contacted V2 in the intersection."},
            follow_redirects=False,
        )
        assert timeline_response.status_code in {302, 303}

        media_response = client.post(
            f"/reports/accident-reconstruction/{reconstruction_id}/media",
            data={
                "media_type": "scene photo",
                "description": "Overview from southeast corner",
                "file": (BytesIO(b"fake image bytes"), "scene.jpg"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert media_response.status_code in {302, 303}

        diagram_response = client.get(f"/reports/accident-reconstruction/{reconstruction_id}/diagram")
        diagram_html = diagram_response.get_data(as_text=True)
        assert diagram_response.status_code == 200
        assert "data-accident-recon" in diagram_html
        assert "Clear All" in diagram_html
        assert "Vehicle" in diagram_html
        assert "deer" not in diagram_html.lower()

        with client.application.app_context():
            vehicle = ReconstructionVehicle.query.filter_by(reconstruction_id=reconstruction_id, label="V1").first()
            assert vehicle is not None
            vehicle_id = vehicle.id

        save_response = client.post(
            f"/reports/accident-reconstruction/{reconstruction_id}/diagram",
            data=json.dumps(
                {
                    "vehicles": [{"id": vehicle_id, "label": "V1", "type": "vehicle", "x": 410, "y": 275, "rotation": 12}],
                    "objects": [{"clientId": "poi-1", "type": "point", "label": "POI", "x": 500, "y": 292, "rotation": 0}],
                    "measurements": [{"label": "Skid 1", "value": "48", "units": "ft", "startX": 200, "startY": 240, "endX": 300, "endY": 260}],
                    "units": "ft",
                }
            ),
            content_type="application/json",
        )
        assert save_response.status_code == 200
        assert save_response.get_json()["ok"] is True

        with client.application.app_context():
            row = db.session.get(AccidentReconstruction, reconstruction_id)
            vehicle = db.session.get(ReconstructionVehicle, vehicle_id)
            assert row.diagram_data_json
            assert vehicle.x_position == 410
            assert vehicle.y_position == 275
            assert vehicle.rotation == 12

        export_response = client.get(f"/reports/accident-reconstruction/{reconstruction_id}/export")
        assert export_response.status_code == 200
        assert export_response.headers["Content-Type"].startswith("application/pdf")
        assert export_response.data.startswith(b"%PDF")
        assert "accident-reconstruction-AR-TEST-001.pdf" in export_response.headers.get("Content-Disposition", "")
    finally:
        with client.application.app_context():
            _cleanup_reconstruction(reconstruction_id)
        _dispose_app(client.application)


def test_accident_reconstruction_routes_render_mobile_shell_cleanly():
    client = _logged_in_client()
    reconstruction_id = None
    try:
        create_response = client.post(
            "/reports/accident-reconstruction/new",
            data={"incident_number": "AR-MOBILE-001", "title": "Mobile reconstruction route check"},
            follow_redirects=False,
        )
        assert create_response.status_code in {302, 303}
        with client.application.app_context():
            row = AccidentReconstruction.query.filter_by(incident_number="AR-MOBILE-001").first()
            assert row is not None
            reconstruction_id = row.id

        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile"}
        for path in [
            "/reports/accident-reconstruction",
            f"/reports/accident-reconstruction/{reconstruction_id}",
            f"/reports/accident-reconstruction/{reconstruction_id}/diagram",
        ]:
            response = client.get(path, headers=headers)
            html = response.get_data(as_text=True)
            assert response.status_code == 200, path
            assert "Traceback" not in html
            assert "reports-command-sidebar" in html
            assert "Accident Reconstruction" in html
            assert "href=\"#\"" not in html
    finally:
        with client.application.app_context():
            _cleanup_reconstruction(reconstruction_id)
        _dispose_app(client.application)


def test_report_connected_scene_diagram_creates_linked_reconstruction():
    client = _logged_in_client()
    report_id = None
    reconstruction_id = None
    try:
        with client.application.app_context():
            user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
            report = Report(title="Crash report linked reconstruction", owner_id=user.id, status="DRAFT")
            db.session.add(report)
            db.session.commit()
            report_id = report.id

        response = client.get(f"/reports/{report_id}/scene-diagram", follow_redirects=False)
        assert response.status_code in {302, 303}
        assert "/reports/accident-reconstruction/" in response.headers["Location"]
        assert response.headers["Location"].endswith("/diagram")

        with client.application.app_context():
            row = AccidentReconstruction.query.filter_by(report_id=report_id).first()
            assert row is not None
            reconstruction_id = row.id
            assert row.incident_number == f"RPT-{report_id}"

        detail_response = client.get(f"/reports/{report_id}")
        html = detail_response.get_data(as_text=True)
        assert detail_response.status_code == 200
        assert "Scene Diagram / Accident Reconstruction" in html
        assert "Open Diagram" in html
        assert "Export PDF" in html
    finally:
        with client.application.app_context():
            _cleanup_reconstruction(reconstruction_id)
            if report_id:
                Report.query.filter_by(id=report_id).delete()
                db.session.commit()
        _dispose_app(client.application)
