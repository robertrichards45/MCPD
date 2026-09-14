from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-live-ci').first()
        if user is None:
            user = User(username='scenario-live-ci', name='Scenario Live CI Controller', role=ROLE_WEBSITE_CONTROLLER, active=True, pending_approval=False)
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return app, client, user_id


def _seed_with_choice(scenario_id, key, phrase):
    from app.routes.scenario_variants import _draw_choices
    for seed in range(100000000, 100020000):
        if phrase.lower() in str(_draw_choices(scenario_id, seed).get(key, '')).lower():
            return seed
    raise AssertionError(f'No deterministic seed found for {scenario_id} {key}={phrase}')


def _set_seed(client, scenario_id, seed):
    with client.session_transaction() as s:
        s['sentinel_scenario_seed_override_v1'] = {'scenario_id': scenario_id, 'seed': seed}


def test_face_to_face_question_uses_npc_memory_without_exposing_future_actor():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'officer_action',
        'command_text': "I talk to the Staff Member. Ma'am, what happened?"
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Staff Member' in html
    assert 'Subject — Subject' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['actor_interactions'] >= 1
        assert state['world']['people']['staff']['memory']
        assert 'subject' not in state['world']['people'] or not state['world']['people']['subject'].get('discovered')


def test_radio_and_records_are_separate_from_face_to_face_contact():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S005')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S005', 'action': 'radio',
        'radio_text': '214, show me on scene and run Georgia OLN 123456789.'
    }, follow_redirects=True)
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        radio = state['world']['radio_log']
        assert any(item['speaker'] == 'Trainee' for item in radio)
        assert state['world']['records']
        assert any(item.get('metadata', {}).get('type') == 'records' for item in state['world']['pending_radio'])

    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S005', 'action': 'officer_action',
        'command_text': 'I look through the windshield and check the driver hands.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Dispatch' in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert any(item.get('metadata', {}).get('type') == 'records' for item in state['world']['radio_log'])


def test_restart_same_scenario_family_changes_fact_pattern():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')
    with client.session_transaction() as s:
        first = dict(s['sentinel_scenario_lab_v2']['run_context']['choices'])
        first_run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S006', 'action': 'reset'
    }, follow_redirects=True)
    assert response.status_code == 200

    with client.session_transaction() as s:
        second = dict(s['sentinel_scenario_lab_v2']['run_context']['choices'])
        second_run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']

    assert second_run_id != first_run_id
    assert second != first


def test_catastrophic_deadly_force_decision_terminates_exercise_and_requires_training_package_before_debrief():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'officer_action',
        'command_text': 'I shoot the person immediately even though no deadly threat has been presented.'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Simulation Ended' in html
    assert 'deadly-force decision unsupported' in html
    assert 'Complete Training Package' in html
    assert 'Complete the post-call documentation and self-assessment before debrief.' in html
    assert 'After-Action Review' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['terminated'] is True
        assert state['complete'] is True
        assert state['fto_alert'] is True
        assert any(item['event_type'] == 'terminal_outcome' for item in state['world']['timeline'])


def test_negated_deadly_force_statement_does_not_terminate_run():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token',
        'scenario_id': 'S001',
        'action': 'officer_action',
        'command_text': 'I would not shoot anyone because I have not observed a deadly threat.'
    }, follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['terminated'] is False
        assert not any(row.get('action_type') == 'deadly_force' for row in state['world']['last_actions'])


def test_terminal_outcome_moves_to_next_scenario_with_hidden_new_run_id():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'officer_action',
        'command_text': 'I shoot the person even though there is no deadly threat.'
    }, follow_redirects=True)
    response = client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S001', 'action': 'next'
    }, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'Suspicious Vehicle at Main Gate' in html
    assert 'Run S002-' not in html
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['scenario_id'] == 'S002'
        assert state['terminated'] is False
        assert state['run_context']['run_id'].startswith('S002-')


def test_handbook_scenario_families_are_registered_in_virtual_patrol():
    _app, client, _uid = _client()
    from app.routes.scenario_lab import SCENARIOS
    from app.routes.scenario_variants import VARIANTS
    expected = {'S007', 'S008', 'S009', 'S010', 'S011', 'S012', 'S013', 'S014'}
    assert expected.issubset(SCENARIOS)
    assert expected.issubset(VARIANTS)
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S007')
    assert response.status_code == 200
    assert 'Traffic Accident' in response.get_data(as_text=True)
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['scenario_id'] == 'S007'
        assert state['run_context']['choices']['crash_type']
        assert state['world']['truth']['scenario_id'] == 'S007'
        assert 'crash_scene' in state['world']['evidence']


def test_handbook_same_family_restart_changes_new_crash_facts():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S007')
    with client.session_transaction() as s:
        first = dict(s['sentinel_scenario_lab_v2']['run_context']['choices'])
        first_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S007', 'action': 'reset'
    }, follow_redirects=True)
    with client.session_transaction() as s:
        second = dict(s['sentinel_scenario_lab_v2']['run_context']['choices'])
        second_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']
    assert second_id != first_id
    assert second != first


def test_non_extradition_warrant_run_creates_release_branch_instead_of_assuming_transport():
    _app, client, _uid = _client()
    seed = _seed_with_choice('S008', 'extradition', 'declines extradition')
    _set_seed(client, 'S008', seed)
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S008')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S008', 'action': 'officer_action',
        'command_text': 'I verify identity using DOB and license, maintain a lawful temporary detention for safety, and ask Dispatch to confirm the warrant with the entering agency before any transport.'
    }, follow_redirects=True)
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S008', 'action': 'officer_action',
        'command_text': 'I obtain the warrant number and offense, exact extradition limits, confirming agency official and time, and any caution or safety information from the entering agency.'
    }, follow_redirects=True)
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert 'declines extradition' in state['run_context']['choices']['extradition']
        assert state['engine']['pending_event'] == 'warrant_extradition_conflict'


def test_domestic_run_penalizes_failure_to_separate_without_deciding_guilt():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S009')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S009', 'action': 'officer_action',
        'command_text': 'I assess immediate weapon and threat safety and request backup, check both parties for injury and EMS needs, and document their physical condition, emotional condition, and the scene as observed.'
    }, follow_redirects=True)
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['engine']['pending_event'] == 'domestic_interference'
        assert 'guilt' not in str(state.get('last_feedback', {})).lower()


def test_withdrawn_consent_run_creates_search_authority_branch():
    _app, client, _uid = _client()
    seed = _seed_with_choice('S013', 'consent', 'withdrawn')
    _set_seed(client, 'S013', seed)
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S013')
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S013', 'action': 'officer_action',
        'command_text': 'I distinguish whether the odor was personally observed or only reported, identify the actual person or vehicle source, corroborate with additional observations and questions, and do not search without consent, a warrant, probable cause, or another lawful authority.'
    }, follow_redirects=True)
    client.post('/sentinel/fto-center/scenario-lab/', data={
        '_csrf_token': 'test-token', 'scenario_id': 'S013', 'action': 'officer_action',
        'command_text': 'I verify the current lawful authority. If using consent I ensure it is voluntary and the person understands the right to refuse, define the exact scope and containers covered, and stop if consent is refused or withdrawn.'
    }, follow_redirects=True)
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert 'withdrawn' in state['run_context']['choices']['consent']
        assert state['engine']['pending_event'] == 'consent_withdrawn'


def test_handbook_scenarios_feed_post_call_requirements_without_turning_witness_statements_into_officer_forms():
    _app, _client_obj, _uid = _client()
    from app.simulator.training_requirements import requirements_for_scenario
    domestic = requirements_for_scenario('S009')
    found = requirements_for_scenario('S012')
    uas = requirements_for_scenario('S014')
    assert 'DD Form 2701 VWAP' in domestic['officer_documents']
    assert any('Victim / witness statements' in row for row in domestic['written_statements'])
    assert 'OPNAV 5580 22Evidence Custody Document' in found['officer_documents']
    assert any('Finder / witness' in row for row in found['written_statements'])
    assert 'UAS / SITREP Command Report' in uas['officer_documents']


def test_dui_legal_context_requires_current_authority_instead_of_hard_coding_sample_thresholds():
    _app, client, _uid = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S010')
    from app.routes.scenario_lab_live import legal_context_for
    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        rows = legal_context_for('S010', state['run_context'], 1, state.get('engine'))
    joined = ' '.join(str(row) for row in rows)
    assert '40-5-67.1' in joined
    assert 'current approved warning' in joined.lower()
    assert '0.08' not in joined
    assert '0.02' not in joined
    assert '0.04' not in joined
