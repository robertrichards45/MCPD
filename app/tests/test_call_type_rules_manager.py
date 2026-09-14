import json

from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, Form, User
from app.services.call_type_rules import load_call_type_rules
from app.services.call_type_rules_v2 import evaluate_call_type_rule


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _manager_client(monkeypatch, tmp_path):
    monkeypatch.setenv('MCPD_CALL_TYPE_RULES_PATH', str(tmp_path / 'call_type_rules.json'))
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='call-type-ci').first()
        if user is None:
            user = User(
                username='call-type-ci',
                name='Call Type CI Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
                builder_mode_access=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
        else:
            user.role = ROLE_WEBSITE_CONTROLLER
            user.active = True
            user.pending_approval = False

        for title in ('Test Required Form', 'Test Triggered Form', 'Test Legacy Form'):
            if not Form.query.filter_by(title=title).first():
                db.session.add(
                    Form(
                        title=title,
                        category='Test',
                        file_path='data/uploads/forms/' + title.lower().replace(' ', '-') + '.pdf',
                        is_active=True,
                    )
                )
        db.session.commit()
        user_id = user.id

        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True
            session['_csrf_token'] = 'test-token'
    return app, client


def test_call_type_manager_adds_rules_and_mobile_consumes_them(monkeypatch, tmp_path):
    app, client = _manager_client(monkeypatch, tmp_path)
    try:
        response = client.get('/forms/call-types')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Call Type Paperwork Manager' in body
            assert 'Circumstance Rules' in body
            assert 'Not Normally Required' in body
        finally:
            response.close()

        response = client.post(
            '/forms/call-types',
            data={
                '_csrf_token': 'test-token',
                'title': 'Noise Complaint',
                'slug': 'noise-complaint',
                'short_label': 'Noise',
                'description': 'Quiet-hours or nuisance call.',
                'recommended_forms': ['Test Required Form'],
                'recommended_forms_extra': 'Narrative',
                'optional_forms_extra': (
                    'Voluntary Statement\n'
                    '@when:written_statement|Test Triggered Form|Use when the configured circumstance applies.\n'
                    '@notnormally:Test Legacy Form|Not part of the normal packet.'
                ),
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
        rule = rules['noise-complaint']
        assert rule['recommendedForms'] == ['Test Required Form', 'Narrative']
        assert rule['optionalForms'] == ['Voluntary Statement']
        assert rule['conditionalRules'][0]['key'] == 'written_statement'
        assert rule['conditionalRules'][0]['forms'] == ['Test Triggered Form']
        assert rule['notNormallyRequiredForms'] == [
            {'form': 'Test Legacy Form', 'why': 'Not part of the normal packet.'}
        ]

        inactive_packet = evaluate_call_type_rule(rule, {'written_statement': False})
        assert 'Test Triggered Form' not in inactive_packet['requiredForms']
        assert inactive_packet['remainingConditions'][0]['key'] == 'written_statement'

        active_packet = evaluate_call_type_rule(rule, {'written_statement': True})
        assert 'Test Triggered Form' in active_packet['requiredForms']
        assert active_packet['triggeredConditions'][0]['key'] == 'written_statement'

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
            assert parsed['noise-complaint']['conditionalRules'][0]['key'] == 'written_statement'
            assert parsed['noise-complaint']['notNormallyRequiredForms'][0]['form'] == 'Test Legacy Form'
        finally:
            response.close()

        response = client.get('/reports')
        try:
            body = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Paperwork Packet Builder' in body
            assert 'Call Type Rules Engine' in body
            assert 'conditionalRules' in body
            assert 'notNormallyRequiredForms' in body
        finally:
            response.close()
    finally:
        _dispose_app(app)
