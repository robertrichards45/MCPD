from app.simulator.npc_engine import respond as npc_respond
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


def test_npc_identity_response_matches_exact_record_carried_to_paperwork():
    state = _state()
    reveal_requested_identities(
        state,
        [{'action_type': 'interview', 'target': 'lp'}],
        'I ask the witness for their name, date of birth, address, and phone number.',
    )
    identity = state['world']['people']['lp']['identity']
    answer, mode = npc_respond(
        state,
        {'id': 'lp', 'name': 'Loss Prevention', 'role': 'Witness'},
        'What is your name, date of birth, address, and phone number?',
        allowed_facts=[],
        visible_facts=[],
        fallback='Fallback should not be used for an obtained identity.',
        run_context=state['run_context'],
        officer_actions=[{'action_type': 'interview', 'target': 'lp'}],
    )
    assert mode == 'structured_identity'
    assert identity['full_name'] in answer
    assert identity['dob'] in answer
    assert identity['address'] in answer
    assert identity['phone'] in answer


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
    assert statement['form_read_only'] is True
    assert statement['declarant_name']
    assert statement['dob']
    assert statement['address']
    assert statement['phone']
    assert 'personally observed' in statement['statement_text'].lower()
    assert statement['signature'].startswith('TRAINING SIGNATURE')
    assert state['world']['people']['lp']['identity_obtained'] is True

    assert statement['form_document_name'] == 'OPNAV 5580 2 Voluntary Statement'
    values = statement['form_values']
    assert values['VicName'] == statement['declarant_name']
    assert values['Statement'] == statement['statement_text']
    assert values['Date'] == statement['statement_date']
    assert values['RespTime'] == statement['statement_time']
    assert values['Location'] == statement['statement_location']
    assert values['Initials']
    assert values['Signature'].startswith('TRAINING SIGNATURE')
    assert values['WitnessSign'] == ''
    assert values['OfficerSign'] == ''

    officer_only_fields = [field for field in statement['form_fields'] if field.get('officer_only')]
    assert officer_only_fields
    assert all(field['value'] == '' for field in officer_only_fields)
    assert all(field['locked'] is True for field in statement['form_fields'])


def test_voluntary_statement_is_not_officer_editable_paperwork_choice():
    requirements = requirements_for_scenario('S004')
    officer_choices = trainee_requirement_choices('S004')
    assert all('voluntary statement' not in value.lower() for value in officer_choices)
    assert any('voluntary statement' in value.lower() for value in requirements['statement_documents'])
    assert requirements['statements_are_declarant_completed'] is True
