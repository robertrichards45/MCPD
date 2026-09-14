from app.simulator.person_records import obtain_requested_statements, reveal_requested_identities
from app.simulator.training_requirements import requirements_for_scenario, trainee_requirement_choices
from app.simulator.world_state import ensure_world_state


def _state(scenario_id='S004'):
    state = {
        'scenario_id': scenario_id,
        'run_context': {'run_id': 'TEST-PERSON-RECORDS', 'seed': 4242, 'choices': {}},
    }
    world = ensure_world_state(state, scenario_id)
    world['truth'] = {'people': {'lp': {'private_facts': ['The declarant personally observed the relevant event.']}}}
    world['people'] = {
        'lp': {
            'id': 'lp',
            'name': 'Loss Prevention',
            'role': 'Witness',
            'status': 'present',
            'discovered': True,
            'memory': [
                {'speaker': 'officer', 'text': 'Tell me what you observed.', 'clock': 2},
                {'speaker': 'npc', 'text': 'I personally observed the relevant event.', 'clock': 2},
            ],
        }
    }
    return state


def test_identifying_information_is_revealed_only_when_developed():
    state = _state()
    person = state['world']['people']['lp']
    assert not person.get('identity_obtained')

    changed = reveal_requested_identities(
        state,
        [{'action_type': 'interview', 'target': 'lp'}],
        'I obtain the witness name, date of birth, address, and phone number.',
    )
    assert changed == ['lp']
    person = state['world']['people']['lp']
    assert person['identity_obtained'] is True
    assert person['identity']['full_name']
    assert person['identity']['dob']
    assert person['identity']['address']
    assert person['identity']['phone']
    assert person['identity']['synthetic'] is True


def test_written_statement_is_completed_by_declarant_and_read_only():
    state = _state()
    created = obtain_requested_statements(
        state,
        [],
        'I obtain a written statement from Loss Prevention.',
    )
    assert len(created) == 1
    statement = created[0]
    assert statement['completed_by'] == 'simulated_declarant'
    assert statement['officer_editable'] is False
    assert statement['declarant_name']
    assert statement['dob']
    assert statement['address']
    assert statement['phone']
    assert 'personally observed' in statement['statement_text'].lower()
    assert statement['signature'].startswith('TRAINING SIGNATURE')
    assert state['world']['people']['lp']['identity_obtained'] is True


def test_voluntary_statement_is_not_officer_editable_paperwork_choice():
    requirements = requirements_for_scenario('S004')
    officer_choices = trainee_requirement_choices('S004')
    assert all('voluntary statement' not in value.lower() for value in officer_choices)
    assert any('voluntary statement' in value.lower() for value in requirements['statement_documents'])
    assert requirements['statements_are_declarant_completed'] is True
