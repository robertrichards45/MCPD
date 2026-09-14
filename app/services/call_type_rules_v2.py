import json
import re

from . import call_type_rules as legacy


CONDITION_DEFINITIONS = [
    {'key': 'reporting_party', 'label': 'Reporting party involved', 'question': 'Is there a reporting party for this incident?'},
    {'key': 'written_statement', 'label': 'Written statement needed', 'question': 'Does current guidance call for a written statement?'},
    {'key': 'property_documentation', 'label': 'Property documentation', 'question': 'Does this incident include property that needs additional documentation?'},
    {'key': 'medical_documentation', 'label': 'Medical documentation', 'question': 'Does a medical response change the paperwork packet?'},
    {'key': 'external_referral', 'label': 'External referral / screening', 'question': 'Does current guidance call for an external referral or screening step?'},
    {'key': 'vehicle_documentation', 'label': 'Vehicle documentation', 'question': 'Does vehicle handling require additional paperwork?'},
    {'key': 'additional_documentation', 'label': 'Additional documentation', 'question': 'Do the facts trigger any additional documentation?'},
]
CONDITION_MAP = {item['key']: item for item in CONDITION_DEFINITIONS}


def _dedupe(items):
    output = []
    seen = set()
    for item in items or []:
        text = str(item or '').strip()
        key = text.lower()
        if text and key not in seen:
            output.append(text)
            seen.add(key)
    return output


def split_multivalue(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        chunks = []
        for item in value:
            chunks.extend(split_multivalue(item))
        return _dedupe(chunks)

    chunks = []
    for line in str(value or '').replace('\r', '\n').split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('@'):
            chunks.append(line)
        else:
            chunks.extend(part.strip() for part in line.split(',') if part.strip())
    return _dedupe(chunks)


def _condition_rule(raw):
    data = dict(raw or {}) if isinstance(raw, dict) else {}
    key = re.sub(r'[^a-z0-9_]+', '_', str(data.get('key') or data.get('trigger') or '').strip().lower()).strip('_')
    forms = split_multivalue(data.get('forms') or data.get('form_names'))
    if not key or not forms:
        return None
    definition = CONDITION_MAP.get(key, {})
    return {
        'key': key,
        'label': str(data.get('label') or definition.get('label') or key.replace('_', ' ').title()).strip(),
        'question': str(data.get('question') or definition.get('question') or '').strip(),
        'forms': forms,
        'why': str(data.get('why') or data.get('reason') or '').strip(),
        'active': bool(data.get('active', True)),
    }


def _parse_tokens(entries):
    normal = []
    conditions = []
    not_normal = []
    explicit_none = False
    for raw in entries or []:
        text = str(raw or '').strip()
        lower = text.lower()
        if lower == '@conditions:none':
            explicit_none = True
            continue
        if lower.startswith('@when:'):
            parts = text[6:].split('|', 2)
            if len(parts) >= 2:
                item = _condition_rule({
                    'key': parts[0].strip(),
                    'forms': [parts[1].strip()],
                    'why': parts[2].strip() if len(parts) > 2 else '',
                })
                if item:
                    conditions.append(item)
            continue
        if lower.startswith('@notnormally:'):
            parts = text[len('@notnormally:'):].split('|', 1)
            form_name = parts[0].strip()
            if form_name:
                not_normal.append({'form': form_name, 'why': parts[1].strip() if len(parts) > 1 else ''})
            continue
        normal.append(text)
    return normal, conditions, not_normal, explicit_none


def _merge_conditions(rows):
    merged = {}
    order = []
    for raw in rows or []:
        item = _condition_rule(raw)
        if not item:
            continue
        key = item['key']
        if key not in merged:
            merged[key] = item
            order.append(key)
        else:
            merged[key]['forms'] = _dedupe(merged[key]['forms'] + item['forms'])
            if item.get('why'):
                merged[key]['why'] = item['why']
    return [merged[key] for key in order]


def _normalize_not_normal(rows):
    output = []
    seen = set()
    if isinstance(rows, dict):
        rows = [{'form': name, 'why': why} for name, why in rows.items()]
    for raw in rows or []:
        if isinstance(raw, dict):
            form_name = str(raw.get('form') or raw.get('name') or '').strip()
            why = str(raw.get('why') or raw.get('reason') or '').strip()
        else:
            form_name = str(raw or '').strip()
            why = ''
        key = form_name.lower()
        if form_name and key not in seen:
            output.append({'form': form_name, 'why': why})
            seen.add(key)
    return output


def normalize_call_type_rule(raw):
    data = dict(raw or {})
    base = legacy.normalize_call_type_rule(data)
    optional_raw = split_multivalue(data.get('optionalForms') or data.get('optional_forms') or base.get('optionalForms'))
    optional_forms, token_conditions, token_not_normal, explicit_none = _parse_tokens(optional_raw)

    structured = list(data.get('conditionalRules') or data.get('conditional_rules') or [])
    if not explicit_none:
        structured.extend(token_conditions)

    result = dict(base)
    result['recommendedForms'] = split_multivalue(data.get('recommendedForms') or data.get('recommended_forms') or base.get('recommendedForms'))
    result['optionalForms'] = optional_forms
    result['conditionalRules'] = _merge_conditions(structured)
    result['notNormallyRequiredForms'] = _normalize_not_normal(
        list(data.get('notNormallyRequiredForms') or data.get('not_normally_required_forms') or []) + token_not_normal
    )
    return result


def load_call_type_rules(include_inactive=False):
    rules = legacy.load_call_type_rules(include_inactive=True)
    output = {}
    for slug, raw in rules.items():
        rule = normalize_call_type_rule(raw)
        if include_inactive or rule.get('active', True):
            output[slug] = rule
    return output


def save_call_type_rules(rules):
    normalized = {}
    entries = rules.values() if isinstance(rules, dict) else rules
    for item in entries or []:
        rule = normalize_call_type_rule(item)
        normalized[rule['slug']] = rule
    path = legacy._rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding='utf-8')
    return normalized


def evaluate_call_type_rule(rule, circumstances=None):
    normalized = normalize_call_type_rule(rule)
    circumstances = circumstances or {}
    required = list(normalized.get('recommendedForms') or [])
    seen = {name.lower() for name in required}
    triggered = []
    remaining = []

    for condition in normalized.get('conditionalRules') or []:
        if not condition.get('active', True):
            continue
        matched = bool(circumstances.get(condition.get('key')))
        (triggered if matched else remaining).append(dict(condition))
        if matched:
            for form_name in condition.get('forms') or []:
                key = form_name.lower()
                if key not in seen:
                    required.append(form_name)
                    seen.add(key)

    return {
        'slug': normalized.get('slug'),
        'title': normalized.get('title'),
        'requiredForms': required,
        'triggeredConditions': triggered,
        'remainingConditions': remaining,
        'notNormallyRequiredForms': list(normalized.get('notNormallyRequiredForms') or []),
        'statutes': list(normalized.get('statutes') or []),
        'checklistItems': list(normalized.get('checklistItems') or []),
    }
