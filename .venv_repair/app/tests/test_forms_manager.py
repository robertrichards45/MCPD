from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, Form, User
from app.services import form_source_updates


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _manager_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        user.role = ROLE_WEBSITE_CONTROLLER
        form = Form.query.filter_by(title='Manager Test Form Original').first()
        if not form:
            form = Form(
                title='Manager Test Form Original',
                category='Testing',
                version_label='draft',
                file_path='data/uploads/forms/manager-test-form.pdf',
                uploaded_by=user.id,
                is_active=True,
            )
            db.session.add(form)
        else:
            form.category = 'Testing'
            form.version_label = 'draft'
            form.is_active = True
        db.session.commit()
        form_id = form.id
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return app, client, form_id


def test_forms_manager_edits_and_hides_forms():
    app, client, form_id = _manager_client()
    try:
        response = client.get('/forms/manage')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Forms Manager' in body
            assert 'Add New Form' in body
        finally:
            response.close()

        response = client.post(
            '/forms/manage',
            data={
                'form_id': str(form_id),
                'title': 'Manager Test Form Updated',
                'category': 'Field Test',
                'version_label': '2026',
                'retention_mode': 'full_save_allowed',
                'notes': 'Updated through forms manager test.',
                'allow_email': 'on',
                'allow_download': 'on',
                'allow_blank_print': 'on',
                'allow_completed_save': 'on',
                'is_active': 'on',
                'action': 'save',
            },
            follow_redirects=False,
        )
        try:
            assert response.status_code == 302
        finally:
            response.close()

        response = client.get('/forms?q=Manager+Test+Form+Updated')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Manager Test Form Updated' in body
            assert 'Field Test' in body
        finally:
            response.close()

        response = client.post(
            '/forms/manage',
            data={'form_id': str(form_id), 'action': 'hide'},
            follow_redirects=False,
        )
        try:
            assert response.status_code == 302
        finally:
            response.close()

        response = client.get('/forms?q=Manager+Test+Form+Updated')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            with app.app_context():
                assert db.session.get(Form, form_id).is_active is False
        finally:
            response.close()
    finally:
        _dispose_app(app)


def test_forms_manager_can_apply_direct_official_pdf_update(monkeypatch):
    app, client, form_id = _manager_client()

    class FakeResponse:
        status_code = 200
        headers = {'content-type': 'application/pdf'}
        content = b'%PDF-1.4\n% official replacement\n'

    monkeypatch.setattr(form_source_updates.requests, 'get', lambda *_args, **_kwargs: FakeResponse())
    try:
        response = client.post(
            '/forms/manage',
            data={
                'form_id': str(form_id),
                'title': 'Manager Test Form Updated',
                'category': 'Field Test',
                'version_label': '2026',
                'retention_mode': 'full_save_allowed',
                'official_source_url': 'https://forms.documentservices.dla.mil/order/test-form.pdf',
                'official_source_version': 'official-test',
                'source_auto_update_enabled': 'on',
                'allow_email': 'on',
                'allow_download': 'on',
                'allow_blank_print': 'on',
                'allow_completed_save': 'on',
                'is_active': 'on',
                'action': 'update_source',
            },
            follow_redirects=False,
        )
        try:
            assert response.status_code == 302
        finally:
            response.close()
        with app.app_context():
            form = db.session.get(Form, form_id)
            assert form.official_source_url == 'https://forms.documentservices.dla.mil/order/test-form.pdf'
            assert form.official_source_version == 'official-test'
            assert form.source_auto_update_enabled is True
            assert form.official_source_hash
            assert 'updated' in form.official_source_last_status
            assert form.file_path.endswith('.pdf')
    finally:
        _dispose_app(app)


def test_form_source_update_marks_dso_storefront_as_gated(monkeypatch, tmp_path):
    class FakeResponse:
        status_code = 200
        headers = {'content-type': 'text/html'}
        content = b'<html><script>window.location.href="/dsf/SmartStore.aspx";</script>Login</html>'

    form = type('FormLike', (), {
        'title': 'DSO Test',
        'file_path': str(tmp_path / 'current.pdf'),
        'official_source_url': 'https://dso.dla.mil/DSF/SmartStore.aspx',
    })()
    monkeypatch.setattr(form_source_updates.requests, 'get', lambda *_args, **_kwargs: FakeResponse())
    result = form_source_updates.check_and_update_form_source(form, str(tmp_path), apply_update=True)
    assert result.ok is False
    assert result.status == 'requires_login'
