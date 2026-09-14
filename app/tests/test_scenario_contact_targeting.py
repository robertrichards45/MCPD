from app.simulator.action_interpreter import deterministic_interpret, interpret_action


VISIBLE = [
    {'id': 'staff', 'name': 'Staff Member', 'role': 'Reporting Party'},
    {'id': 'subject', 'name': 'Subject', 'role': 'Subject'},
    {'id': 'employee2', 'name': 'Second Employee', 'role': 'Witness'},
]


def _person_action(rows):
    return next((row for row in rows if row.get('action_type') in {'speak', 'interview', 'move'} and row.get('target')), None)


def test_suspect_alias_targets_subject_not_reporting_party():
    rows = deterministic_interpret(
        'I make contact with the suspect and ask them what is going on.',
        visible_people=VISIBLE,
    )
    action = _person_action(rows)
    assert action is not None
    assert action['target'] == 'subject'


def test_complainant_alias_targets_reporting_party():
    rows = deterministic_interpret(
        'I ask the complainant to tell me what happened.',
        visible_people=VISIBLE,
    )
    action = _person_action(rows)
    assert action is not None
    assert action['target'] == 'staff'


def test_caller_alias_targets_reporting_party():
    rows = deterministic_interpret(
        'I speak with the caller first.',
        visible_people=VISIBLE,
    )
    action = _person_action(rows)
    assert action is not None
    assert action['target'] == 'staff'


def test_witness_alias_targets_witness():
    rows = deterministic_interpret(
        'I interview the witness about what they personally saw.',
        visible_people=VISIBLE,
    )
    action = _person_action(rows)
    assert action is not None
    assert action['target'] == 'employee2'


def test_offline_interpreter_preserves_explicit_subject_target():
    rows = interpret_action(
        'I ask the suspect what happened from his side.',
        visible_people=VISIBLE,
        use_ai=False,
    )
    person_rows = [row for row in rows if row.get('action_type') in {'speak', 'interview'}]
    assert person_rows
    assert all(row['target'] == 'subject' for row in person_rows)
