from app import create_app
from app.extensions import db
from app.models import Form, User


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = False
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def test_forms_library_hides_test_only_records_from_operational_page():
    client = _logged_in_client()
    with client.application.app_context():
        form = Form(
            title='Test Required Form',
            category='Pytest',
            file_path='data/uploads/forms/test-required-form.pdf',
            is_active=True,
        )
        db.session.add(form)
        db.session.commit()
        form_id = form.id

    try:
        response = client.get('/forms')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'Test Required Form' not in html
        assert f'/forms/{form_id}/download' not in html
    finally:
        with client.application.app_context():
            form = db.session.get(Form, form_id)
            if form:
                db.session.delete(form)
                db.session.commit()
