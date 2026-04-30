from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, Form, User


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _manager_client(monkeypatch, tmp_path):
    monkeypatch.setenv('MCPD_PAPERWORK_GUIDE_CUSTOM_PATH', str(tmp_path / 'paperwork_guide_custom.json'))
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        user.role = ROLE_WEBSITE_CONTROLLER
        if not Form.query.filter_by(title='Navigator Pickable Test Form').first():
            db.session.add(
                Form(
                    title='Navigator Pickable Test Form',
                    category='Testing',
                    file_path='data/uploads/forms/navigator-pickable-test.pdf',
                    uploaded_by=user.id,
                    is_active=True,
                )
            )
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return app, client


def test_paperwork_guide_manager_adds_and_hides_entries(monkeypatch, tmp_path):
    app, client = _manager_client(monkeypatch, tmp_path)
    try:
        response = client.get('/incident-paperwork-guide/manage')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Navigator Editor' in body
            assert 'Add New Entry' in body
            assert 'Click available forms to add them' in body
            assert 'Navigator Pickable Test Form' in body
        finally:
            response.close()

        response = client.post(
            '/incident-paperwork-guide/manage',
            data={
                'title': 'Noise Complaint',
                'slug': 'noise-complaint',
                'description': 'Quiet-hours or nuisance call.',
                'paperwork_forms': ['Navigator Pickable Test Form'],
                'required_paperwork_text': 'Narrative\nVoluntary Statement',
                'officer_responsibilities': 'Identify reporting party\nDocument warning or citation',
                'notes': 'Check local quiet-hours ordinance',
                'active': 'on',
                'action': 'save',
            },
            follow_redirects=False,
        )
        try:
            assert response.status_code == 302
        finally:
            response.close()

        response = client.get('/incident-paperwork-guide?q=Noise')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Noise Complaint' in body
            assert 'Navigator Pickable Test Form' in body
            assert 'Narrative' in body
            assert 'Voluntary Statement' in body
        finally:
            response.close()

        response = client.post(
            '/incident-paperwork-guide/manage',
            data={
                'title': 'Noise Complaint',
                'slug': 'noise-complaint',
                'action': 'delete',
            },
            follow_redirects=False,
        )
        try:
            assert response.status_code == 302
        finally:
            response.close()

        response = client.get('/incident-paperwork-guide?q=Noise')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Noise Complaint' not in body
        finally:
            response.close()
    finally:
        _dispose_app(app)
