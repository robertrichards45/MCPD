from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.training_requirements import requirements_for_scenario


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-paperwork-ci').first()
        if user is None:
            user = User(
                username='scenario-paperwork-ci',
                name='Scenario Paperwork CI Controller',
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
    return client


def _complete_s004(client):
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S004')
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        state['complete'] = True
        s['sentinel_scenario_lab_v2'] = state


def _submit_package(client, narrative='Synthetic training narrative based only on facts developed during the run.'):
    return client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': 'submit',
        'selected_documents': ['OPNAV 5580 2 Voluntary Statement'],
        'cid_decision': 'screen',
        'notification_notes': 'Screen with CID and provide the developed facts.',
        'narrative': narrative,
    }, follow_redirects=True)


def test_requirements_never_assign_blotter_to_trainee():
    for scenario_id in ('S001', 'S002', 'S003', 'S004', 'S005', 'S006'):
        requirements = requirements_for_scenario(scenario_id)
        assert requirements['trainee_blotter_required'] is False
        assert all('blotter' not in item.lower() for item in requirements['officer_documents'])
        assert all('desk journal' not in item.lower() for item in requirements['officer_documents'])


def test_property_and_theft_training_require_cid_screening():
    assert requirements_for_scenario('S003')['cid']['requirement'] == 'screen'
    assert requirements_for_scenario('S004')['cid']['requirement'] == 'screen'
    assert requirements_for_scenario('S004')['cid']['verified_for_training'] is True


def test_active_call_cannot_open_post_call_paperwork():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S004')
    response = client.get('/sentinel/fto-center/scenario-paperwork/', follow_redirects=True)
    assert response.status_code == 200
    assert 'Finish or clear the synthetic call' in response.get_data(as_text=True)


def test_completed_call_can_submit_and_preserve_original_package():
    client = _client()
    _complete_s004(client)

    response = client.get('/sentinel/fto-center/scenario-paperwork/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Training Package' in html
    assert 'not part of the trainee paperwork exercise' in html.lower()

    response = _submit_package(client)
    assert response.status_code == 200
    assert 'original submission is preserved' in response.get_data(as_text=True).lower()

    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert package['status'] == 'SUBMITTED'
        assert len(package['submissions']) == 1
        assert package['submissions'][0]['revision'] == 0
        assert package['submissions'][0]['cid_decision'] == 'screen'

    client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': 'revise',
        'selected_documents': ['OPNAV 5580 2 Voluntary Statement'],
        'cid_decision': 'screen',
        'notification_notes': 'CID screening documented in the training package.',
        'narrative': 'Revision one preserves the original and corrects the synthetic narrative.',
    }, follow_redirects=True)

    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert len(package['submissions']) == 2
        assert package['submissions'][0]['revision'] == 0
        assert package['submissions'][1]['revision'] == 1
        assert 'facts developed' in package['submissions'][0]['narrative']
        assert 'Revision one' in package['submissions'][1]['narrative']


def test_fto_can_return_package_and_trainee_session_receives_review():
    client = _client()
    _complete_s004(client)
    _submit_package(client)

    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    response = client.post(f'/sentinel/fto-center/scenario-paperwork/run/{run_id}', data={
        '_csrf_token': 'test-token',
        'fto_action': 'correction',
        'fto_comments': 'Correct the chronology and make the CID screening documentation clearer.',
        'remediation_area': '',
        'remediation_plan': '',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'returned for correction' in response.get_data(as_text=True).lower()

    response = client.get('/sentinel/fto-center/scenario-paperwork/')
    html = response.get_data(as_text=True)
    assert 'Correction Required' in html
    assert 'Correct the chronology' in html

    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert package['status'] == 'CORRECTION_REQUIRED'
        assert len(package['submissions']) == 1
        assert len(package['review_history']) == 1
        assert package['review_history'][0]['revision_reviewed'] == 0
