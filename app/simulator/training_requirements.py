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


def load_scenario_requirement_overrides():
    path = _scenario_requirements_path()
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        raw = {}
    return raw if isinstance(raw, dict) else {}


def requirements_for_scenario(scenario_id):
    """Return the one post-call requirements view consumed by the simulator.

    Paperwork comes from the existing Call Type Paperwork Manager rules. Scenario-
    specific training requirements supply notification/CID decisions that are not
    currently represented by that older rules schema. Blotter/journal entries are
    always excluded from trainee paperwork by product requirement.
    """
    scenario_id = _text(scenario_id).upper()
    overrides = load_scenario_requirement_overrides().get(scenario_id) or {}
    call_type_slug = _text(overrides.get('callType'))
    call_type_rules = load_call_type_rules(include_inactive=True)
    call_type = call_type_rules.get(call_type_slug) or {}

    manager_forms = _list(call_type.get('recommendedForms'))
    scenario_documents = _list(overrides.get('officerDocuments'))
    officer_documents = []
    seen = set()
    for name in manager_forms + scenario_documents:
        key = name.lower()
        if not _trainee_document(name) or key in seen:
            continue
        officer_documents.append(name)
        seen.add(key)

    cid = dict(overrides.get('cid') or {})
    requirement = _text(cid.get('requirement')).lower() or 'unconfigured'
    if requirement not in {'none', 'screen', 'notify', 'conditional', 'unconfigured'}:
        requirement = 'unconfigured'

    return {
        'scenario_id': scenario_id,
        'call_type_slug': call_type_slug,
        'call_type_title': _text(call_type.get('title')) or call_type_slug.replace('-', ' ').title(),
        'officer_documents': officer_documents,
        'optional_documents': [name for name in _list(call_type.get('optionalForms')) if _trainee_document(name)],
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
    }


def trainee_requirement_choices(scenario_id):
    """Return choices safe to present only after the live call is over."""
    requirements = requirements_for_scenario(scenario_id)
    choices = list(requirements['officer_documents'])
    for item in requirements['written_statements']:
        if item not in choices:
            choices.append(item)
    return choices
