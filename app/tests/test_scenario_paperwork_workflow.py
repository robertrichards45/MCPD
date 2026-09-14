from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.training_requirements import requirements_for_scenario, trainee_requirement_choices


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
        'cid_decision': 'screen',
        'notification_notes': 'Training screening decision documented.',
        'narrative': narrative,
    }, follow_redirects=True)


def _self_assess(client):
    return client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': 'self_assess',
        'what_went_well': 'I developed the available facts and kept the event organized.',
        'what_change': 'I would improve chronology and documentation clarity.',
        'decision_basis': 'I relied on the facts developed during the synthetic exercise and training procedures.',
        'notifications_considered': 'I considered the configured training notifications based on the exercise facts.',
        'training_need': 'Additional documentation practice would be useful.',
    }, follow_redirects=True)


def test_requirements_never_assign_blotter_to_trainee():
    for scenario_id in ('S001', 'S002', 'S003', 'S004', 'S005', 'S006'):
        requirements = requirements_for_scenario(scenario_id)
        assert requirements['trainee_blotter_required'] is False
        assert all('blotter' not in item.lower() for item in requirements['officer_documents'])
        assert all('desk journal' not in item.lower() for item in requirements['officer_documents'])


def test_trainee_form_picker_is_full_library_not_scenario_answer_key():
    choices = trainee_requirement_choices('S004')
    assert any('voluntary statement' in item.lower() for item in choices)
    assert any('evidence custody' in item.lower() for item in choices)
    assert any('sf 91' in item.lower() for item in choices)
    assert all('blotter' not in item.lower() for item in choices)


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


def test_completed_call_can_submit_self_assess_unlock_debrief_and_preserve_revision_history():
    client = _client()
    _complete_s004(client)

    response = _submit_package(client)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'self-assessment' in html.lower()
    assert 'Open After-Action Debrief' not in html

    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert package['status'] == 'SELF_ASSESSMENT_REQUIRED'
        assert len(package['submissions']) == 1
        assert package['submissions'][0]['revision'] == 0
        assert package['submissions'][0]['report_analysis']['mode'] == 'deterministic'

    response = _self_assess(client)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'ready for fto review' in html.lower()
    assert 'Open After-Action Debrief' in html

    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert package['status'] == 'READY_FOR_FTO_REVIEW'
        assert package['self_assessment']['what_went_well']
        assert package['self_assessment']['decision_basis']

    client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': 'revise',
        'cid_decision': 'screen',
        'notification_notes': 'Updated synthetic training documentation.',
        'narrative': 'Revision one preserves the original and corrects the synthetic narrative.',
    }, follow_redirects=True)

    with client.session_transaction() as s:
        package = s['sentinel_scenario_lab_v2']['training_package']
        assert len(package['submissions']) == 2
        assert package['submissions'][0]['revision'] == 0
        assert package['submissions'][1]['revision'] == 1


def test_hidden_report_consistency_cues_show_only_in_evaluator_view():
    client = _client()
    _complete_s004(client)
    _submit_package(client, narrative='Short synthetic narrative.')

    trainee_response = client.get('/sentinel/fto-center/scenario-paperwork/')
    trainee_html = trainee_response.get_data(as_text=True)
    assert 'Narrative is very short' not in trainee_html

    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    evaluator_response = client.get(f'/sentinel/fto-center/scenario-paperwork/run/{run_id}')
    evaluator_html = evaluator_response.get_data(as_text=True)
    assert evaluator_response.status_code == 200
    assert 'Possible Narrative Issues for Human Verification' in evaluator_html
    assert 'Narrative is very short' in evaluator_html
    assert 'FTO disposition locked' in evaluator_html


def test_fto_disposition_is_locked_until_self_assessment_then_review_syncs_and_can_be_acknowledged():
    client = _client()
    _complete_s004(client)
    _submit_package(client)

    with client.session_transaction() as s:
        run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    locked = client.post(f'/sentinel/fto-center/scenario-paperwork/run/{run_id}', data={
        '_csrf_token': 'test-token',
        'fto_action': 'correction',
        'fto_comments': 'Review remains locked until the trainee reflection is complete.',
        'remediation_area': '',
        'remediation_plan': '',
    }, follow_redirects=True)
    assert locked.status_code == 200
    assert 'self-assessment is still pending' in locked.get_data(as_text=True).lower()

    _self_assess(client)

    response = client.post(f'/sentinel/fto-center/scenario-paperwork/run/{run_id}', data={
        '_csrf_token': 'test-token',
        'fto_action': 'correction',
        'fto_comments': 'Revise the chronology and clarify the documentation.',
        'remediation_area': '',
        'remediation_plan': '',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'returned for correction' in response.get_data(as_text=True).lower()

    response = client.get('/sentinel/fto-center/scenario-paperwork/')
    html = response.get_data(as_text=True)
    assert 'Correction Required' in html
    assert 'Revise the chronology' in html
    assert 'Acknowledge FTO Feedback' in html

    response = client.post('/sentinel/fto-center/scenario-paperwork/', data={
        '_csrf_token': 'test-token',
        'action': 'acknowledge',
        'acknowledge_review': 'yes',
        'trainee_comments': 'I reviewed the feedback and understand what must be corrected.',
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Trainee Acknowledged Review' in html

    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        package = state['training_package']
        assert package['status'] == 'CORRECTION_REQUIRED'
        assert len(package['submissions']) == 1
        assert len(package['review_history']) == 1
        assert package['self_assessment']['notifications_considered']
        assert package['trainee_acknowledgement']['reviewed_revision'] == 0
        assert 'understand what must be corrected' in package['trainee_acknowledgement']['trainee_comments']
        assert any(item['event_type'] == 'trainee_review_acknowledgement' for item in state['world']['timeline'])
