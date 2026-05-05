from app import create_app
from app.extensions import db
from app.models import User


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _text_response(response):
    try:
        return response.get_data(as_text=True)
    finally:
        response.close()


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='Robertrichards').first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def test_mobile_statement_pages_render_for_authenticated_user():
    client = _logged_in_client()
    try:
        cases = [
            ('/mobile/incident/statements', 'Statement Launcher'),
            ('/mobile/incident/statements/entry', 'Statement Entry'),
            ('/mobile/incident/statements/review', 'Statement Review'),
            ('/mobile/incident/statements/signature', 'Signature Capture'),
        ]
        for url, expected in cases:
            response = client.get(url)
            try:
                assert response.status_code == 200
                assert expected in response.get_data(as_text=True)
            finally:
                response.close()
    finally:
        _dispose_app(client.application)


def test_mobile_home_keeps_approved_field_actions():
    client = _logged_in_client()
    try:
        response = client.get('/mobile/home')
        assert response.status_code == 200
        html = _text_response(response)
        assert 'Law Lookup' in html
        assert 'Start Report' in html or 'Continue Report' in html
        assert 'Forms' in html
        assert 'Orders' in html
        assert 'Training' in html
        assert 'Saved' in html
        assert 'Officer Stats' in html
        assert 'Contact Info' in html
        assert 'Voluntary Statement' not in html
        assert 'Open Statements' not in html
    finally:
        _dispose_app(client.application)
