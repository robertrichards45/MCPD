import json
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import quote

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AuditLog, Form, ROLE_DESK_SGT, ROLE_WATCH_COMMANDER, ROLE_WEBSITE_CONTROLLER

bp = Blueprint('reference', __name__)

HANDBOOK_JSON_PATH = os.path.join('data', 'handbook', 'officer_handbook.json')
HANDBOOK_PDF_PATH = os.path.join('data', 'handbook', 'officer_handbook_source.pdf')
HANDBOOK_ADDITIONS_JSON_PATH = os.path.join('data', 'handbook', 'officer_handbook_additions.json')
HANDBOOK_GENERATED_BACKUP_PATH = os.path.join('data', 'handbook', 'officer_handbook_generated_backup.json')
PAPERWORK_GUIDE_CUSTOM_JSON_PATH = os.path.join('data', 'handbook', 'incident_paperwork_guide_custom.json')

PAPERWORK_FORM_SEARCH_HINTS = [
    ('witness statement', 'Statement'),
    ('guardian statement', 'Statement'),
    ('use of force', 'Force'),
    ('evidence', 'Evidence'),
    ('property inventory', 'Property'),
    ('property form', 'Property'),
    ('property', 'Property'),
    ('vehicle impound', 'Impound'),
    ('field interview', 'Field Interview'),
    ('accident report', 'Accident'),
    ('incident/accident report', 'Accident'),
    ('incident report', 'Incident'),
    ('citation', 'Notice'),
    ('notice', 'Notice'),
]

PRIORITY_QUICK_INCIDENTS = (
    'Domestic Disturbance',
    'Traffic Accident',
    'Assault',
    'Shoplifting',
    'Drug Possession',
    'Suspicious Person',
    'Vehicle Impound',
    'Trespass After Warning',
)

HANDBOOK_FORM_ALIASES = {
    'incident report': ('incident report', 'incident/accident report', 'accident report'),
    'witness statement': ('witness statement', 'witness statements', 'witness statement(s)', 'guardian statement', 'guardian statements'),
    'evidence property forms': ('evidence form', 'property form', 'property/evidence form', 'property inventory', 'evidence / property forms'),
    'vehicle impound form': ('vehicle impound form', 'vehicle impound'),
    'use of force report': ('use of force', 'use of force report'),
    'supplemental report': ('supplemental', 'supplemental report'),
    'field interview documentation': ('field interview', 'field interview documentation'),
    'juvenile specific processing documents': ('juvenile-specific processing documents', 'juvenile processing documents', 'juvenile processing'),
    'citation notice documentation': ('citation/notice documentation', 'citation documentation', 'notice documentation', 'citation', 'notice'),
}


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _handbook_json_file():
    return os.path.join(current_app.root_path, HANDBOOK_JSON_PATH)


def _handbook_additions_file():
    return os.path.join(current_app.root_path, HANDBOOK_ADDITIONS_JSON_PATH)


def _handbook_generated_backup_file():
    return os.path.join(current_app.root_path, HANDBOOK_GENERATED_BACKUP_PATH)


def _paperwork_guide_custom_file():
    configured = (os.environ.get('MCPD_PAPERWORK_GUIDE_CUSTOM_PATH') or '').strip()
    if configured:
        return configured
    return os.path.join(current_app.root_path, PAPERWORK_GUIDE_CUSTOM_JSON_PATH)


def _handbook_pdf_file():
    configured = (os.environ.get('OFFICER_HANDBOOK_PDF') or '').strip()
    if configured and os.path.exists(configured):
        return configured
    return os.path.join(current_app.root_path, HANDBOOK_PDF_PATH)


def _default_additions_payload():
    return {
        'title': 'Officer Handbook Additions',
        'version': '1.0',
        'sections': [],
    }


def _load_json_payload(path, fallback):
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
    except Exception:
        return fallback
    if not isinstance(payload, dict):
        return fallback
    payload.setdefault('title', fallback.get('title', 'Officer Handbook'))
    payload.setdefault('version', fallback.get('version', 'draft'))
    payload.setdefault('sections', [])
    if not isinstance(payload.get('sections'), list):
        payload['sections'] = []
    return payload


def _save_json_payload(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def _base_version_token(path):
    if not os.path.exists(path):
        return 'missing'
    ts = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc)
    return ts.strftime('%Y.%m.%d')


def _default_generated_payload():
    return {
        'title': 'MCPD Officer Handbook',
        'version': 'backup',
        'sections': [],
    }


def _default_paperwork_guide_payload():
    return {
        'title': 'Incident Paperwork Guide Custom Entries',
        'version': '1.0',
        'scenarios': [],
    }


def _bootstrap_handbook_storage():
    legacy_path = _handbook_json_file()
    backup_path = _handbook_generated_backup_file()
    additions_path = _handbook_additions_file()
    if os.path.exists(legacy_path) and not os.path.exists(backup_path):
        try:
            with open(legacy_path, 'r', encoding='utf-8') as src:
                legacy_payload = json.load(src)
            if isinstance(legacy_payload, dict):
                _save_json_payload(backup_path, legacy_payload)
        except Exception:
            pass
    if not os.path.exists(additions_path):
        _save_json_payload(additions_path, _default_additions_payload())
    custom_path = _paperwork_guide_custom_file()
    if not os.path.exists(custom_path):
        _save_json_payload(custom_path, _default_paperwork_guide_payload())


def _scenario_section_key(section):
    raw = str(section.get('id') or section.get('title') or '').strip().lower()
    return raw.replace('_', '-').replace(' ', '-')


def _scenario_search_blob(scenario):
    paperwork = ' '.join(
        str(item.get('label') or '').strip()
        for item in (scenario.get('required_paperwork') or [])
        if isinstance(item, dict) and str(item.get('label') or '').strip()
    )
    return ' '.join(
        [
            str(scenario.get('title') or ''),
            str(scenario.get('description') or ''),
            paperwork,
            str(scenario.get('officer_responsibilities') or ''),
            str(scenario.get('notes') or ''),
        ]
    ).lower()


def _slugify_text(value):
    lowered = str(value or '').strip().lower()
    slug = ''.join(ch if ch.isalnum() else '-' for ch in lowered)
    return '-'.join(part for part in slug.split('-') if part)


def _split_text_lines(value):
    return [line.strip() for line in str(value or '').splitlines() if line.strip()]


def _paperwork_items_from_value(value):
    if isinstance(value, str):
        source_items = _split_text_lines(value)
    elif isinstance(value, list):
        source_items = value
    else:
        source_items = []

    items = []
    seen = set()
    for item in source_items:
        if isinstance(item, dict):
            label = str(item.get('label') or item.get('name') or '').strip()
            search_term = str(item.get('search_term') or '').strip()
        else:
            label = str(item or '').strip()
            search_term = ''
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                'label': label,
                'search_term': search_term or _paperwork_search_term(label),
            }
        )
    return items


def _normalize_incident_scenario(raw, source='handbook'):
    title = str((raw or {}).get('title') or '').strip()
    if not title:
        return None
    slug = _slugify_text((raw or {}).get('slug') or title)
    return {
        'title': title,
        'description': str((raw or {}).get('description') or '').strip(),
        'required_paperwork': _paperwork_items_from_value((raw or {}).get('required_paperwork')),
        'officer_responsibilities': str((raw or {}).get('officer_responsibilities') or '').strip(),
        'notes': str((raw or {}).get('notes') or '').strip(),
        'slug': slug,
        'source': source,
        'active': (raw or {}).get('active', True) is not False,
        'updated_at': str((raw or {}).get('updated_at') or '').strip(),
    }


def _load_paperwork_guide_payload():
    _bootstrap_handbook_storage()
    path = _paperwork_guide_custom_file()
    fallback = _default_paperwork_guide_payload()
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
    except Exception:
        return fallback
    if not isinstance(payload, dict):
        return fallback
    payload.setdefault('title', fallback['title'])
    payload.setdefault('version', fallback['version'])
    payload.setdefault('scenarios', [])
    if not isinstance(payload.get('scenarios'), list):
        payload['scenarios'] = []
    return payload


def _save_paperwork_guide_payload(payload):
    payload.setdefault('title', 'Incident Paperwork Guide Custom Entries')
    payload.setdefault('version', '1.0')
    payload.setdefault('scenarios', [])
    _save_json_payload(_paperwork_guide_custom_file(), payload)


def _load_custom_incident_scenarios(include_inactive=False):
    payload = _load_paperwork_guide_payload()
    scenarios = []
    for raw in payload.get('scenarios') or []:
        normalized = _normalize_incident_scenario(raw, source='custom')
        if not normalized:
            continue
        if normalized.get('active') or include_inactive:
            scenarios.append(normalized)
    return scenarios


def _save_custom_incident_scenario(scenario):
    payload = _load_paperwork_guide_payload()
    normalized = _normalize_incident_scenario(scenario, source='custom')
    if not normalized:
        return None
    normalized['source'] = 'custom'
    normalized['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    kept = []
    replaced = False
    for existing in payload.get('scenarios') or []:
        existing_slug = _slugify_text(existing.get('slug') or existing.get('title'))
        if existing_slug == normalized['slug']:
            kept.append(normalized)
            replaced = True
        else:
            kept.append(existing)
    if not replaced:
        kept.append(normalized)
    payload['scenarios'] = kept
    _save_paperwork_guide_payload(payload)
    return normalized


def _hide_custom_incident_scenario(slug, title=''):
    cleaned_slug = _slugify_text(slug)
    if not cleaned_slug:
        return False
    payload = _load_paperwork_guide_payload()
    changed = False
    kept = []
    for existing in payload.get('scenarios') or []:
        existing_slug = _slugify_text(existing.get('slug') or existing.get('title'))
        if existing_slug == cleaned_slug:
            updated = dict(existing)
            updated.setdefault('title', title or existing.get('title') or cleaned_slug.replace('-', ' ').title())
            updated['slug'] = cleaned_slug
            updated['active'] = False
            updated['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            kept.append(updated)
            changed = True
        else:
            kept.append(existing)
    if not changed:
        kept.append(
            {
                'title': title or cleaned_slug.replace('-', ' ').title(),
                'slug': cleaned_slug,
                'description': '',
                'required_paperwork': [],
                'officer_responsibilities': '',
                'notes': '',
                'active': False,
                'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            }
        )
    payload['scenarios'] = kept
    _save_paperwork_guide_payload(payload)
    return True


def _normalize_lookup_text(value):
    text = str(value or '').strip().lower()
    text = text.replace('&', ' and ')
    text = text.replace('(s)', '')
    text = re.sub(r'\(if applicable\)', '', text)
    text = re.sub(r'\bif applicable\b', '', text)
    text = text.replace('/', ' ')
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return ' '.join(part for part in text.split() if part)


def _guidance_points(text, fallback, limit=4):
    raw = str(text or '').strip()
    if not raw:
        raw = str(fallback or '').strip()
    pieces = re.split(r'[.;]\s*|,\s+(?=[a-zA-Z])', raw)
    points = []
    seen = set()
    for piece in pieces:
        cleaned = str(piece or '').strip(' ,.-')
        if not cleaned:
            continue
        cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        points.append(cleaned)
        if len(points) >= limit:
            break
    return points


def _load_form_reference_index():
    _bootstrap_handbook_storage()
    sources = [
        _load_json_payload(_handbook_generated_backup_file(), _default_generated_payload()),
        _load_json_payload(_handbook_additions_file(), _default_additions_payload()),
    ]
    references = {}

    def ensure_entry(name):
        key = _normalize_lookup_text(name)
        entry = references.setdefault(
            key,
            {
                'name': str(name or '').strip(),
                'summary': '',
                'when_used': '',
                'field_focus': [],
                'common_mistakes': [],
                'aliases': {key},
            },
        )
        return key, entry

    for payload in sources:
        for section in payload.get('sections', []):
            for topic in section.get('topics') or []:
                title = str(topic.get('title') or '').strip()
                if not title:
                    continue
                key, entry = ensure_entry(title)
                if not entry['summary']:
                    entry['summary'] = str(topic.get('content') or '').strip()
                for alias in HANDBOOK_FORM_ALIASES.get(key, ()):
                    entry['aliases'].add(_normalize_lookup_text(alias))

            for guide in section.get('form_guides') or []:
                name = str(guide.get('form_name') or '').strip()
                if not name:
                    continue
                key, entry = ensure_entry(name)
                if not entry['summary']:
                    entry['summary'] = str(guide.get('purpose') or '').strip()
                if not entry['when_used']:
                    entry['when_used'] = str(guide.get('when_used') or '').strip()
                entry['field_focus'] = entry['field_focus'] or list(guide.get('field_instructions') or [])[:3]
                entry['common_mistakes'] = entry['common_mistakes'] or list(guide.get('common_mistakes') or [])[:2]
                for alias in HANDBOOK_FORM_ALIASES.get(key, ()):
                    entry['aliases'].add(_normalize_lookup_text(alias))

    return list(references.values())


def _form_reference_for_label(label, reference_index):
    normalized_label = _normalize_lookup_text(label)
    if not normalized_label:
        return None

    best = None
    best_score = -1
    label_tokens = set(normalized_label.split())
    for entry in reference_index:
        aliases = set(entry.get('aliases') or ())
        if normalized_label in aliases:
            return entry
        score = 0
        for alias in aliases:
            if not alias:
                continue
            if alias in normalized_label or normalized_label in alias:
                score = max(score, 18)
            alias_tokens = set(alias.split())
            overlap = label_tokens & alias_tokens
            if overlap:
                score = max(score, len(overlap) * 5)
        if score > best_score:
            best = entry
            best_score = score
    return best if best_score >= 5 else None


def _decorate_incident_scenario(scenario, reference_index):
    paperwork_items = []
    for item in scenario.get('required_paperwork') or []:
        reference = _form_reference_for_label(item.get('label'), reference_index)
        paperwork_items.append(
            {
                'label': item.get('label'),
                'search_term': item.get('search_term'),
                'handbook_summary': (reference or {}).get('summary', ''),
                'when_used': (reference or {}).get('when_used', ''),
                'field_focus': list((reference or {}).get('field_focus') or [])[:2],
                'common_mistakes': list((reference or {}).get('common_mistakes') or [])[:2],
                'handbook_query': item.get('label') or scenario.get('title'),
            }
        )

    response_points = _guidance_points(
        scenario.get('officer_responsibilities'),
        'Maintain scene safety, preserve evidence, document facts objectively, and coordinate notifications before end of shift.',
    )
    note_points = _guidance_points(
        scenario.get('notes'),
        'Confirm command direction, local policy, and any extra notifications tied to this call type.',
        limit=3,
    )

    decorated = dict(scenario)
    decorated['required_paperwork'] = paperwork_items
    decorated['response_points'] = response_points
    decorated['note_points'] = note_points
    decorated['paperwork_count'] = len(paperwork_items)
    decorated['handbook_matches'] = sum(1 for item in paperwork_items if item.get('handbook_summary'))
    return decorated


def _quick_incident_cards(scenarios, limit=8):
    by_title = {str(item.get('title') or '').strip().lower(): item for item in scenarios}
    quick = []
    for title in PRIORITY_QUICK_INCIDENTS:
        found = by_title.get(title.lower())
        if found and found not in quick:
            quick.append(found)
    for scenario in scenarios:
        if scenario not in quick:
            quick.append(scenario)
        if len(quick) >= limit:
            break
    return quick[:limit]


def _paperwork_search_term(label):
    text = str(label or '').strip()
    lowered = text.lower()
    for needle, search_term in PAPERWORK_FORM_SEARCH_HINTS:
        if needle in lowered:
            return search_term
    stop_words = {'if', 'applicable', 'needed', 'required', 'documentation', 'documents', 'specific', 'and', 'or', 'as'}
    cleaned = ' '.join(
        token for token in text.replace('(', ' ').replace(')', ' ').replace('/', ' ').split()
        if token.lower() not in stop_words
    )
    return cleaned or text


def _load_incident_scenarios():
    _bootstrap_handbook_storage()
    additions = _load_json_payload(_handbook_additions_file(), _default_additions_payload())
    backup = _load_json_payload(_handbook_generated_backup_file(), _default_generated_payload())

    base_scenarios = []
    seen = set()
    for payload in [additions, backup]:
        for section in payload.get('sections', []):
            for scenario in section.get('scenarios') or []:
                title = str(scenario.get('title') or '').strip()
                if not title:
                    continue
                key = _slugify_text(title)
                if key in seen:
                    continue
                normalized = _normalize_incident_scenario(scenario, source='handbook')
                if not normalized:
                    continue
                base_scenarios.append(normalized)
                seen.add(key)

    custom_by_slug = {
        scenario.get('slug'): scenario
        for scenario in _load_custom_incident_scenarios(include_inactive=True)
        if scenario.get('slug')
    }
    merged = []
    merged_slugs = set()
    for scenario in base_scenarios:
        slug = scenario.get('slug')
        override = custom_by_slug.get(slug)
        if override and not override.get('active'):
            merged_slugs.add(slug)
            continue
        if override:
            merged.append(override)
            merged_slugs.add(slug)
            continue
        merged.append(scenario)
        merged_slugs.add(slug)

    for scenario in custom_by_slug.values():
        slug = scenario.get('slug')
        if scenario.get('active') and slug not in merged_slugs:
            merged.append(scenario)
            merged_slugs.add(slug)
    return merged


def _apply_incident_fallback(payload):
    scenarios = _load_incident_scenarios()
    if not scenarios:
        return payload

    target_keys = {'scenario-paperwork-guide', 'scenario-guides'}
    sections = []
    replaced = False
    for section in payload.get('sections', []):
        key = _scenario_section_key(section)
        if key in target_keys:
            updated = dict(section)
            existing = updated.get('scenarios') or []
            if not existing:
                updated['scenarios'] = scenarios
            if not updated.get('summary'):
                updated['summary'] = 'Quick-reference paperwork expectations by common incident type.'
            sections.append(updated)
            replaced = True
            continue
        sections.append(section)

    if not replaced:
        insert_at = 1 if sections else 0
        sections.insert(
            insert_at,
            {
                'id': 'scenario-paperwork-guide',
                'title': 'Scenario-Based Paperwork Guide (Supplemental)',
                'summary': 'Quick-reference paperwork expectations by common incident type.',
                'scenarios': scenarios,
            },
        )

    hydrated = dict(payload)
    hydrated['sections'] = sections
    return hydrated


def _load_handbook():
    _bootstrap_handbook_storage()
    pdf_path = _handbook_pdf_file()
    additions = _apply_incident_fallback(
        _load_json_payload(_handbook_additions_file(), _default_additions_payload())
    )
    original_version = _base_version_token(pdf_path)
    improved_version = str(additions.get('version') or _base_version_token(_handbook_additions_file()))
    return {
        'title': 'MCPD Officer Handbook',
        'version': f'Original {original_version} | Improved {improved_version}',
        'original_version': original_version,
        'improved_version': improved_version,
        'sections': additions.get('sections') or [],
        'base_pdf_available': os.path.exists(pdf_path),
    }


def _save_handbook_additions(payload):
    path = _handbook_additions_file()
    _save_json_payload(path, payload)


def _can_edit_handbook():
    return current_user.has_any_role(ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER, ROLE_DESK_SGT)


def _safe_email(value):
    return (value or '').strip()


def _smtp_send_with_attachment(recipient, subject, body, file_path=None):
    host = (os.environ.get('SMTP_HOST') or '').strip()
    sender = (os.environ.get('SMTP_FROM') or '').strip()
    if not host or not sender:
        return False, 'SMTP not configured.'
    port = int((os.environ.get('SMTP_PORT') or '587').strip())
    username = (os.environ.get('SMTP_USERNAME') or '').strip()
    password = (os.environ.get('SMTP_PASSWORD') or '').strip()
    use_tls = (os.environ.get('SMTP_USE_TLS') or '1').strip().lower() in {'1', 'true', 'yes', 'on'}

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    msg.set_content(body)

    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as handle:
            data = handle.read()
        msg.add_attachment(data, maintype='application', subtype='pdf', filename=os.path.basename(file_path))

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)
    return True, 'sent'


def _match_text(blob, query):
    return query in (blob or '').lower()


def _filter_handbook(payload, search_term):
    term = (search_term or '').strip().lower()
    if not term:
        return payload
    sections = []
    for section in payload.get('sections', []):
        section_blob = ' '.join(
            [
                str(section.get('title') or ''),
                str(section.get('summary') or ''),
                json.dumps(section, ensure_ascii=True),
            ]
        ).lower()
        if _match_text(section_blob, term):
            sections.append(section)
            continue
    return {
        'title': payload.get('title'),
        'version': payload.get('version'),
        'original_version': payload.get('original_version'),
        'improved_version': payload.get('improved_version'),
        'base_pdf_available': payload.get('base_pdf_available'),
        'sections': sections,
    }


def _filter_incident_scenarios(scenarios, search_term):
    term = (search_term or '').strip().lower()
    if not term:
        return scenarios
    filtered = []
    for scenario in scenarios:
        if term in _scenario_search_blob(scenario):
            filtered.append(scenario)
    return filtered


def _paperwork_guide_manage_scenarios():
    scenarios = list(_load_incident_scenarios())
    by_slug = {scenario.get('slug'): scenario for scenario in scenarios if scenario.get('slug')}
    for custom in _load_custom_incident_scenarios(include_inactive=True):
        slug = custom.get('slug')
        if slug and slug not in by_slug:
            scenarios.append(custom)
            by_slug[slug] = custom
    return sorted(scenarios, key=lambda item: str(item.get('title') or '').lower())


def _scenario_textarea_payload(scenario):
    paperwork_lines = [
        str(item.get('label') or '').strip()
        for item in scenario.get('required_paperwork') or []
        if isinstance(item, dict) and str(item.get('label') or '').strip()
    ]
    return {
        'title': scenario.get('title') or '',
        'slug': scenario.get('slug') or '',
        'description': scenario.get('description') or '',
        'required_paperwork_text': '\n'.join(paperwork_lines),
        'officer_responsibilities': scenario.get('officer_responsibilities') or '',
        'notes': scenario.get('notes') or '',
        'active': scenario.get('active', True) is not False,
        'source': scenario.get('source') or 'handbook',
        'updated_at': scenario.get('updated_at') or '',
    }


def _paperwork_guide_form_payload(form):
    title = (form.get('title') or '').strip()
    slug = _slugify_text(form.get('slug') or title)
    selected_forms = []
    if hasattr(form, 'getlist'):
        selected_forms = form.getlist('paperwork_forms')
    paperwork_lines = selected_forms + _split_text_lines(form.get('required_paperwork_text') or '')
    return {
        'title': title,
        'slug': slug,
        'description': (form.get('description') or '').strip(),
        'required_paperwork': _paperwork_items_from_value(paperwork_lines),
        'officer_responsibilities': '\n'.join(_split_text_lines(form.get('officer_responsibilities') or '')),
        'notes': '\n'.join(_split_text_lines(form.get('notes') or '')),
        'active': form.get('active') == 'on',
    }


@bp.route('/reference', methods=['GET'])
@login_required
def quick_reference():
    return redirect(url_for('reference.officer_handbook'))


@bp.route('/officer-handbook', methods=['GET'])
@login_required
def officer_handbook():
    payload = _load_handbook()
    search_term = (request.args.get('q') or '').strip()
    target_form = (request.args.get('form') or '').strip().lower()
    if not search_term and target_form:
        search_term = target_form
    filtered = _filter_handbook(payload, search_term)
    forms = Form.query.filter_by(is_active=True).order_by(Form.title.asc()).all()
    return render_template(
        'officer_handbook.html',
        user=current_user,
        handbook=filtered,
        search_term=search_term,
        target_form=target_form,
        forms=forms,
        can_edit_handbook=_can_edit_handbook(),
        pdf_available=os.path.exists(_handbook_pdf_file()),
    )


@bp.route('/incident-paperwork-guide', methods=['GET'])
@login_required
def incident_paperwork_guide():
    search_term = (request.args.get('q') or request.args.get('incident') or '').strip()
    scenarios = _load_incident_scenarios()
    reference_index = _load_form_reference_index()
    filtered = [
        _decorate_incident_scenario(item, reference_index)
        for item in _filter_incident_scenarios(scenarios, search_term)
    ]
    quick_incidents = _quick_incident_cards(scenarios)
    return render_template(
        'incident_paperwork_guide.html',
        user=current_user,
        search_term=search_term,
        scenarios=filtered,
        quick_incidents=quick_incidents,
        scenario_count=len(scenarios),
        form_reference_count=len(reference_index),
    )


@bp.route('/incident-paperwork-guide/manage', methods=['GET', 'POST'])
@login_required
def incident_paperwork_guide_manage():
    if not current_user.can_manage_site():
        abort(403)

    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()
        slug = _slugify_text(request.form.get('slug') or request.form.get('title'))
        title = (request.form.get('title') or '').strip()

        if action == 'delete':
            if not slug:
                flash('Choose a navigator entry before removing it.', 'error')
                return redirect(url_for('reference.incident_paperwork_guide_manage'))
            _hide_custom_incident_scenario(slug, title=title)
            db.session.add(AuditLog(actor_id=current_user.id, action='paperwork_guide_hide', details=slug))
            db.session.commit()
            flash('Navigator entry hidden from the paperwork guide.', 'success')
            return redirect(url_for('reference.incident_paperwork_guide_manage'))

        payload = _paperwork_guide_form_payload(request.form)
        if not payload['title']:
            flash('Incident / call type name is required.', 'error')
            return redirect(url_for('reference.incident_paperwork_guide_manage'))
        if not payload['required_paperwork']:
            flash('Add at least one paperwork item so officers know what to use.', 'error')
            return redirect(url_for('reference.incident_paperwork_guide_manage', edit=payload['slug']))

        saved = _save_custom_incident_scenario(payload)
        db.session.add(AuditLog(actor_id=current_user.id, action='paperwork_guide_save', details=saved['slug']))
        db.session.commit()
        flash('Paperwork Navigator entry saved.', 'success')
        return redirect(url_for('reference.incident_paperwork_guide_manage', edit=saved['slug']))

    scenarios = _paperwork_guide_manage_scenarios()
    edit_slug = _slugify_text(request.args.get('edit') or '')
    edit_scenario = next((item for item in scenarios if item.get('slug') == edit_slug), None)
    if edit_slug and not edit_scenario:
        flash('That navigator entry was not found. You can add it now.', 'error')
    edit_payload = _scenario_textarea_payload(edit_scenario or {})
    active_forms = Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).all()
    return render_template(
        'incident_paperwork_guide_manage.html',
        user=current_user,
        scenarios=scenarios,
        edit_scenario=edit_payload,
        edit_slug=edit_slug,
        active_forms=active_forms,
    )


@bp.route('/officer-handbook/print', methods=['GET'])
@login_required
def print_officer_handbook():
    payload = _load_handbook()
    forms = Form.query.filter_by(is_active=True).order_by(Form.title.asc()).all()
    return render_template(
        'officer_handbook.html',
        user=current_user,
        handbook=payload,
        search_term='',
        target_form='',
        forms=forms,
        can_edit_handbook=_can_edit_handbook(),
        pdf_available=os.path.exists(_handbook_pdf_file()),
        print_mode=True,
    )


@bp.route('/officer-handbook/pdf', methods=['GET'])
@login_required
def download_officer_handbook_pdf():
    pdf_path = _handbook_pdf_file()
    if not os.path.exists(pdf_path):
        abort(404)
    return send_file(pdf_path, as_attachment=True, download_name='MCPD-Officer-Handbook.pdf')


@bp.route('/officer-handbook/email', methods=['POST'])
@login_required
def email_officer_handbook():
    recipient = _safe_email(current_user.email)
    if not recipient:
        flash('Set your profile email before emailing handbook.', 'error')
        return redirect(url_for('reference.officer_handbook'))
    pdf_path = _handbook_pdf_file()
    subject = 'MCPD Officer Handbook'
    body = (
        f"Officer Handbook generated for {current_user.display_name}.\n"
        f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Download link: {url_for('reference.download_officer_handbook_pdf', _external=True)}\n"
    )
    try:
        sent, info = _smtp_send_with_attachment(recipient, subject, body, pdf_path if os.path.exists(pdf_path) else None)
    except Exception as exc:
        sent, info = False, str(exc)
    if sent:
        db.session.add(AuditLog(actor_id=current_user.id, action='handbook_email', details='sent'))
        db.session.commit()
        flash('Handbook emailed to your profile address.', 'success')
    else:
        mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body)}"
        db.session.add(AuditLog(actor_id=current_user.id, action='handbook_email', details='fallback'))
        db.session.commit()
        flash(f'SMTP unavailable. Use fallback: {mailto}', 'error')
    return redirect(url_for('reference.officer_handbook'))


@bp.route('/officer-handbook/admin', methods=['GET', 'POST'])
@login_required
def officer_handbook_admin():
    if not _can_edit_handbook():
        abort(403)
    _bootstrap_handbook_storage()
    payload = _load_json_payload(_handbook_additions_file(), _default_additions_payload())
    if request.method == 'POST':
        raw = (request.form.get('handbook_json') or '').strip()
        if not raw:
            flash('Handbook JSON cannot be empty.', 'error')
            return redirect(url_for('reference.officer_handbook_admin'))
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            flash(f'Invalid JSON: {exc}', 'error')
            return redirect(url_for('reference.officer_handbook_admin'))
        if not isinstance(parsed, dict) or 'sections' not in parsed:
            flash('JSON must be an object containing a sections array.', 'error')
            return redirect(url_for('reference.officer_handbook_admin'))
        if not isinstance(parsed.get('sections'), list):
            flash('Handbook sections must be a JSON array.', 'error')
            return redirect(url_for('reference.officer_handbook_admin'))
        parsed.setdefault('title', payload.get('title', 'Officer Handbook Additions'))
        parsed.setdefault('version', payload.get('version', '1.0'))
        _save_handbook_additions(parsed)
        db.session.add(AuditLog(actor_id=current_user.id, action='handbook_update', details='json_saved'))
        db.session.commit()
        flash('Officer handbook additions updated. Original uploaded handbook remains unchanged.', 'success')
        return redirect(url_for('reference.officer_handbook'))
    return render_template(
        'officer_handbook_admin.html',
        user=current_user,
        handbook_json=json.dumps(payload, indent=2, ensure_ascii=True),
    )
