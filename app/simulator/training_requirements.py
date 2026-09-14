import json
from copy import deepcopy
from pathlib import Path

from ..models import Form
from ..services.call_type_rules import load_call_type_rules


_BLOTTER_TERMS = ('blotter', 'desk journal', 'desk-journal')

# Safety fallback for tests/offline development when there is no Flask/DB context.
# In the running portal the catalog is always pulled from Form.query so newly
# activated forms automatically appear in the FTO simulator.
_AUDITED_FORM_FALLBACK = (
    '5580 9 Command search authorization',
    '5580 16 PERMISSIVE AUTHORIZATION FOR SEARCH AND SEIZURE',
    'DD Form 2708Receipt for Inmate or Detained Person',
    'ENCLOSURE CHECKLIST FILLABLE',
    'Field test results',
    'MCPD Stat Sheet Revision 20240711',
    'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
    'NAVMC 11130 Statement of Force Use of Detention',
    'OPNAV 5580 3 Military Suspects Rights',
    'OPNAV 5580 4 Civilian Suspects Rights',
    'OPNAV 5580 2 Voluntary Statement',
    'OPNAV 5580 2 Voluntary Statement Traffic',
    'Affidavit for Seach and Seizure',
    'OPNAV 5580 21Field Interview Card',
    'OPNAV 5580 8 TELEPHONIC THREAT COMPLAINT',
    'OPNAV 5580 9 Command search authorization',
    'OPNAV 5580 10 Affidavit for Seach and Seizure',
    'OPNAV 5580 11 COMPLAINT OF STOLEN MOTOR VEHICLE',
    'OPNAV 5580 12 DON VEHICLE REPORT',
    'OPNAV 5580 16 PERMISSIVE AUTHORIZATION FOR SEARCH AND SEIZURE',
    'OPNAV 5580 20 Field test results',
    'OPNAV 5580 22Evidence Custody Document',
    'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
    'DD FORM 1920 ALCOHOL INCIDENT REPORT',
    'TA FIELD SKETCH NEW',
    'UNSECURED BUILDING NOTICE',
    'USACIL DNA Database Collection Eform v2 RE',
    'DD Form 2341 Report of Animal Bite Potential Rabies Exposure',
    'DD Form 2504Abandoned Vehicle Notice',
    'DD Form 2505Abandoned Vehicle Removal Authorization',
    'DD Form 2506Vehicle Impoundment Report',
    'DD Form 2507Notice of Vehicle Impoundment',
    'DD Form 2701 VWAP',
)


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


def is_declarant_completed_form(name):
    """True when the named form is completed by the declarant, not authored by the officer.

    These forms remain visible in the full trainee form library because recognizing
    that a written statement is needed is itself part of the exercise. If selected,
    the simulator must use the statement actually obtained from the simulated person;
    it must never ask the trainee to type the other person's statement.
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


def _third_party_statement_form(name):
    """Backward-compatible alias used by older code/tests."""
    return is_declarant_completed_form(name)


def load_scenario_requirement_overrides():
    path = _scenario_requirements_path()
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        raw = {}
    return raw if isinstance(raw, dict) else {}


def requirements_for_scenario(scenario_id):
    """Return the hidden post-call answer key used by the FTO review.

    The trainee does NOT receive this filtered list. The trainee sees the complete
    active MCPD form library and must decide which documents are appropriate. This
    requirements object remains the scenario/call-type comparison source for the FTO.
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
        if is_declarant_completed_form(name):
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
            if _trainee_document(name) and not is_declarant_completed_form(name)
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


def _active_library_titles():
    """Return every active form title in the real portal form library.

    Database access is deliberately best-effort so pure unit tests can call the
    helper without requiring an application context. Runtime requests use the DB.
    """
    titles = []
    try:
        rows = Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).all()
        titles = [_text(row.title) for row in rows if _trainee_document(row.title)]
    except Exception:
        titles = []

    if not titles:
        titles = [_text(name) for name in _AUDITED_FORM_FALLBACK if _trainee_document(name)]

    result = []
    seen = set()
    for name in titles:
        key = name.lower()
        if name and key not in seen:
            result.append(name)
            seen.add(key)
    return result


def trainee_requirement_choices(scenario_id=None):
    """Return the full active MCPD form library for trainee selection.

    `scenario_id` is accepted for backward compatibility but intentionally does not
    filter the list. Selecting the correct paperwork is part of the FTO exercise.
    """
    return _active_library_titles()
