import json
import os
import smtplib
import time
from email.message import EmailMessage
from functools import lru_cache
from pathlib import Path

import re

import functools
import hmac

from flask import Blueprint, current_app, g, jsonify, render_template, request, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    AuditLog,
    Form,
    IncidentPacket,
    PACKET_APPROVAL_APPROVED,
    PACKET_APPROVAL_NEEDS_CORRECTION,
    PACKET_APPROVAL_PENDING,
    SavedForm,
    Report,
    User,
    utcnow_naive,
)
from ..permissions import can_supervisor_review
from ..services.ai_client import ask_openai, is_ai_unavailable_message
from ..services.call_type_rules import load_call_type_rules
from ..services.forms_pdf_renderer import inspect_xfa_fields, render_form_pdf
from ..services.mobile_incident_documents import build_narrative_draft, build_packet_pdf
from ..services.mobile_form_catalog import build_mobile_form_catalog

bp = Blueprint('mobile', __name__)


def _require_csrf(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = (
            request.headers.get('X-CSRFToken')
            or (request.get_json(silent=True) or {}).get('_csrf_token')
            or ''
        )
        expected = session.get('_csrf_token', '')
        if not expected or not hmac.compare_digest(str(token), str(expected)):
            return jsonify({'ok': False, 'error': 'CSRF validation failed.'}), 403
        return f(*args, **kwargs)
    return wrapper


PACKET_ALLOWED_FORM_STATUSES = {'COMPLETED', 'SUBMITTED'}
LEGACY_FORM_ALIASES = {
    'incidentreport': 'DD FORM 1920 ALCOHOL INCIDENT REPORT',
    'witnessstatement': 'OPNAV 5580 2 Voluntary Statement',
    'voluntarystatement': 'OPNAV 5580 2 Voluntary Statement',
    'useofforcereport': 'NAVMC 11130 Statement of Force Use of Detention',
    'evidencepropertyform': 'OPNAV 5580 22Evidence Custody Document',
    'evidenceform': 'OPNAV 5580 22Evidence Custody Document',
    'propertyform': 'OPNAV 5580 22Evidence Custody Document',
    'victimsassistanceworksheet': 'DD Form 2701 VWAP',
    'incidentaccidentreport': 'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
    'vehicleimpoundform': 'DD Form 2506Vehicle Impoundment Report',
    'fieldsketch': 'TA FIELD SKETCH NEW',
    'donvehiclereport': 'OPNAV 5580 12 DON VEHICLE REPORT',
    'fieldinterviewcard': 'OPNAV 5580 21Field Interview Card',
    'citationnoticedocumentation': 'UNSECURED BUILDING NOTICE',
}


def _shell_context(title, active_tab):
    return {
        'title': f'{title} | MCPD Mobile',
        'body_class': 'mobile-foundation',
        'mobile_title': title,
        'mobile_active_tab': active_tab,
        'mobile_call_type_rules': load_call_type_rules(),
        'user': current_user,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _handbook_backup_blob():
    path = _repo_root() / 'app' / 'data' / 'handbook' / 'officer_handbook_generated_backup.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _domestic_mobile_schema():
    try:
        forms_dir = _repo_root() / 'data' / 'uploads' / 'forms'
        matches = sorted(forms_dir.glob('*DOMESTIC*CHECKLIST*.pdf'))
    except OSError:
        return {'sections': []}
    if not matches:
        return {'sections': []}
    try:
        info = inspect_xfa_fields(str(matches[0]))
    except Exception:
        return {'sections': []}
    fields = info.get('fields', []) if isinstance(info.get('fields'), list) else []
    section_specs = [
        ('Dispatch And Parties', 'SupInitial.1'),
        ('Victim Condition And Statements', 'SupInitial.2'),
        ('Suspect Condition And Statements', 'Angry1'),
        ('Scene, Relationship, And Prior Violence', 'FQ'),
        ('Witnesses, Evidence, And Victim Services', 'SupInitial.4'),
        ('Medical Response And Injury Documentation', 'SupInitial.7'),
    ]
    index_lookup = {}
    for index, field in enumerate(fields):
        raw_name = str(field.get('raw_name') or field.get('name') or '')
        if raw_name.startswith('form1.'):
            raw_name = raw_name.split('form1.', 1)[1]
        if raw_name and raw_name not in index_lookup:
            index_lookup[raw_name] = index
    ordered = [(title, index_lookup.get(anchor)) for title, anchor in section_specs if index_lookup.get(anchor) is not None]
    ordered.sort(key=lambda item: item[1])
    sections = []
    for idx, (title, start) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(fields)
        section_fields = []
        for field in fields[start:end]:
            raw_name = str(field.get('raw_name') or field.get('name') or '').strip()
            full_name = str(field.get('name') or '').strip()
            field_type = str(field.get('type') or 'text').strip().lower() or 'text'
            section_fields.append(
                {
                    'name': full_name or raw_name,
                    'raw_name': raw_name,
                    'label': str(field.get('label') or raw_name or '').strip() or 'Field',
                    'type': field_type,
                    'group_names': list(field.get('group_names') or []),
                }
            )
        sections.append({'title': title, 'fields': section_fields})
    return {'sections': sections}


def _normalize_key(value):
    return ''.join(ch for ch in str(value or '').lower() if ch.isalnum())


def _canonical_form_title(title):
    raw = str(title or '').strip()
    return LEGACY_FORM_ALIASES.get(_normalize_key(raw), raw)


def _is_statement_form_title(title):
    return 'voluntarystatement' in _normalize_key(title)


def _is_domestic_form_title(title):
    return 'domesticviolence' in _normalize_key(title)


def _is_narrative_virtual_title(title):
    normalized = _normalize_key(title)
    return normalized in {'narrative', 'incidentnarrative', 'incidentreportnarrative'}


def _state_form_drafts(state):
    return state.get('formDrafts') if isinstance(state.get('formDrafts'), dict) else {}


def _domestic_mobile_draft(state):
    drafts = _state_form_drafts(state)
    draft = drafts.get('domesticSupplemental')
    if isinstance(draft, dict):
        return dict(draft)
    legacy = state.get('domesticSupplemental')
    return dict(legacy) if isinstance(legacy, dict) else {}


def _person_by_role(state, role_name):
    people = state.get('persons') if isinstance(state.get('persons'), list) else []
    wanted = str(role_name or '').strip().lower()
    for item in people:
        if not isinstance(item, dict):
            continue
        if str(item.get('role') or '').strip().lower() == wanted:
            return item
    return {}


def _domestic_mobile_enriched_draft(state):
    draft = _domestic_mobile_draft(state)
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    victim = _person_by_role(state, 'Victim')
    suspect = _person_by_role(state, 'Suspect')
    if victim.get('name') and not str(_domestic_lookup(draft, 'VicName') or '').strip():
        draft['form1.VicName'] = str(victim.get('name') or '').strip()
    if basics.get('occurredDate') and not str(_domestic_lookup(draft, 'ResponseDate') or '').strip():
        draft['form1.ResponseDate'] = str(basics.get('occurredDate') or '').strip()
    response_time = str(basics.get('arrivalTime') or basics.get('occurredTime') or '').strip()
    if response_time and not str(_domestic_lookup(draft, 'RespTime') or '').strip():
        draft['form1.RespTime'] = response_time
    if basics.get('summary') and not str(_domestic_lookup(draft, 'Reported') or '').strip():
        draft['form1.Reported'] = str(basics.get('summary') or '').strip()
    if victim and not _domestic_truthy(draft, 'Victim'):
        draft['form1.RadioButtonList.Victim'] = 'Yes'
    if suspect and not _domestic_truthy(draft, 'Suspect'):
        draft['form1.RadioButtonList.Suspect'] = 'Yes'
    return draft


def _domestic_lookup(draft, suffix):
    suffix = str(suffix or '').strip()
    if not suffix:
        return ''
    if suffix in draft:
        return draft.get(suffix)
    for key, value in draft.items():
        clean_key = str(key or '').strip()
        if clean_key == suffix or clean_key.endswith(f'.{suffix}'):
            return value
    return ''


def _domestic_truthy(draft, suffix):
    return str(_domestic_lookup(draft, suffix) or '').strip().lower() in {'1', 'true', 'yes', 'on', 'x'}


def _domestic_core_errors(draft):
    errors = []
    required_fields = [
        ('Victim Name', 'VicName'),
        ('Response Date', 'ResponseDate'),
        ('Response Time', 'RespTime'),
        ('Initial Incident / Violation Reported', 'Reported'),
    ]
    for label, key in required_fields:
        if not str(_domestic_lookup(draft, key) or '').strip():
            errors.append({'field': label, 'message': f'{label} is missing from the domestic supplemental.'})

    if not any(_domestic_truthy(draft, key) for key in ('Victim', 'Suspect', 'Child', 'Other')):
        errors.append({'field': 'Domestic Roles', 'message': 'Identify who the domestic incident involved.'})

    conditional_requirements = [
        ('Incident location detail', 'IncidentOther', 'Where'),
        ('Temporary address location', 'OtherLoc', 'Location'),
        ('Other victim service location', 'NO', 'OtherLocation'),
        ('Victim first aid by', 'VFA', 'FirstAidBy.1'),
        ('Victim treatment facility', 'VMTF', 'Facility.1'),
        ('Suspect first aid by', 'SFA', 'FirstAidBy.2'),
        ('Suspect treatment facility', 'SMTF', 'Facility.2'),
        ('Injury explanation', 'OtherEx', 'InjExplain'),
        ('Second injury explanation', 'OtherEx1', 'InjExplain1'),
    ]
    for label, trigger_key, value_key in conditional_requirements:
        if _domestic_truthy(draft, trigger_key) and not str(_domestic_lookup(draft, value_key) or '').strip():
            errors.append({'field': label, 'message': f'{label} is required for the selected domestic supplemental option.'})
    return errors


def _domestic_payload(schema, draft):
    values = {}
    draft = draft if isinstance(draft, dict) else {}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            field_name = str(field.get('name') or '').strip()
            if not field_name:
                continue
            values[field_name] = str(_domestic_lookup(draft, field_name) or '').strip()
    return {
        'schema_id': schema.get('id') or '',
        'values': values,
        'role_entries': [],
        'notes': '',
    }


def _statement_text(statement):
    return str(
        statement.get('reviewedDraft')
        or statement.get('formattedDraft')
        or statement.get('formattedStatement')
        or statement.get('reviewedStatement')
        or ''
    ).strip()


def _statement_initials_value(statement):
    return str(statement.get('initialsDataUrl') or statement.get('initials') or '').strip()


def _statement_signature_value(statement):
    return str(statement.get('signatureDataUrl') or statement.get('signature') or '').strip()


def _statement_witness_signature_value(statement):
    return str(
        statement.get('witnessingSignatureDataUrl')
        or statement.get('officerSignature')
        or statement.get('witnessSignature')
        or ''
    ).strip()


def _statement_ready(state):
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []
    if not statements:
        return False
    for statement in statements:
        if not _statement_text(statement):
            return False
        if not _statement_initials_value(statement):
            return False
        if not _statement_signature_value(statement):
            return False
        if not _statement_witness_signature_value(statement):
            return False
    return True


def _packet_recipient_context():
    from .forms import _email_recipients_for_current_user

    return _email_recipients_for_current_user()


def _state_packet_email(state):
    packet_status = state.get('packetStatus')
    if isinstance(packet_status, dict):
        return str(packet_status.get('email') or packet_status.get('recipient') or '').strip()
    return ''


def _dedupe_titles(values):
    ordered = []
    seen = set()
    for value in values or []:
        title = _canonical_form_title(value)
        if not title:
            continue
        key = _normalize_key(title)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(title)
    return ordered


def _packet_form_entries(state):
    requested_titles = _dedupe_titles(state.get('selectedForms') or [])
    forms = Form.query.filter_by(is_active=True).all()
    forms_by_key = {_normalize_key(form.title): form for form in forms}
    domestic_draft = _domestic_mobile_enriched_draft(state)
    entries = []
    statements_present = bool(state.get('statements')) if isinstance(state, dict) else False
    for requested in requested_titles:
        if _is_narrative_virtual_title(requested):
            narrative_text = str(state.get('narrative') or '').strip() or build_narrative_draft(state)
            narrative_ready = bool(str(narrative_text or '').strip()) and bool(state.get('narrativeApproved'))
            entries.append(
                {
                    'requested_title': requested,
                    'form': None,
                    'saved': None,
                    'source_mode': 'mobile_narrative',
                    'status': 'COMPLETED' if narrative_ready else 'NOT_STARTED',
                    'status_label': 'Completed' if narrative_ready else 'Not Started',
                    'title': 'Narrative',
                    'preview_url': url_for('mobile.incident_narrative_review', _external=True),
                    'mobile_draft': {},
                }
            )
            continue
        form = forms_by_key.get(_normalize_key(requested))
        saved = None
        if form is not None:
            saved = (
                SavedForm.query.filter_by(form_id=form.id, officer_user_id=current_user.id)
                .order_by(SavedForm.updated_at.desc())
                .first()
            )
        status = str(getattr(saved, 'status', '') or '').strip().upper() or 'NOT_STARTED'
        source_mode = 'saved_form' if saved is not None else 'unresolved'
        if _is_statement_form_title(requested) and (statements_present or saved is None):
            source_mode = 'mobile_statement'
            status = 'COMPLETED' if _statement_ready(state) else ('DRAFT' if state.get('statements') else 'NOT_STARTED')
        elif _is_domestic_form_title(requested) and (domestic_draft or saved is None):
            source_mode = 'mobile_domestic'
            status = 'COMPLETED' if domestic_draft and not _domestic_core_errors(domestic_draft) else ('DRAFT' if domestic_draft else 'NOT_STARTED')
        entries.append(
            {
                'requested_title': requested,
                'form': form,
                'saved': saved,
                'source_mode': source_mode,
                'status': status,
                'status_label': status.replace('_', ' ').title(),
                'title': form.title if form is not None else requested,
                'preview_url': (
                    url_for('forms.preview_saved_form', saved_form_id=saved.id, _external=True)
                    if saved is not None
                    else url_for('mobile.incident_domestic_supplemental', _external=True)
                    if source_mode == 'mobile_domestic'
                    else url_for('mobile.statement_review', _external=True)
                    if source_mode == 'mobile_statement'
                    else url_for('forms.blank_form_preview', form_id=form.id, _external=True)
                    if form is not None
                    else ''
                ),
                'mobile_draft': domestic_draft if source_mode == 'mobile_domestic' else {},
            }
        )
    return entries


def _packet_validation(state, form_entries, recipient):
    errors = []
    warnings = []
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    facts = state.get('facts') if isinstance(state.get('facts'), list) else []
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []
    checklist = state.get('checklist') if isinstance(state.get('checklist'), list) else []
    narrative = str(state.get('narrative') or '').strip() or build_narrative_draft(state)
    narrative_approved = bool(state.get('narrativeApproved'))
    persons = state.get('persons') if isinstance(state.get('persons'), list) else []

    if not str(state.get('callType') or '').strip():
        errors.append({'field': 'Call Type', 'message': 'Select the incident call type before sending the packet.'})
    if not str(basics.get('occurredDate') or '').strip():
        errors.append({'field': 'Incident Date', 'message': 'Incident date is missing.'})
    if not str(basics.get('occurredTime') or '').strip():
        errors.append({'field': 'Incident Time', 'message': 'Incident time is missing.'})
    if not str(basics.get('location') or '').strip():
        errors.append({'field': 'Location', 'message': 'Incident location is missing.'})
    if not str(basics.get('summary') or '').strip():
        errors.append({'field': 'Summary', 'message': 'Incident summary is missing.'})
    if not any(str(item.get('value') or '').strip() for item in facts if isinstance(item, dict)):
        errors.append({'field': 'Facts Capture', 'message': 'Capture at least one factual section before sending.'})
    if not narrative:
        errors.append({'field': 'Narrative', 'message': 'Narrative review is still blank.'})
    elif not narrative_approved:
        errors.append({'field': 'Narrative', 'message': 'Approve the narrative review before sending the packet.'})
    else:
        nq = _narrative_quality_check(narrative)
        for issue in nq.get('issues', []):
            warnings.append({'field': 'Narrative Quality', 'message': issue})
    if not form_entries:
        errors.append({'field': 'Forms', 'message': 'Select at least one form for the packet.'})
    if not persons:
        errors.append({'field': 'People', 'message': 'Add the involved people before sending the packet.'})
    for index, person in enumerate(persons, start=1):
        if not isinstance(person, dict):
            errors.append({'field': f'Person {index}', 'message': 'Person entry is invalid.'})
            continue
        if not str(person.get('role') or '').strip():
            errors.append({'field': f'Person {index}', 'message': 'Each involved person must have a role.'})
        if not str(person.get('name') or '').strip():
            errors.append({'field': f'Person {index}', 'message': 'Each involved person must have a name.'})

    requires_statement = any('voluntarystatement' in _normalize_key(entry['title']) for entry in form_entries)
    if requires_statement and not statements:
        errors.append({'field': 'Statements', 'message': 'A voluntary statement form is selected, but no statement has been captured.'})

    for entry in form_entries:
        if entry['form'] is None and entry.get('source_mode') not in {'mobile_statement', 'mobile_domestic', 'mobile_narrative'}:
            errors.append({'field': 'Forms', 'message': f'Selected form "{entry["requested_title"]}" could not be resolved in the live form library.'})
            continue
        if entry['status'] not in PACKET_ALLOWED_FORM_STATUSES:
            errors.append(
                {
                    'field': entry['title'],
                    'message': f'Form status is {entry["status_label"]}. Complete or submit this form before sending the packet.',
                }
            )
        if entry.get('source_mode') == 'mobile_domestic':
            errors.extend(_domestic_core_errors(entry.get('mobile_draft') or {}))

    for index, statement in enumerate(statements, start=1):
        label = str(statement.get('formTitle') or f'Statement {index}')
        reviewed_text = _statement_text(statement)
        if not reviewed_text:
            errors.append({'field': label, 'message': 'Statement review text is missing.'})
        if not _statement_initials_value(statement):
            errors.append({'field': label, 'message': 'Statement initials are missing.'})
        if not _statement_signature_value(statement):
            errors.append({'field': label, 'message': 'Declarant signature is missing.'})
        if not _statement_witness_signature_value(statement):
            errors.append({'field': label, 'message': 'Witnessing officer signature is missing.'})

    for item in checklist:
        if not isinstance(item, dict):
            continue
        if not bool(item.get('completed')):
            warnings.append({'field': 'Checklist', 'message': str(item.get('label') or 'Checklist item is still open.').strip()})

    if not recipient and not _state_packet_email(state):
        errors.append({'field': 'Profile Email', 'message': 'Your profile email is required before sending the packet.'})

    return {
        'errors': errors,
        'warnings': warnings,
        'can_send': not errors,
    }


def _narrative_quality_check(narrative_text: str) -> dict:
    text = str(narrative_text or '').strip()
    if not text:
        return {
            'ok': False,
            'word_count': 0,
            'char_count': 0,
            'issues': ['Narrative is empty.'],
            'prompts': ['Who was involved?', 'What happened?', 'Where did it occur?', 'When did it happen?', 'What actions did you take?'],
        }

    words = text.split()
    word_count = len(words)
    issues = []
    prompts = []

    if word_count < 30:
        issues.append(f'Narrative is very short ({word_count} words). A thorough narrative should have at least 50 words.')
    elif word_count < 50:
        issues.append(f'Narrative is brief ({word_count} words). Consider adding more detail.')

    # Detect repeated sentences
    sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if len(s.strip()) > 10]
    seen_sentences: set = set()
    for s in sentences:
        normalized = ' '.join(s.lower().split())
        if normalized in seen_sentences:
            issues.append('Narrative contains repeated text. Check for duplicate sentences.')
            break
        seen_sentences.add(normalized)

    # Check for key narrative elements
    tl = text.lower()
    if not any(w in tl for w in ('officer', 'this officer', 'i ', 'responding', 'writer', 'reporting')):
        prompts.append('Who was the responding officer?')
    if not any(w in tl for w in ('suspect', 'victim', 'subject', 'person', 'individual', 'complainant', 'witness')):
        prompts.append('Who was involved (suspect/victim/witness)?')
    if not any(w in tl for w in ('located', 'area', 'building', 'parking', 'lot', 'street', ' at ', ' near ', ' on ')):
        prompts.append('Where exactly did this occur?')
    if not any(w in tl for w in ('approximately', 'approx', 'hours', ' at ', ' on ')):
        prompts.append('When did this occur?')
    if not any(w in tl for w in ('arrested', 'detained', 'advised', 'responded', 'notified', 'issued', 'transported', 'released', 'reported', 'cleared', 'secured')):
        prompts.append('What actions were taken?')

    return {
        'ok': not issues,
        'word_count': word_count,
        'char_count': len(text),
        'issues': issues,
        'prompts': prompts,
    }


def _rule_based_narrative_suggestions(narrative: str, state: dict) -> list:
    """Return actionable suggestion dicts for a narrative. Never invents facts."""
    text = str(narrative or '').strip()
    tl = text.lower()
    words = text.split()
    wc = len(words)
    suggestions = []

    if not text:
        return [{'severity': 'error', 'element': 'length', 'text': 'Narrative is empty. Write a narrative before analyzing.'}]

    if wc < 30:
        suggestions.append({'severity': 'error', 'element': 'length', 'text': f'Narrative is very short ({wc} words). Aim for at least 50 words for a complete report.'})
    elif wc < 50:
        suggestions.append({'severity': 'warn', 'element': 'length', 'text': f'Narrative is brief ({wc} words). Consider expanding with more detail.'})

    if not any(w in tl for w in ('officer', 'this officer', 'responding', 'writer', 'reporting')):
        suggestions.append({'severity': 'warn', 'element': 'who', 'text': 'Identify the responding officer by rank/name or use "This officer" or "The reporting officer".'})

    if not any(w in tl for w in ('suspect', 'victim', 'subject', 'person', 'individual', 'complainant', 'witness')):
        suggestions.append({'severity': 'warn', 'element': 'who', 'text': 'Identify involved parties by role (suspect, victim, complainant, witness).'})

    if not any(w in tl for w in ('located', 'arrived at', 'responded to', 'observed at', 'building', 'parking', 'street', ' at ', ' near ', ' on ')):
        suggestions.append({'severity': 'warn', 'element': 'where', 'text': 'Include the exact location of the incident or your response.'})

    if not any(w in tl for w in ('approximately', 'at approx', 'hours', 'at 0', 'at 1', 'at 2')):
        suggestions.append({'severity': 'warn', 'element': 'when', 'text': 'State the time of occurrence or your response (e.g., "at approximately 1430 hours").'})

    if not any(w in tl for w in ('arrested', 'detained', 'advised', 'responded', 'notified', 'issued', 'transported', 'released', 'cleared', 'secured', 'observed', 'interviewed')):
        suggestions.append({'severity': 'warn', 'element': 'actions', 'text': 'Document the officer\'s actions taken (detained, interviewed, cleared, arrested, etc.).'})

    if not any(w in tl for w in ('disposition', 'cleared', 'released', 'arrested', 'transported', 'unfounded', 'referred', 'report taken')):
        suggestions.append({'severity': 'info', 'element': 'disposition', 'text': 'Add a disposition line at the end (cleared, arrested, report taken, unfounded, etc.).'})

    # Repeated sentence check
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 10]
    seen_s: set = set()
    for s in sentences:
        norm = ' '.join(s.lower().split())
        if norm in seen_s:
            suggestions.append({'severity': 'warn', 'element': 'quality', 'text': 'Narrative contains repeated text. Remove duplicate sentences.'})
            break
        seen_s.add(norm)

    # Cross-check persons in state
    persons = state.get('persons') if isinstance(state.get('persons'), list) else []
    for person in persons:
        if not isinstance(person, dict):
            continue
        name = str(person.get('name') or '').strip()
        if not name or len(name) < 4:
            continue
        parts = name.lower().split()
        if not any(part in tl for part in parts if len(part) > 2):
            suggestions.append({'severity': 'info', 'element': 'persons', 'text': f'Person "{name}" is entered in the incident but not mentioned in the narrative.'})

    return suggestions


def _ai_narrative_suggestions(narrative: str, state: dict, api_key: str):
    """Call OpenAI for narrative improvement suggestions. Returns list of dicts or error string."""
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    call_type = str(state.get('callType') or '').replace('-', ' ').strip()
    location = str(basics.get('location') or '').strip()

    prompt = (
        'You are a professional police report writing coach for MCPD. '
        'Review the incident narrative below and return up to 4 specific, actionable improvement suggestions. '
        'RULES: (1) Do NOT add or invent any facts. Only analyze what is written. '
        '(2) Suggest improvements to clarity, professional wording, logical flow, and completeness. '
        '(3) If the narrative is adequate, respond with a JSON array containing one item saying so. '
        '(4) Return ONLY a JSON array. Each element: {"severity":"warn"|"info","text":"suggestion"}. '
        f'Call type: {call_type or "unknown"}. Location: {location or "unknown"}.\n\nNarrative:\n{narrative[:1200]}'
    )
    result = ask_openai(prompt, api_key)
    if is_ai_unavailable_message(result):
        return result  # caller checks with is_ai_unavailable_message
    match = re.search(r'\[.*?\]', result, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
        if not isinstance(items, list):
            return []
        out = []
        for item in items[:5]:
            if isinstance(item, dict) and str(item.get('text') or '').strip():
                out.append({'severity': str(item.get('severity') or 'info'), 'text': str(item['text']).strip()[:300], 'ai': True})
        return out
    except (ValueError, KeyError):
        return []


def _rule_based_form_suggestions(state: dict) -> list:
    """Return paperwork suggestion dicts based on incident state. Never auto-adds forms."""
    suggestions = []
    call_type = str(state.get('callType') or '').lower()
    persons = state.get('persons') if isinstance(state.get('persons'), list) else []
    selected_forms_raw = state.get('selectedForms') if isinstance(state.get('selectedForms'), list) else []
    selected_lower = [str(f).lower() for f in selected_forms_raw]
    facts = state.get('facts') if isinstance(state.get('facts'), list) else []
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}

    # Build searchable text corpus from all captured data
    text_corpus = ' '.join([
        str(f.get('value') or '') for f in facts if isinstance(f, dict)
    ] + [
        str(state.get('narrative') or ''),
        str(basics.get('summary') or ''),
    ]).lower()

    has_victim = any(str(p.get('role') or '').lower() in ('victim', 'complainant') for p in persons if isinstance(p, dict))
    has_witness = any('witness' in str(p.get('role') or '').lower() for p in persons if isinstance(p, dict))
    has_suspect = any(str(p.get('role') or '').lower() in ('suspect', 'subject') for p in persons if isinstance(p, dict))
    has_statement_form = any('statement' in f for f in selected_lower)
    has_evidence_form = any('evidence' in f or 'custody' in f or 'property' in f for f in selected_lower)
    has_domestic_form = any('domestic' in f for f in selected_lower)
    has_vwap = any('2701' in f or 'vwap' in f for f in selected_lower)
    has_force_form = any('force' in f or '11130' in f for f in selected_lower)

    evidence_words = ('evidence', 'seized', 'weapon', 'contraband', 'narcotics', 'drug', 'firearm', 'gun', 'knife', 'exhibit')
    injury_words = ('injured', 'injury', 'hurt', 'bleeding', 'medical', 'hospital', 'laceration', 'bruise')
    has_evidence_mention = any(w in text_corpus for w in evidence_words)
    has_injury_mention = any(w in text_corpus for w in injury_words)

    # Statement form
    if (has_victim or has_witness or has_suspect) and not has_statement_form and not statements:
        roles = [str(p.get('role') or '') for p in persons if isinstance(p, dict) and p.get('role')]
        roles_str = ', '.join(r for r in roles if r)
        suggestions.append({'severity': 'warn', 'text': f'Parties involved ({roles_str}) — consider adding OPNAV 5580-2 Voluntary Statement form.'})

    # Evidence form
    if has_evidence_mention and not has_evidence_form:
        suggestions.append({'severity': 'warn', 'text': 'Evidence or seized items detected in notes. Add OPNAV 5580-22 Evidence Custody Document.'})

    # Domestic supplement
    if 'domestic' in call_type and not has_domestic_form:
        suggestions.append({'severity': 'error', 'text': 'Domestic call type requires NAVMAC 11337 Domestic Violence Supplement.'})

    # VWAP for victim
    if has_victim and not has_vwap:
        suggestions.append({'severity': 'info', 'text': 'A victim is listed — consider DD Form 2701 (Victim/Witness Assistance Program).'})

    # Use of force
    force_indicators = ('use-of-force' in call_type, 'force' in text_corpus, 'resistance' in text_corpus)
    if any(force_indicators) and not has_force_form:
        suggestions.append({'severity': 'warn', 'text': 'Force indicators detected. NAVMC 11130 Use of Force Report may be required.'})

    # Injury note
    if has_injury_mention:
        suggestions.append({'severity': 'info', 'text': 'Injury language detected — document medical aid, injury photos, and medical clearance.'})

    return suggestions


def _build_incident_summary(state: dict) -> dict:
    """Build a structured incident summary dict from state data. Never invents facts."""
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    persons = state.get('persons') if isinstance(state.get('persons'), list) else []
    facts = state.get('facts') if isinstance(state.get('facts'), list) else []
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []

    parties = []
    for p in persons:
        if not isinstance(p, dict):
            continue
        role = str(p.get('role') or '').strip()
        name = str(p.get('name') or '').strip()
        if role and name:
            parties.append(f'{name} ({role})')
        elif name:
            parties.append(name)

    key_facts = []
    actions_taken = ''
    disposition = ''
    for item in facts:
        if not isinstance(item, dict):
            continue
        fact_id = str(item.get('id') or '').lower()
        value = str(item.get('value') or '').strip()
        label = str(item.get('label') or '').strip()
        if not value:
            continue
        if fact_id in ('officer_actions', 'actions_taken', 'actions'):
            actions_taken = value[:300]
        elif fact_id == 'disposition':
            disposition = value[:200]
        elif label:
            key_facts.append(f'{label}: {value[:200]}')
        else:
            key_facts.append(value[:200])

    date_str = str(basics.get('occurredDate') or '').strip()
    time_str = str(basics.get('occurredTime') or '').strip()

    return {
        'incident_type': str(state.get('callType') or '').replace('-', ' ').title() or None,
        'date_time': f'{date_str} {time_str}'.strip() or None,
        'location': str(basics.get('location') or '').strip() or None,
        'parties': parties,
        'key_facts': key_facts[:6],
        'actions_taken': actions_taken or None,
        'disposition': disposition or None,
        'form_count': len(state.get('selectedForms') or []),
        'statement_count': len(statements),
    }


def _compute_training_flags(missing_counts: dict, total: int, avg_word_count: int) -> list:
    """Return training flag dicts for a set of packet statistics."""
    flags = []
    if total < 2:
        return flags

    threshold = max(2, total // 2)

    stat_misses = missing_counts.get('Stat Sheet', 0) + missing_counts.get('Forms', 0)
    if stat_misses >= threshold:
        flags.append({'severity': 'error', 'text': f'Frequently missing Stat Sheet ({stat_misses}/{total} packets)'})

    narrative_misses = missing_counts.get('Narrative', 0)
    if narrative_misses >= threshold:
        flags.append({'severity': 'error', 'text': f'Narrative often missing or unapproved ({narrative_misses}/{total} packets)'})

    if 0 < avg_word_count < 40:
        flags.append({'severity': 'warn', 'text': f'Narratives often below minimum length (avg {avg_word_count} words)'})

    person_misses = missing_counts.get('People', 0)
    if person_misses >= threshold:
        flags.append({'severity': 'warn', 'text': f'Persons section frequently empty ({person_misses}/{total} packets)'})

    facts_misses = missing_counts.get('Facts Capture', 0)
    if facts_misses >= threshold:
        flags.append({'severity': 'warn', 'text': f'Facts section often empty ({facts_misses}/{total} packets)'})

    return flags


def _officer_pattern_summary(officer_user_id: int, limit: int = 20) -> dict:
    """Return pattern stats for an officer based on their recent IncidentPackets."""
    packets = (
        IncidentPacket.query
        .filter_by(officer_user_id=officer_user_id)
        .order_by(IncidentPacket.submitted_at.desc())
        .limit(limit)
        .all()
    )
    if not packets:
        return {'packet_count': 0, 'missing_counts': {}, 'flags': [], 'avg_word_count': 0}

    missing_counts: dict = {}
    word_counts: list = []
    for p in packets:
        try:
            val = json.loads(p.validation_json or '{}')
            for err in val.get('errors', []):
                field = str(err.get('field') or 'Unknown')
                missing_counts[field] = missing_counts.get(field, 0) + 1
        except Exception:
            pass
        try:
            st = json.loads(p.packet_json or '{}')
            narrative = str(st.get('narrative') or '').strip()
            if narrative:
                word_counts.append(len(narrative.split()))
        except Exception:
            pass

    avg_wc = int(sum(word_counts) / len(word_counts)) if word_counts else 0
    return {
        'packet_count': len(packets),
        'missing_counts': missing_counts,
        'flags': _compute_training_flags(missing_counts, len(packets), avg_wc),
        'avg_word_count': avg_wc,
    }


# ── Phase 7 API Endpoints ────────────────────────────────────────────────────


@bp.route('/mobile/api/narrative/suggest', methods=['POST'])
@login_required
@_require_csrf
def narrative_suggest():
    body = request.get_json(silent=True) or {}
    narrative = str(body.get('narrative') or '').strip()
    state = body.get('state') if isinstance(body.get('state'), dict) else {}

    suggestions = _rule_based_narrative_suggestions(narrative, state)

    ai_used = False
    ai_error = None
    api_key = (current_app.config.get('OPENAI_API_KEY') or '').strip()
    if api_key and narrative and len(narrative.split()) >= 10:
        try:
            ai_result = _ai_narrative_suggestions(narrative, state, api_key)
            if isinstance(ai_result, list) and ai_result:
                suggestions.extend(ai_result)
                ai_used = True
            elif isinstance(ai_result, str) and is_ai_unavailable_message(ai_result):
                ai_error = ai_result
        except Exception:
            pass

    return jsonify({'ok': True, 'suggestions': suggestions, 'ai_used': ai_used, 'ai_error': ai_error})


@bp.route('/mobile/api/forms/smart-suggest', methods=['POST'])
@login_required
@_require_csrf
def forms_smart_suggest():
    state = request.get_json(silent=True) or {}
    suggestions = _rule_based_form_suggestions(state if isinstance(state, dict) else {})
    return jsonify({'ok': True, 'suggestions': suggestions})


@bp.route('/mobile/api/incident/summary', methods=['POST'])
@login_required
@_require_csrf
def incident_summary_api():
    state = request.get_json(silent=True) or {}
    summary = _build_incident_summary(state if isinstance(state, dict) else {})
    return jsonify({'ok': True, 'summary': summary})


def _build_packet_summary_text(state, form_entries):
    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    facts = state.get('facts') if isinstance(state.get('facts'), list) else []
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []
    lines = [
        'MCPD MOBILE INCIDENT PACKET',
        '',
        'INCIDENT BASICS',
        f'Call Type: {state.get("callType") or ""}',
        f'Date: {basics.get("occurredDate") or ""}',
        f'Time: {basics.get("occurredTime") or ""}',
        f'Location: {basics.get("location") or ""}',
        f'Call Source: {basics.get("callSource") or ""}',
        f'Summary: {basics.get("summary") or ""}',
        '',
        'FACTS',
    ]
    if facts:
        for item in facts:
            if not isinstance(item, dict):
                continue
            label = str(item.get('label') or item.get('id') or 'Facts').strip()
            value = str(item.get('value') or '').strip()
            if value:
                lines.append(f'{label}: {value}')
    else:
        lines.append('No facts captured.')

    lines.extend(
        [
            '',
            'NARRATIVE',
            str(state.get('narrative') or '').strip() or build_narrative_draft(state) or 'No narrative captured.',
            '',
            'FORMS',
        ]
    )
    if form_entries:
        for entry in form_entries:
            lines.append(f'- {entry["title"]} ({entry["status_label"]})')
            if entry['preview_url']:
                lines.append(f'  Preview: {entry["preview_url"]}')
    else:
        lines.append('No forms selected.')

    lines.extend(['', 'STATEMENTS'])
    if statements:
        for index, statement in enumerate(statements, start=1):
            lines.append(f'Statement {index}: {statement.get("formTitle") or "Voluntary Statement"}')
            lines.append(f'  Speaker: {statement.get("speaker") or statement.get("personName") or ""}')
            lines.append(f'  Subject: {statement.get("statementSubject") or ""}')
            lines.append(f'  Draft: {_statement_text(statement) or statement.get("plainLanguage") or ""}')
    else:
        lines.append('No statements captured.')

    return '\n'.join(lines).strip() + '\n'


def _render_saved_form_attachment(entry):
    from .forms import _load_saved_form_data, _normalize_payload, _pdf_source_for_form, _schema_for_form

    form = entry.get('form')
    saved = entry.get('saved')
    source_mode = str(entry.get('source_mode') or '')
    if source_mode == 'mobile_statement':
        return None
    if form is None:
        return None
    schema = _schema_for_form(form)
    if source_mode == 'mobile_domestic':
        payload = _domestic_payload(schema, entry.get('mobile_draft') or {})
        file_suffix = 'mobile-domestic'
    elif saved is not None:
        payload = _normalize_payload(_load_saved_form_data(saved.field_data_json), schema)
        file_suffix = str(saved.id)
    else:
        return None
    pdf_path, _render_meta = render_form_pdf(_pdf_source_for_form(form), schema, payload, blank_mode=False)
    try:
        with open(pdf_path, 'rb') as handle:
            pdf_bytes = handle.read()
    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
    filename = f'{secure_filename(form.title or "packet-form") or "packet-form"}-{file_suffix}.pdf'
    return {
        'filename': filename,
        'content_type': 'application/pdf',
        'bytes': pdf_bytes,
        'meta': _render_meta,
    }


def _is_unfaithful_packet_render(entry, attachment):
    if not isinstance(entry, dict) or not isinstance(attachment, dict):
        return False
    title = _normalize_key(entry.get('title') or entry.get('requested_title') or '')
    meta = attachment.get('meta') if isinstance(attachment.get('meta'), dict) else {}
    mode = str(meta.get('mode') or '').strip().lower()
    return 'domesticviolence' in title and mode in {'overlay', 'overlay_template_fallback'}


def _smtp_send_packet(recipient, cc_list, subject, body, attachments):
    host = os.environ.get('SMTP_HOST', '').strip()
    sender = os.environ.get('SMTP_FROM', '').strip()
    if not host or not sender:
        return False, 'SMTP not configured.'
    port = int(os.environ.get('SMTP_PORT', '587') or '587')
    username = os.environ.get('SMTP_USERNAME', '').strip()
    password = os.environ.get('SMTP_PASSWORD', '').strip()
    use_tls = os.environ.get('SMTP_USE_TLS', '1').strip().lower() in {'1', 'true', 'yes', 'on'}

    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    if cc_list:
        message['Cc'] = ', '.join(cc_list)
    message['Subject'] = subject
    message.set_content(body)

    for attachment in attachments or []:
        content_type = str(attachment.get('content_type') or 'application/octet-stream')
        maintype, _, subtype = content_type.partition('/')
        message.add_attachment(
            attachment.get('bytes') or b'',
            maintype=maintype or 'application',
            subtype=subtype or 'octet-stream',
            filename=attachment.get('filename') or 'attachment.bin',
        )

    last_exc = None
    for attempt in range(2):
        try:
            with smtplib.SMTP(host, port, timeout=20) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(message)
            return True, 'sent'
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(1.5)
    return False, str(last_exc)


@bp.route('/mobile/home')
@login_required
def home():
    saved_forms_count = SavedForm.query.filter_by(officer_user_id=current_user.id).count()
    report_count = Report.query.filter_by(owner_id=current_user.id).count()
    primary_cards = [
        {
            'title': 'Start Incident',
            'subtitle': 'Full intake workflow',
            'href': url_for('mobile.incident_start'),
            'is_live': True,
            'is_primary': True,
        },
        {
            'title': 'Fast Capture',
            'subtitle': 'Quick field notes',
            'href': url_for('mobile.fast_capture'),
            'is_live': True,
            'is_primary': False,
        },
    ]
    feature_cards = [
        {'title': 'Forms', 'href': url_for('forms.list_forms'), 'is_live': True},
        {'title': 'Law Lookup', 'href': url_for('legal.legal_home'), 'is_live': True},
        {'title': 'Reference Library', 'href': url_for('reference.incident_paperwork_guide'), 'is_live': True},
        {'title': 'Supervisor Review', 'href': url_for('mobile.supervisor_review'), 'is_live': True},
        {'title': 'Critical Incident', 'href': url_for('mobile.critical_incident'), 'is_live': True},
        {'title': 'Accident Diagram', 'href': url_for('mobile.accident_diagram_entry'), 'is_live': True},
    ]
    if current_user.can_manage_team():
        feature_cards.append({'title': 'Admin', 'href': url_for('admin.stats_uploads'), 'is_live': True})
    return render_template(
        'mobile_home.html',
        primary_cards=primary_cards,
        feature_cards=feature_cards,
        action_cards=primary_cards + feature_cards,
        dashboard_saved_forms_count=saved_forms_count,
        dashboard_report_count=report_count,
        **_shell_context('Home', 'home'),
    )


@bp.route('/mobile/more')
@login_required
def more():
    return render_template('mobile_more.html', **_shell_context('More', 'more'))


@bp.route('/mobile/fast-capture')
@login_required
def fast_capture():
    return render_template(
        'mobile_fast_capture.html',
        mobile_header_kicker='Fast Capture',
        mobile_header_note='Capture now, refine in full workflow',
        mobile_incident_boot=False,
        mobile_incident_page='fast_capture',
        **_shell_context('Quick Notes', 'incident'),
    )


@bp.route('/mobile/supervisor-review')
@login_required
def supervisor_review():
    return render_template(
        'mobile_supervisor_review.html',
        mobile_header_kicker='Supervisor Review',
        mobile_header_note='Packet readiness check',
        mobile_incident_boot=False,
        mobile_incident_page='supervisor_review',
        **_shell_context('Packet Review', 'home'),
    )


@bp.route('/mobile/critical-incident')
@login_required
def critical_incident():
    return render_template(
        'mobile_critical_incident.html',
        mobile_header_kicker='Critical Incident',
        mobile_header_note='Required actions and paperwork',
        mobile_incident_boot=False,
        mobile_incident_page='critical_incident',
        **_shell_context('Critical Checklists', 'home'),
    )


@bp.route('/mobile/accident-diagram')
@login_required
def accident_diagram_entry():
    return render_template(
        'mobile_accident_diagram.html',
        mobile_header_kicker='Accident Diagram',
        mobile_header_note='Reconstruction tool',
        mobile_incident_boot=False,
        mobile_incident_page='accident_diagram',
        **_shell_context('Accident Diagram', 'home'),
    )


@bp.route('/mobile/incident/start')
@login_required
def incident_start():
    return render_template(
        'mobile_incident_start.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 1 of 9 / Call Type',
        mobile_incident_boot=True,
        mobile_incident_page='start',
        **_shell_context('Incident', 'incident'),
    )


@bp.route('/mobile/incident/basics')
@login_required
def incident_basics():
    return render_template(
        'mobile_incident_basics.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 2 of 9 / Basics',
        mobile_incident_boot=True,
        mobile_incident_page='basics',
        **_shell_context('Incident Basics', 'incident'),
    )


@bp.route('/mobile/incident/statute')
@login_required
def incident_statute():
    return render_template(
        'mobile_statute.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Statute',
        mobile_incident_boot=True,
        mobile_incident_page='statute',
        **_shell_context('Statute / Category', 'incident'),
    )


@bp.route('/mobile/incident/checklist')
@login_required
def incident_checklist():
    return render_template(
        'mobile_checklist.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Checklist',
        mobile_incident_boot=True,
        mobile_incident_page='checklist',
        **_shell_context('Checklist', 'incident'),
    )


@bp.route('/mobile/incident/persons')
@login_required
def incident_persons():
    return render_template(
        'mobile_persons_list.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 4 of 9 / People',
        mobile_incident_boot=True,
        mobile_incident_page='persons-list',
        **_shell_context('Persons', 'incident'),
    )


@bp.route('/mobile/incident/persons/edit')
@login_required
def incident_person_editor():
    return render_template(
        'mobile_person_editor.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 4 of 9 / Edit Person',
        mobile_incident_boot=True,
        mobile_incident_page='person-editor',
        **_shell_context('Edit Person', 'incident'),
    )


@bp.route('/mobile/incident/facts')
@login_required
def incident_facts():
    return render_template(
        'mobile_facts_capture.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 5 of 9 / Facts',
        mobile_incident_boot=True,
        mobile_incident_page='facts',
        **_shell_context('Facts Capture', 'incident'),
    )


@bp.route('/mobile/incident/statements')
@login_required
def statement_launcher():
    return render_template(
        'mobile_statement_launcher.html',
        mobile_header_kicker='Voluntary Statements',
        mobile_header_note='Step 7 of 9 / Statements',
        mobile_incident_boot=True,
        mobile_incident_page='statement-launcher',
        **_shell_context('Statement Launcher', 'incident'),
    )


@bp.route('/mobile/incident/statements/entry')
@login_required
def statement_entry():
    return render_template(
        'mobile_statement_entry.html',
        mobile_header_kicker='Voluntary Statements',
        mobile_header_note='Step 7 of 9 / Statement Entry',
        mobile_incident_boot=True,
        mobile_incident_page='statement-entry',
        **_shell_context('Statement Entry', 'incident'),
    )


@bp.route('/mobile/incident/statements/review')
@login_required
def statement_review():
    return render_template(
        'mobile_statement_review.html',
        mobile_header_kicker='Voluntary Statements',
        mobile_header_note='Step 7 of 9 / Statement Review',
        mobile_incident_boot=True,
        mobile_incident_page='statement-review',
        **_shell_context('Statement Review', 'incident'),
    )


@bp.route('/mobile/incident/statements/signature')
@login_required
def statement_signature_capture():
    return render_template(
        'mobile_signature_capture.html',
        mobile_header_kicker='Voluntary Statements',
        mobile_header_note='Step 7 of 9 / Sign',
        mobile_incident_boot=True,
        mobile_incident_page='statement-signature',
        **_shell_context('Signature Capture', 'incident'),
    )


@bp.route('/mobile/incident/narrative-review')
@login_required
def incident_narrative_review():
    return render_template(
        'mobile_narrative_review.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 6 of 9 / Narrative',
        mobile_incident_boot=True,
        mobile_incident_page='narrative-review',
        **_shell_context('Narrative Review', 'incident'),
    )


@bp.route('/mobile/incident/domestic-supplemental')
@login_required
def incident_domestic_supplemental():
    return render_template(
        'mobile_domestic_supplemental.html',
        mobile_header_kicker='Domestic Supplemental',
        mobile_header_note='Step 7 of 9 / Domestic',
        mobile_incident_boot=True,
        mobile_incident_page='domestic-supplemental',
        mobile_domestic_schema=_domestic_mobile_schema(),
        **_shell_context('Domestic Supplemental', 'incident'),
    )


@bp.route('/mobile/incident/recommended-forms')
@bp.route('/mobile/incident/selected-forms')
@login_required
def incident_selected_forms():
    latest_saved_by_form = {}
    saved_rows = (
        SavedForm.query.filter_by(officer_user_id=current_user.id)
        .order_by(SavedForm.updated_at.desc())
        .all()
    )
    for row in saved_rows:
        latest_saved_by_form.setdefault(row.form_id, row)
    forms_catalog = build_mobile_form_catalog(
        Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).all(),
        latest_saved_by_form,
    )
    return render_template(
        'mobile_recommended_forms.html',
        mobile_header_kicker='Incident Intake',
        mobile_header_note='Step 3 of 9 / Forms Used',
        mobile_incident_boot=True,
        mobile_incident_page='selected-forms',
        mobile_forms_catalog=forms_catalog,
        **_shell_context('Selected Forms', 'incident'),
    )


@bp.route('/mobile/incident/packet-review')
@login_required
def packet_review():
    latest_saved_by_form = {}
    saved_rows = (
        SavedForm.query.filter_by(officer_user_id=current_user.id)
        .order_by(SavedForm.updated_at.desc())
        .all()
    )
    for row in saved_rows:
        latest_saved_by_form.setdefault(row.form_id, row)
    forms_catalog = build_mobile_form_catalog(
        Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).all(),
        latest_saved_by_form,
    )
    return render_template(
        'mobile_packet_review.html',
        mobile_header_kicker='Packet Review',
        mobile_header_note='Step 8 of 9 / Review',
        mobile_incident_boot=True,
        mobile_incident_page='packet-review',
        mobile_forms_catalog=forms_catalog,
        **_shell_context('Packet Review', 'incident'),
    )


@bp.route('/mobile/incident/send-packet')
@login_required
def send_packet():
    recipient, cc_list = _packet_recipient_context()
    latest_saved_by_form = {}
    saved_rows = (
        SavedForm.query.filter_by(officer_user_id=current_user.id)
        .order_by(SavedForm.updated_at.desc())
        .all()
    )
    for row in saved_rows:
        latest_saved_by_form.setdefault(row.form_id, row)
    forms_catalog = build_mobile_form_catalog(
        Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).all(),
        latest_saved_by_form,
    )
    return render_template(
        'mobile_send_packet.html',
        mobile_header_kicker='Packet Delivery',
        mobile_header_note='Step 9 of 9 / Send',
        mobile_incident_boot=True,
        mobile_incident_page='send-packet',
        mobile_forms_catalog=forms_catalog,
        mobile_packet_recipient=recipient,
        mobile_packet_cc=cc_list,
        **_shell_context('Send Packet', 'incident'),
    )


@bp.route('/mobile/incident/success')
@login_required
def packet_success():
    return render_template(
        'mobile_success.html',
        mobile_header_kicker='Packet Delivery',
        mobile_header_note='Step 9 of 9 / Complete',
        mobile_incident_boot=True,
        mobile_incident_page='packet-success',
        **_shell_context('Packet Sent', 'incident'),
    )


@bp.route('/mobile/api/incident/send-packet', methods=['POST'])
@login_required
def send_packet_api():
    payload = request.get_json(silent=True) or {}
    state = payload.get('incident') if isinstance(payload.get('incident'), dict) else payload
    if not isinstance(state, dict):
        state = {}

    recipient, cc_list = _packet_recipient_context()
    recipient = recipient or _state_packet_email(state)
    form_entries = _packet_form_entries(state)
    validation = _packet_validation(state, form_entries, recipient)
    if validation['errors']:
        return (
            jsonify(
                {
                    'ok': False,
                    'errors': validation['errors'],
                    'warnings': validation['warnings'],
                    'recipient': recipient,
                    'ccList': cc_list,
                }
            ),
            400,
        )

    rendered_form_attachments = []
    render_errors = []
    for entry in form_entries:
        try:
            attachment = _render_saved_form_attachment(entry)
        except Exception as exc:
            render_errors.append({'field': entry['title'], 'message': f'Unable to render the saved form PDF for delivery: {exc}'})
            continue
        if attachment is not None:
            if _is_unfaithful_packet_render(entry, attachment):
                render_errors.append(
                    {
                        'field': entry['title'],
                        'message': 'This domestic supplemental packet still falls back to a non-faithful overlay export. Complete this delivery from the full forms workflow until XFA flattening is implemented.',
                    }
                )
                continue
            rendered_form_attachments.append(attachment)

    if render_errors:
        return (
            jsonify(
                {
                    'ok': False,
                    'errors': render_errors,
                    'warnings': validation['warnings'],
                    'recipient': recipient,
                    'ccList': cc_list,
                }
            ),
            400,
        )

    try:
        packet_pdf_bytes, packet_meta = build_packet_pdf(state, form_entries, rendered_form_attachments)
    except Exception as exc:
        return (
            jsonify(
                {
                    'ok': False,
                    'errors': [{'field': 'Packet Build', 'message': f'Unable to assemble the incident packet: {exc}'}],
                    'warnings': validation['warnings'],
                    'recipient': recipient,
                    'ccList': cc_list,
                }
            ),
            400,
        )
    attachments = [
        {
            'filename': 'mcpd-incident-packet.pdf',
            'content_type': 'application/pdf',
            'bytes': packet_pdf_bytes,
        }
    ]

    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    subject_tail = str(basics.get('summary') or basics.get('location') or 'Incident Packet').strip() or 'Incident Packet'
    subject = f'MCPD Mobile Packet - {subject_tail}'
    body = _build_packet_summary_text(state, form_entries)
    sent, info = _smtp_send_packet(recipient, cc_list, subject, body, attachments)
    if not sent:
        return (
            jsonify(
                {
                    'ok': False,
                    'errors': [{'field': 'Delivery', 'message': info}],
                    'warnings': validation['warnings'],
                    'recipient': recipient,
                    'ccList': cc_list,
                }
            ),
            500,
        )

    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action='mobile_packet_sent',
            details=f'forms={len(form_entries)}|statements={len(state.get("statements") or [])}|recipient={recipient}|attachments={len(attachments)}|packet_pages={packet_meta.get("page_count", 0)}',
        )
    )
    try:
        packet_record = IncidentPacket(
            officer_user_id=current_user.id,
            call_type=str(state.get('callType') or '')[:80],
            occurred_date=str(basics.get('occurredDate') or '')[:20],
            location=str(basics.get('location') or '')[:255],
            summary=str(basics.get('summary') or '')[:500],
            form_count=len(form_entries),
            statement_count=len(state.get('statements') or []),
            packet_json=json.dumps(state, default=str),
            validation_json=json.dumps(validation, default=str),
            approval_status=PACKET_APPROVAL_PENDING,
        )
        db.session.add(packet_record)
    except Exception:
        pass
    db.session.commit()
    return jsonify(
        {
            'ok': True,
            'recipient': recipient,
            'ccList': cc_list,
            'attachmentCount': len(attachments),
            'subject': subject,
        }
    )


# ── Supervisor / Command Routes ─────────────────────────────────────────────


def _supervisor_required_or_403():
    """Returns a 403 response if current_user cannot do supervisor review, else None."""
    from flask import abort
    if not can_supervisor_review(current_user):
        abort(403)


def _packet_review_context(packet: IncidentPacket) -> dict:
    """Build the full review context dict for a supervisor packet review template."""
    try:
        state = json.loads(packet.packet_json or '{}')
    except Exception:
        state = {}
    try:
        cached_validation = json.loads(packet.validation_json or '{}')
    except Exception:
        cached_validation = {}

    basics = state.get('incidentBasics') if isinstance(state.get('incidentBasics'), dict) else {}
    persons = state.get('persons') if isinstance(state.get('persons'), list) else []
    facts = state.get('facts') if isinstance(state.get('facts'), list) else []
    statements = state.get('statements') if isinstance(state.get('statements'), list) else []
    selected_forms = state.get('selectedForms') if isinstance(state.get('selectedForms'), list) else []
    narrative_text = str(state.get('narrative') or '').strip()
    narrative_approved = bool(state.get('narrativeApproved'))

    # Re-run narrative quality check
    nq = _narrative_quality_check(narrative_text)

    # Stat sheet check
    stat_sheet_present = any('stat sheet' in str(f).lower() or 'statsheet' in str(f).lower().replace(' ', '') for f in selected_forms)

    # Domestic supplement check
    domestic_present = any('domestic' in str(f).lower() for f in selected_forms)

    # Evidence check
    evidence_present = any('evidence' in str(f).lower() or 'property' in str(f).lower() or 'custody' in str(f).lower() for f in selected_forms)

    # Build structured section statuses
    sections = [
        {
            'label': 'Stat Sheet',
            'status': 'ok' if stat_sheet_present else 'error',
            'detail': 'Present' if stat_sheet_present else 'Missing — MCPD Stat Sheet is required.',
        },
        {
            'label': 'Incident Type',
            'status': 'ok' if state.get('callType') else 'error',
            'detail': str(state.get('callType') or 'Missing — call type not selected.'),
        },
        {
            'label': 'Location',
            'status': 'ok' if str(basics.get('location') or '').strip() else 'error',
            'detail': str(basics.get('location') or 'Missing — incident location not entered.'),
        },
        {
            'label': 'Date / Time',
            'status': 'ok' if (basics.get('occurredDate') and basics.get('occurredTime')) else 'error',
            'detail': f"{basics.get('occurredDate') or ''} {basics.get('occurredTime') or ''}".strip() or 'Missing — date/time not entered.',
        },
        {
            'label': 'Officer',
            'status': 'ok',
            'detail': str(packet.officer.display_name if packet.officer else 'Unknown'),
        },
        {
            'label': 'Narrative',
            'status': 'ok' if (narrative_text and narrative_approved) else ('warn' if narrative_text else 'error'),
            'detail': (
                f'Present and approved — {nq["word_count"]} words.'
                if (narrative_text and narrative_approved)
                else ('Written but not approved.' if narrative_text else 'Missing — narrative not written.')
            ),
        },
        {
            'label': 'Narrative Quality',
            'status': 'ok' if nq['ok'] else 'warn',
            'detail': '; '.join(nq['issues']) if nq['issues'] else f'{nq["word_count"]} words — looks adequate.',
        },
        {
            'label': 'Persons',
            'status': 'ok' if persons else 'error',
            'detail': f'{len(persons)} person(s) entered.' if persons else 'Missing — no persons entered.',
        },
        {
            'label': 'Statements',
            'status': 'ok' if (not statements or all(
                s.get('reviewedDraft') and s.get('signatureDataUrl') and s.get('initialsDataUrl')
                for s in statements if isinstance(s, dict)
            )) else 'warn',
            'detail': (
                f'{len(statements)} statement(s) — all complete.' if statements
                else 'No statements collected.'
            ),
        },
        {
            'label': 'Forms Selected',
            'status': 'ok' if selected_forms else 'error',
            'detail': ', '.join(str(f) for f in selected_forms) if selected_forms else 'No forms selected.',
        },
    ]

    if domestic_present:
        domestic_complete = any(
            'domestic' in str(f).lower() and 'supplement' in str(f).lower()
            for f in selected_forms
        )
        sections.append({
            'label': 'Domestic Supplement',
            'status': 'ok' if domestic_present else 'warn',
            'detail': 'Domestic supplement form is in packet.' if domestic_present else 'Domestic call type detected but supplement form not selected.',
        })

    if evidence_present:
        sections.append({
            'label': 'Evidence/Property',
            'status': 'ok',
            'detail': 'Evidence/property documentation is in packet.',
        })

    error_count = sum(1 for s in sections if s['status'] == 'error')
    warn_count = sum(1 for s in sections if s['status'] == 'warn')
    overall_status = 'READY' if error_count == 0 else 'NOT READY'

    return {
        'packet': packet,
        'state': state,
        'basics': basics,
        'persons': persons,
        'facts': facts,
        'statements': statements,
        'selected_forms': selected_forms,
        'narrative_text': narrative_text,
        'narrative_approved': narrative_approved,
        'narrative_quality': nq,
        'sections': sections,
        'error_count': error_count,
        'warn_count': warn_count,
        'overall_status': overall_status,
        'cached_validation': cached_validation,
    }


@bp.route('/mobile/supervisor/dashboard')
@login_required
def supervisor_dashboard():
    _supervisor_required_or_403()
    packets = (
        IncidentPacket.query
        .order_by(IncidentPacket.submitted_at.desc())
        .limit(60)
        .all()
    )
    pending = [p for p in packets if p.approval_status == PACKET_APPROVAL_PENDING]
    approved = [p for p in packets if p.approval_status == PACKET_APPROVAL_APPROVED]
    needs_correction = [p for p in packets if p.approval_status == PACKET_APPROVAL_NEEDS_CORRECTION]

    # Count common missing items from cached validation errors
    missing_counts: dict = {}
    for p in packets:
        try:
            val = json.loads(p.validation_json or '{}')
        except Exception:
            continue
        for err in val.get('errors', []):
            field = str(err.get('field') or 'Unknown')
            missing_counts[field] = missing_counts.get(field, 0) + 1
    top_missing = sorted(missing_counts.items(), key=lambda x: -x[1])[:6]

    # Insights: focus areas (top 3 error fields → focus area labels)
    focus_labels = {'Narrative': 'Narrative writing', 'Stat Sheet': 'Stat Sheet inclusion', 'Forms': 'Form completion',
                    'People': 'Persons documentation', 'Facts Capture': 'Facts capture', 'Statements': 'Statement collection'}
    focus_areas = [(focus_labels.get(field, field), count) for field, count in top_missing[:3]]

    # Officer-level pattern detection
    from collections import defaultdict
    officer_buckets: dict = defaultdict(list)
    for p in packets:
        officer_buckets[p.officer_user_id].append(p)

    officer_patterns = []
    for officer_id, o_packets in officer_buckets.items():
        if len(o_packets) < 2:
            continue
        o_missing: dict = {}
        o_word_counts: list = []
        for p in o_packets:
            try:
                val = json.loads(p.validation_json or '{}')
                for err in val.get('errors', []):
                    f = str(err.get('field') or 'Unknown')
                    o_missing[f] = o_missing.get(f, 0) + 1
            except Exception:
                pass
            try:
                st = json.loads(p.packet_json or '{}')
                n = str(st.get('narrative') or '').strip()
                if n:
                    o_word_counts.append(len(n.split()))
            except Exception:
                pass
        avg_wc = int(sum(o_word_counts) / len(o_word_counts)) if o_word_counts else 0
        flags = _compute_training_flags(o_missing, len(o_packets), avg_wc)
        if flags:
            officer = User.query.get(officer_id)
            if officer:
                officer_patterns.append({'officer': officer, 'packet_count': len(o_packets), 'flags': flags})

    return render_template(
        'mobile_supervisor_dashboard.html',
        mobile_header_kicker='Command Dashboard',
        mobile_header_note='Supervisor tools and packet review',
        mobile_incident_boot=False,
        mobile_incident_page='supervisor_dashboard',
        packets=packets,
        pending=pending,
        approved=approved,
        needs_correction=needs_correction,
        top_missing=top_missing,
        focus_areas=focus_areas,
        officer_patterns=officer_patterns,
        PACKET_APPROVAL_PENDING=PACKET_APPROVAL_PENDING,
        PACKET_APPROVAL_APPROVED=PACKET_APPROVAL_APPROVED,
        PACKET_APPROVAL_NEEDS_CORRECTION=PACKET_APPROVAL_NEEDS_CORRECTION,
        **_shell_context('Command Dashboard', 'home'),
    )


@bp.route('/mobile/supervisor/packet/<int:packet_id>')
@login_required
def supervisor_packet_review(packet_id):
    packet = IncidentPacket.query.get_or_404(packet_id)
    # Officer can view their own packet; supervisors can view any
    if packet.officer_user_id != current_user.id:
        _supervisor_required_or_403()
    ctx = _packet_review_context(packet)
    training_flags = []
    if can_supervisor_review(current_user):
        patterns = _officer_pattern_summary(packet.officer_user_id)
        training_flags = patterns.get('flags', [])
    return render_template(
        'mobile_supervisor_packet_review.html',
        mobile_header_kicker='Packet Review',
        mobile_header_note='Supervisor deficiency review',
        mobile_incident_boot=False,
        mobile_incident_page='supervisor_packet_review',
        is_supervisor=can_supervisor_review(current_user),
        training_flags=training_flags,
        **ctx,
        **_shell_context('Packet Review', 'home'),
    )


@bp.route('/mobile/api/supervisor/packet/<int:packet_id>/action', methods=['POST'])
@login_required
@_require_csrf
def supervisor_packet_action(packet_id):
    _supervisor_required_or_403()
    packet = IncidentPacket.query.get_or_404(packet_id)
    body = request.get_json(silent=True) or {}
    action = str(body.get('action') or '').strip().lower()
    notes = str(body.get('notes') or '').strip()[:2000]
    if action == 'approve':
        packet.approval_status = PACKET_APPROVAL_APPROVED
    elif action == 'needs_correction':
        packet.approval_status = PACKET_APPROVAL_NEEDS_CORRECTION
    else:
        return jsonify({'ok': False, 'error': 'Invalid action. Use "approve" or "needs_correction".'}), 400
    packet.reviewer_user_id = current_user.id
    packet.reviewed_at = utcnow_naive()
    if notes:
        packet.supervisor_notes = notes
    db.session.add(
        AuditLog(
            actor_id=current_user.id,
            action=f'supervisor_packet_{action}',
            details=f'packet_id={packet_id}|officer_id={packet.officer_user_id}|notes_len={len(notes)}',
        )
    )
    db.session.commit()
    return jsonify({'ok': True, 'approval_status': packet.approval_status})

