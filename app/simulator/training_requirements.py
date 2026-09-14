import json
from copy import deepcopy
from pathlib import Path

from ..services.call_type_rules import load_call_type_rules


_BLOTTER_TERMS = ('blotter', 'desk journal', 'desk-journal')


def _scenario_requirements_path():
    return Path(__file__).resolve().parents[1] / 'data' / 'fto_scenario_requirements.json'


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _list(value):
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    return []


def _trainee_document(name):
    low = _text(name).lower()
    return bool(low) and not any(term in low for term in _BLOTTER_TERMS)


def _third_party_statement_form(name):
    """Identify forms completed by the declarant rather than by the officer.

    OPNAV 5580/2 voluntary statements and similarly named witness/declarant
    statement forms must never be presented as trainee-authored paperwork.
    Officer-authored force/detention statements are intentionally excluded from
    this classification.
    """
    low = _text(name).lower()
    if not low:
        return False
    if 'force use' in low or 'use of detention' in low:
        return False
    return (
        'voluntary statement' in low
        or 'witness statement' in low
        or 'declarant statement' in low
        or low.startswith('written statement')
    )


def load_scenario_requirement_overrides():
    path = _scenario_requirements_path()
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        raw = {}
    return raw if isinstance(raw, dict) else {}


def requirements_for_scenario(scenario_id):
    """Return the one post-call requirements view consumed by the simulator.

    Officer paperwork comes from the existing Call Type Paperwork Manager rules.
    Third-party written statements are tracked separately because the witness,
    complainant, victim, subject, or other declarant completes their own statement;
    the trainee officer obtains and documents it but does not author it.
    Blotter/journal entries are always excluded from trainee paperwork.
    """
    scenario_id = _text(scenario_id).upper()
    overrides = load_scenario_requirement_overrides().get(scenario_id) or {}
    call_type_slug = _text(overrides.get('callType'))
    call_type_rules = load_call_type_rules(include_inactive=True)
    call_type = call_type_rules.get(call_type_slug) or {}

    manager_forms = _list(call_type.get('recommendedForms'))
    scenario_documents = _list(overrides.get('officerDocuments'))
    officer_documents = []
    statement_documents = []
    seen_officer = set()
    seen_statement = set()

    for name in manager_forms + scenario_documents:
        if not _trainee_document(name):
            continue
        key = name.lower()
        if _third_party_statement_form(name):
            if key not in seen_statement:
                statement_documents.append(name)
                seen_statement.add(key)
            continue
        if key not in seen_officer:
            officer_documents.append(name)
            seen_officer.add(key)

    cid = dict(overrides.get('cid') or {})
    requirement = _text(cid.get('requirement')).lower() or 'unconfigured'
    if requirement not in {'none', 'screen', 'notify', 'conditional', 'unconfigured'}:
        requirement = 'unconfigured'

    return {
        'scenario_id': scenario_id,
        'call_type_slug': call_type_slug,
        'call_type_title': _text(call_type.get('title')) or call_type_slug.replace('-', ' ').title(),
        'officer_documents': officer_documents,
        'optional_documents': [
            name for name in _list(call_type.get('optionalForms'))
            if _trainee_document(name) and not _third_party_statement_form(name)
        ],
        'statement_documents': statement_documents,
        'written_statements': _list(overrides.get('writtenStatements')),
        'notifications': deepcopy(overrides.get('notifications') or []),
        'cid': {
            'requirement': requirement,
            'instruction': _text(cid.get('instruction')),
            'verified_for_training': bool(cid.get('verifiedForTraining', False)),
        },
        'source': {
            'paperwork': 'Call Type Paperwork Manager',
            'scenario_notifications': 'FTO scenario requirements',
        },
        'trainee_blotter_required': False,
        'statements_are_declarant_completed': True,
    }


def trainee_requirement_choices(scenario_id):
    """Return only documentation the trainee officer personally completes."""
    requirements = requirements_for_scenario(scenario_id)
    return list(requirements['officer_documents'])