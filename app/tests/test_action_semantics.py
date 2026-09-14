from app.simulator.action_interpreter import actions_to_semantic_text, deterministic_interpret


def _types(actions):
    return {row.get('action_type') for row in actions}


def test_arrest_action_does_not_invent_probable_cause_or_lawful_authority():
    actions = deterministic_interpret('I arrest the subject and place the subject into custody.')
    assert 'arrest' in _types(actions)
    semantic = actions_to_semantic_text(actions).lower()
    assert 'probable cause' not in semantic
    assert 'reasonable suspicion' not in semantic
    assert 'lawful' not in semantic
    assert 'authority' not in semantic


def test_explicit_probable_cause_statement_creates_separate_legal_assessment():
    actions = deterministic_interpret(
        'I arrest the subject because I have probable cause based on the facts I developed.'
    )
    assert 'arrest' in _types(actions)
    assert 'legal_assessment' in _types(actions)
    semantic = actions_to_semantic_text(actions).lower()
    assert 'probable cause' in semantic


def test_search_action_does_not_invent_consent_warrant_or_probable_cause():
    actions = deterministic_interpret('I search the subject.')
    assert 'search' in _types(actions)
    semantic = actions_to_semantic_text(actions).lower()
    assert 'consent' not in semantic
    assert 'warrant' not in semantic
    assert 'probable cause' not in semantic
    assert 'lawful' not in semantic


def test_force_action_does_not_invent_threat_necessity_or_proportionality():
    actions = deterministic_interpret('I use force and take the subject to the ground.')
    assert 'use_force' in _types(actions)
    semantic = actions_to_semantic_text(actions).lower()
    assert 'necessary' not in semantic
    assert 'reasonable' not in semantic
    assert 'proportionate' not in semantic
    assert 'threat' not in semantic


def test_negated_enforcement_still_does_not_create_action():
    actions = deterministic_interpret(
        'I will not arrest or search the subject because I do not have probable cause.'
    )
    assert 'arrest' not in _types(actions)
    assert 'search' not in _types(actions)
