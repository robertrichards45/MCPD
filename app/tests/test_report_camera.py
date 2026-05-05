from io import BytesIO
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Report, ReportAttachment, User


def _client_with_report():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        report = Report(title='Traffic Accident Camera Test', owner_id=user.id, status='DRAFT')
        db.session.add(report)
        db.session.commit()
        report_id = report.id
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
        return app, client, report_id


def test_report_camera_page_renders_from_report():
    app, client, report_id = _client_with_report()
    try:
        response = client.get(f'/reports/{report_id}/camera')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'Report Camera' in html
        assert 'does not save the photo to the phone camera roll' in html
        assert f'/reports/{report_id}/photo' in html
    finally:
        with app.app_context():
            report = db.session.get(Report, report_id)
            if report:
                db.session.delete(report)
                db.session.commit()


def test_report_photo_upload_stores_app_attachment_not_phone_file():
    app, client, report_id = _client_with_report()
    attachment_id = None
    saved_path = None
    try:
        response = client.post(
            f'/reports/{report_id}/photo',
            data={
                'page_key': 'report-photo-vehicle',
                'label': 'Vehicle Damage',
                'photo': (BytesIO(b'fake-image'), 'damage.jpg'),
            },
            content_type='multipart/form-data',
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload['ok'] is True
        attachment_id = payload['id']

        with app.app_context():
            attachment = db.session.get(ReportAttachment, attachment_id)
            assert attachment is not None
            saved_path = Path(attachment.file_path)
            assert attachment.report_id == report_id
            assert attachment.page_key == 'report-photo-vehicle'
            assert saved_path.exists()
            assert 'reports' in saved_path.parts
            assert 'photos' in saved_path.parts

        download = client.get(f'/reports/{report_id}/attachments/{attachment_id}/download')
        assert download.status_code == 200
        assert download.data == b'fake-image'
    finally:
        with app.app_context():
            if attachment_id:
                attachment = db.session.get(ReportAttachment, attachment_id)
                if attachment:
                    db.session.delete(attachment)
            report = db.session.get(Report, report_id)
            if report:
                db.session.delete(report)
            db.session.commit()
            if saved_path and saved_path.exists():
                try:
                    saved_path.unlink()
                except PermissionError:
                    pass
