import json
import os
import re
from pathlib import Path


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _rules_path():
    override = os.environ.get('MCPD_CALL_TYPE_RULES_PATH')
    if override:
        return Path(override)
    return _repo_root() / 'app' / 'data' / 'call_type_rules.json'


def slugify_call_type(value):
    slug = re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')
    return slug or 'new-call-type'


def split_multivalue(value):
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r'[\r\n,]+', str(value or ''))
    items = []
    seen = set()
    for item in raw_items:
        cleaned = str(item or '').strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            items.append(cleaned)
            seen.add(key)
    return items


def _default_rules():
    return {
        'domestic-disturbance': {
            'slug': 'domestic-disturbance',
            'title': 'Domestic Disturbance',
            'shortLabel': 'Domestic',
            'description': 'Primary domestic response, scene control, initial statements, and follow-up paperwork prep.',
            'statutes': ['Assault / battery review', 'Protective-order review'],
            'recommendedForms': [
                'NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
                'OPNAV 5580 2 Voluntary Statement',
                'NAVMC 11130 Statement of Force Use of Detention',
                'OPNAV 5580 22Evidence Custody Document',
            ],
            'optionalForms': ['DD Form 2701 VWAP', 'ENCLOSURE CHECKLIST FILLABLE'],
            'checklistItems': [
                'Separate involved parties',
                'Document injuries and scene condition',
                'Confirm witness and victim statements',
                'Notify supervisor if escalation or arrest is involved',
            ],
            'active': True,
        },
        'traffic-accident': {
            'slug': 'traffic-accident',
            'title': 'Traffic Accident',
            'shortLabel': 'Traffic',
            'description': 'Collision response, roadway safety, vehicle data capture, and tow/impound preparation.',
            'statutes': ['Traffic enforcement review', 'Installation roadway policy'],
            'recommendedForms': [
                'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
                'OPNAV 5580 2 Voluntary Statement Traffic',
                'TA FIELD SKETCH NEW',
            ],
            'optionalForms': ['DD Form 2506Vehicle Impoundment Report', 'OPNAV 5580 12 DON VEHICLE REPORT'],
            'checklistItems': [
                'Stabilize traffic and scene hazards',
                'Capture driver and vehicle data',
                'Document injuries and medical response',
                'Identify tow or impound decision',
            ],
            'active': True,
        },
        'suspicious-person': {
            'slug': 'suspicious-person',
            'title': 'Suspicious Person',
            'shortLabel': 'Suspicious',
            'description': 'Field contact and articulable-facts workflow for suspicious behavior and security concerns.',
            'statutes': ['Detention authority review', 'Trespass / access review'],
            'recommendedForms': ['OPNAV 5580 21Field Interview Card', 'OPNAV 5580 2 Voluntary Statement'],
            'optionalForms': ['OPNAV 5580 22Evidence Custody Document'],
            'checklistItems': [
                'Record the reason for contact',
                'Capture identifiers and witness information',
                'Document disposition and release / detention outcome',
            ],
            'active': True,
        },
        'trespass-after-warning': {
            'slug': 'trespass-after-warning',
            'title': 'Trespass After Warning',
            'shortLabel': 'Trespass',
            'description': 'Return-after-warning workflow with authority review and citation/notice support.',
            'statutes': ['Trespass authority review', 'Installation access policy'],
            'recommendedForms': ['OPNAV 5580 2 Voluntary Statement', 'UNSECURED BUILDING NOTICE'],
            'optionalForms': ['OPNAV 5580 21Field Interview Card'],
            'checklistItems': [
                'Confirm prior warning details',
                'Record location restrictions',
                'Document witness confirmation',
                'Capture final enforcement action',
            ],
            'active': True,
        },
        'theft': {
            'slug': 'theft',
            'title': 'Theft',
            'shortLabel': 'Theft',
            'description': 'Property crime workflow focused on ownership, recovered items, and evidence trail.',
            'statutes': ['Property crime review', 'Evidence handling review'],
            'recommendedForms': ['OPNAV 5580 22Evidence Custody Document', 'OPNAV 5580 2 Voluntary Statement'],
            'optionalForms': ['OPNAV 5580 21Field Interview Card', 'DD Form 2701 VWAP'],
            'checklistItems': [
                'Verify owner and value information',
                'Document recovered property',
                'Preserve evidence chain',
                'Capture suspect opportunity and access',
            ],
            'active': True,
        },
    }


def normalize_call_type_rule(raw):
    data = dict(raw or {})
    title = str(data.get('title') or data.get('name') or '').strip()
    slug = slugify_call_type(data.get('slug') or title)
    title = title or slug.replace('-', ' ').title()
    return {
        'slug': slug,
        'title': title,
        'shortLabel': str(data.get('shortLabel') or data.get('short_label') or title).strip()[:40],
        'description': str(data.get('description') or '').strip(),
        'statutes': split_multivalue(data.get('statutes')),
        'recommendedForms': split_multivalue(data.get('recommendedForms') or data.get('recommended_forms')),
        'optionalForms': split_multivalue(data.get('optionalForms') or data.get('optional_forms')),
        'checklistItems': split_multivalue(data.get('checklistItems') or data.get('checklist_items')),
        'active': bool(data.get('active', True)),
    }


def load_call_type_rules(include_inactive=False):
    path = _rules_path()
    source = None
    if path.exists():
        try:
            source = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            source = None
    if not source:
        source = _default_rules()
    entries = source.values() if isinstance(source, dict) else source
    rules = {}
    for item in entries or []:
        rule = normalize_call_type_rule(item)
        if include_inactive or rule['active']:
            rules[rule['slug']] = rule
    return rules


def save_call_type_rules(rules):
    normalized = {}
    entries = rules.values() if isinstance(rules, dict) else rules
    for item in entries or []:
        rule = normalize_call_type_rule(item)
        normalized[rule['slug']] = rule
    path = _rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding='utf-8')
    return normalized
