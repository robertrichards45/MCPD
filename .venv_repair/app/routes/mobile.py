import json
import os
import smtplib
from email.message import EmailMessage
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import AuditLog, Form, SavedForm
from ..services.call_type_rules import load_call_type_rules
from ..services.forms_pdf_renderer import inspect_xfa_fields, render_form_pdf
from ..services.mobile_incident_documents import build_narrative_draft, build_packet_pdf
from ..services.mobile_form_catalog import build_mobile_form_catalog

bp = Blueprint('mobile', __name__)

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
    forms_dir = _repo_root() / 'data' / 'uploads' / 'forms'
    matches = sorted(forms_dir.glob('*DOMESTIC*CHECKLIST*.pdf'))
    if not matches:
        return {'sections': []}
    info = inspect_xfa_fields(str(matches[0]))
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

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
    except Exception as exc:
        return False, str(exc)
    return True, 'sent'


@bp.route('/mobile/home')
@login_required
def home():
    action_cards = [
        {
            'title': 'Start New Incident',
            'href': url_for('mobile.incident_start'),
            'button_label': 'Start',
            'is_live': True,
        },
        {
            'title': 'Continue Incident',
            'href': url_for('mobile.incident_start'),
            'button_label': 'Continue',
            'is_live': True,
        },
        {
            'title': 'Laws / Orders',
            'href': url_for('legal.legal_home'),
            'button_label': 'Open',
            'is_live': True,
        },
        {
            'title': 'Quick Reference',
            'href': url_for('reference.incident_paperwork_guide'),
            'button_label': 'Open',
            'is_live': True,
        },
    ]
    return render_template(
        'mobile_home.html',
        mobile_header_kicker='Field Mobile',
        mobile_header_note=None,
        action_cards=action_cards,
        **_shell_context('Home', 'home'),
    )


@bp.route('/mobile/more')
@login_required
def more():
    return render_template(
        'mobile_more.html',
        mobile_header_kicker='Mobile Menu',
        mobile_header_note='More tools',
        **_shell_context('More', 'more'),
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

