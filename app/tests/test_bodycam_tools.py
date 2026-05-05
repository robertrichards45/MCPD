from io import BytesIO
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import BodycamFootage, User


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
        return app, client, user.id


def test_bodycam_desktop_and_mobile_pages_render():
    _app, client, _user_id = _logged_in_client()

    for path, expected in [
        ('/bodycam', 'Bodycam Footage'),
        ('/bodycam/new', 'Body Cam Mode'),
        ('/mobile/bodycam', 'Body Cam Mode'),
        ('/mobile/bodycam/footage', 'Bodycam Footage'),
        ('/tools/narrative', 'Narrative Creator / 5W Builder'),
        ('/mobile/tools/narrative', 'Narrative / 5W Builder'),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.get_data(as_text=True)


def test_bodycam_upload_stores_video_and_transcript():
    app, client, user_id = _logged_in_client()
    response = client.post(
        '/bodycam/upload',
        data={
            'title': 'Test Bodycam',
            'incident_number': 'INC-1',
            'location': 'Gate 1',
            'transcript_text': 'Officer contacted the subject.',
            'duration_seconds': '5',
            'video': (BytesIO(b'fake-webm'), 'bodycam.webm'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['ok'] is True

    with app.app_context():
        item = db.session.get(BodycamFootage, payload['id'])
        assert item is not None
        saved_path = Path(item.file_path)
        assert item.officer_user_id == user_id
        assert item.transcript_text == 'Officer contacted the subject.'
        assert item.location == 'Gate 1'
        db.session.delete(item)
        db.session.commit()
        if saved_path.exists():
            saved_path.unlink()


def test_mobile_home_and_more_expose_bodycam_and_narrative_tools():
    _app, client, _user_id = _logged_in_client()

    home = client.get('/mobile/home').get_data(as_text=True)
    assert 'Law Lookup' in home
    assert 'Start Report' in home
    assert 'Forms' in home
    assert 'Orders' in home
    assert 'Training' in home
    assert 'Saved' in home

    more = client.get('/mobile/more').get_data(as_text=True)
    assert 'Body Cam Mode' in more
    assert 'Bodycam Footage' in more
    assert 'Narrative / 5W Builder' in more
    assert '/mobile/bodycam' in more
    assert '/mobile/tools/narrative' in more
