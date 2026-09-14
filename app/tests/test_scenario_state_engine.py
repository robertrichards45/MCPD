from app.routes.scenario_legal_context import legal_context_for
from app.routes.scenario_state_engine import (
    apply_core_decision,
    new_engine_state,
    pending_event,
)
from app.routes.scenario_variants import build_run_context


def _state(scenario_id):
    return {
        'scenario_id': scenario_id,
        'engine': new_engine_state(scenario_id),
    }


def test_seeded_case_generation_is_reproducible_but_new_seeds_change_runs():
    first = build_run_context('S006', seed=123456789)
    replay = build_run_context('S006', seed=123456789)
    second = build_run_context('S006', seed=987654321)
    assert first == replay
    assert first['run_id'] != second['run_id']
    assert first['choices'] != second['choices']


def test_traffic_stop_without_backup_can_create_later_live_event():
    state = _state('S005')
    text = 'I keep the driver hands visible, maintain a safe position and distance, stay calm and professional, obtain the license and registration, and run the records check through dispatch.'
    apply_core_decision(state, 'S005', 1, text, True)
    event = pending_event(state, 'S005')
    assert event is not None
    assert event['id'] == 'rapid_reach'


def test_requesting_backup_changes_traffic_stop_branch():
    state = _state('S005')
    text = 'I request backup through dispatch, keep the driver hands visible, maintain a safe position and distance, stay calm and professional, obtain the license and registration, and run the records check.'
    apply_core_decision(state, 'S005', 1, text, True)
    assert state['engine']['backup'] in {'enroute', 'arrived'}
    assert pending_event(state, 'S005') is None


def test_poor_communication_can_create_subject_escalation_branch():
    state = _state('S001')
    text = 'I yell back and tell the subject to shut up while moving closer to teach him a lesson.'
    apply_core_decision(state, 'S001', 1, text, False)
    event = pending_event(state, 'S001')
    assert event is not None
    assert event['id'] == 'subject_escalation'
    assert state['engine']['complaint_risk'] is True


def test_medical_call_can_change_when_medical_priority_is_missed():
    state = _state('S006')
    text = 'I start by interviewing coworkers and comparing their accounts before doing anything else.'
    apply_core_decision(state, 'S006', 0, text, True)
    event = pending_event(state, 'S006')
    assert event is not None
    assert event['id'] == 'patient_deterioration'


def test_ucmj_article_108_only_surfaces_for_relevant_service_member_property_run():
    run_context = {
        'choices': {'driver_status': 'active-duty service member'},
    }
    refs = legal_context_for('S003', run_context, 2, {'pending_event': None})
    citations = {item['citation'] for item in refs}
    assert '10 USC 908' in citations
    assert 'OCGA 16-7-23' in citations


def test_legal_research_is_not_given_at_dispatch_before_facts_develop():
    run_context = {'choices': {'subject_status': 'civilian visitor', 'access_history': 'invited earlier'}}
    assert legal_context_for('S001', run_context, 0, {'pending_event': None}) == []
    refs = legal_context_for('S001', run_context, 1, {'pending_event': None})
    assert any(item['citation'] == 'OCGA 16-7-21' for item in refs)
