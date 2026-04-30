import json

from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, Form, User
from app.services.call_type_rules import load_call_type_rules


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _manager_client(monkeypatch, tmp_path):
    monkeypatch.setenv('MCPD_CALL_TYPE_RULES_PATH', str(tmp_path / 'call_type_rules.json'))
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        user.role = ROLE_WEBSITE_CONTROLLER
        if not Form.query.filter_by(title='Test Required Form').first():
            db.session.add(
                Form(
                    title='Test Required Form',
                    category='Test',
                    file_path='data/uploads/forms/test-required-form.pdf',
                    is_active=True,
                )
            )
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return app, client


def test_call_type_manager_adds_rules_and_mobile_consumes_them(monkeypatch, tmp_path):
    app, client = _manager_client(monkeypatch, tmp_path)
    try:
        response = client.get('/forms/call-types')
        try:
            assert response.status_code == 200
            assert 'Call Type Paperwork Manager' in response.get_data(as_text=True)
        finally:
            response.close()

        response = client.post(
            '/forms/call-types',
            data={
                'title': 'Noise Complaint',
                'slug': 'noise-complaint',
                'short_label': 'Noise',
                'description': 'Quiet-hours or nuisance call.',
                'recommended_forms': ['Test Required Form'],
                'recommended_forms_extra': 'Narrative',
                'optional_forms_extra': 'Voluntary Statement',
                'statutes': 'Quiet hours\nDisorderly conduct review',
                'checklist_items': 'Identify reporting party\nDocument warning or citation',
                'active': 'on',
                'action': 'save',
            },
            follow_redirects=False,
        )
        try:
            assert response.status_code == 302
        finally:
            response.close()

        rules = load_call_type_rules(include_inactive=True)
        assert rules['noise-complaint']['recommendedForms'] == ['Test Required Form', 'Narrative']
        assert rules['noise-complaint']['optionalForms'] == ['Voluntary Statement']

        response = client.get('/mobile/incident/start')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'mobile-call-type-rules-data' in body
            assert 'Noise Complaint' in body
            raw = body.split('<script id="mobile-call-type-rules-data" type="application/json">', 1)[1]
            raw = raw.split('</script>', 1)[0]
            parsed = json.loads(raw)
            assert parsed['noise-complaint']['recommendedForms'] == ['Test Required Form', 'Narrative']
        finally:
            response.close()
    finally:
        _dispose_app(app)
