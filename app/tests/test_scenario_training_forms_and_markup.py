from app import create_app
from app.extensions import db
from app.models import Form, ROLE_WEBSITE_CONTROLLER, SavedForm, User
from app.simulator.training_forms import training_form_definition, training_form_definitions


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='training-forms-ci').first()
        if user is None:
            user = User(
                username='training-forms-ci',
                name='Training Forms CI Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return app, client


def _complete_s004(client):
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S004')
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        state['complete'] = True
        s['sentinel_scenario_lab_v2'] = state


def _submit_revision(client, action='submit', narrative='The trainee documented the synthetic call in chronological order.'):
    return client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': action,
        'selected_documents': ['OPNAV 5580 2 Voluntary Statement'],
        'cid_decision': 'screen',
        'notification_notes': 'Synthetic screening decision recorded for training.',
        'narrative': narrative,
    }, follow_redirects=False)


def _training_form_payload(document_name):
    payload = {'_csrf_token': 'test-token'}
    for definition in training_form_definitions([document_name]):
        for field in definition['fields']:
            if not field['required']:
                continue
            if field['type'] == 'checkbox':
                payload[field['input_name']] = 'yes'
            elif field['type'] == 'date':
                payload[field['input_name']] = '2026-09-14'
            elif field['type'] == 'time':
                payload[field['input_name']] = '04:20'
            elif field['type'] == 'number':
                payload[field['input_name']] = '1'
            else:
                payload[field['input_name']] = 'Synthetic training value'
    return payload


def test_registry_backed_training_replica_uses_controlled_fields():
    definition = training_form_definition('OPNAV 5580 2 Voluntary Statement')
    assert definition['source'] == 'official_form_field_registry'
    assert definition['registry_pattern'] == 'voluntary statement'
    assert any(field['label'] == 'Statement' for field in definition['fields'])
    assert all('blotter' not in field['label'].lower() for field in definition['fields'])


def test_training_form_completion_does_not_create_operational_form_records():
    app, client = _client()
    _complete_s004(client)
    response = _submit_revision(client)
    assert response.status_code in (302, 303)
    assert '/scenario-paperwork/training-forms' in response.headers['Location']

    with app.app_context():
        before_forms = Form.query.count()
        before_saved = SavedForm.query.count()

    response = client.post(
        '/sentinel/fto-center/scenario-paperwork/training-forms',
        data=_training_form_payload('OPNAV 5580 2 Voluntary Statement'),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'Training forms saved' in response.get_data(as_text=True)

    with app.app_context():
        assert Form.query.count() == before_forms
        assert SavedForm.query.count() == before_saved

    with client.session_transaction() as s:
        submission = s['sentinel_scenario_lab_v2']['training_package']['submissions'][-1]
        assert submission['forms_complete'] is True
        assert len(submission['training_forms']) == 1
        assert len(submission['training_form_history']) == 1


def test_fto_markup_preserves_original_submission_and_resolution_history():
    _app, client = _client()
    _complete_s004(client)
    original = 'Original synthetic narrative remains unchanged after FTO markup.'
    _submit_revision(client, narrative=original)
    client.post(
        '/sentinel/fto-center/scenario-paperwork/training-forms',
        data=_training_form_payload('OPNAV 5580 2 Voluntary Statement'),
        follow_redirects=True,
    )
    client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': 'self_assess',
        'what_went_well': 'Scene communication.',
        'what_change': 'Improve documentation detail.',
        'decision_basis': 'Synthetic training facts and procedure.',
        'notifications_considered': 'Required synthetic screening.',
        'training_need': 'More report practice.',
    }, follow_redirects=True)

    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    response = client.post(f'/sentinel/fto-center/scenario-paperwork/run/{run_id}/markup', data={
        '_csrf_token': 'test-token',
        'action': 'annotate_narrative',
        'line_number': '1',
        'category': 'clarity',
        'comment': 'Clarify who supplied this fact.',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'annotation saved' in response.get_data(as_text=True).lower()

    client.get('/sentinel/fto-center/scenario-paperwork/')
    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert package['submissions'][0]['narrative'] == original
        assert len(package['annotations']) == 1
        annotation_id = package['annotations'][0]['id']

    response = client.post(f'/sentinel/fto-center/scenario-paperwork/run/{run_id}/markup', data={
        '_csrf_token': 'test-token',
        'action': 'resolve_annotation',
        'annotation_id': annotation_id,
        'resolution_note': 'Addressed during coaching.',
    }, follow_redirects=True)
    assert response.status_code == 200

    client.get('/sentinel/fto-center/scenario-paperwork/')
    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert len(package['annotations']) == 1
        assert package['annotations'][0]['comment'] == 'Clarify who supplied this fact.'
        assert len(package['annotation_actions']) == 1
        assert package['annotation_actions'][0]['action'] == 'resolve'
