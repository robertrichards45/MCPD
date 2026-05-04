import csv
import json
import io
import os
import re
import secrets
import smtplib
import time
import copy
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import quote

from flask import Blueprint, abort, after_this_request, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import AuditLog, Form, ROLE_DESK_SGT, ROLE_WATCH_COMMANDER, SavedForm, SavedFormAudit, User
from ..permissions import can_manage_site, can_view_user
from ..services.call_type_rules import load_call_type_rules, normalize_call_type_rule, save_call_type_rules, slugify_call_type, split_multivalue
from ..services.form_metadata_ai import category_options, choose_latest_form, detect_form_metadata_from_uploads, heuristic_metadata, normalize_form_family
from ..services.form_source_updates import check_and_update_form_source
from ..services.forms_pdf_renderer import (
    get_template_payload,
    inspect_pdf_fields,
    inspect_xfa_fields,
    render_form_pdf,
    save_template_payload,
    source_pdf_has_adobe_wait_shell,
    visible_input_keys_for_pdf,
)

bp = Blueprint('forms', __name__)

FORM_STATUSES = {'DRAFT', 'COMPLETED', 'SUBMITTED'}
RETENTION_MODES = {'no_pii_retention', 'temporary_pii_only', 'save_allowed', 'blank_template_only', 'full_save_allowed'}
TEMP_FORM_SESSION_KEY = 'forms_temp_payloads'
TEMP_FORM_TTL_SECONDS = 60 * 60
PERSON_ROLE_OPTIONS = ['Victim', 'Suspect', 'Complainant', 'Witness', 'Reporting Officer', 'Assisting Officer', 'Juvenile', 'Property Owner', 'Other']
FORM_LIBRARY_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.xlsm', '.csv', '.txt', '.rtf', '.json', '.xml', '.html', '.htm'}


def _get_or_404(model, object_id):
    obj = db.session.get(model, object_id)
    if obj is None:
        abort(404)
    return obj


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _field(name, label, field_type='text', required=False, placeholder=''):
    return {'name': name, 'label': label, 'type': field_type, 'required': bool(required), 'placeholder': placeholder or ''}


MCPD_STAT_SHEET_SCHEMA = {
    'id': 'mcpd_stat_sheet_v1',
    'title': 'MCPD Stat Sheet',
    'description': 'Daily/shift activity and operational statistics.',
    'sections': [
        {'id': 'reporting', 'title': 'Reporting Information', 'fields': [
            _field('report_date', 'Report Date', 'date', True),
            _field('report_period_start', 'Period Start', 'date', True),
            _field('report_period_end', 'Period End', 'date', True),
            _field('shift', 'Shift', 'text', True, 'Day / Swing / Midnight'),
            _field('watch_commander', 'Watch Commander'),
            _field('desk_sergeant', 'Desk Sergeant'),
            _field('reporting_officer', 'Reporting Officer', 'text', True),
            _field('badge_employee_id', 'Badge/Employee ID'),
            _field('unit_section', 'Unit / Section'),
        ]},
        {'id': 'activity_counts', 'title': 'Calls and Enforcement Totals', 'fields': [
            _field('calls_for_service', 'Calls for Service', 'number'),
            _field('traffic_stops', 'Traffic Stops', 'number'),
            _field('citations_written', 'Citations Written', 'number'),
            _field('warnings_written', 'Warnings Written', 'number'),
            _field('adult_arrests', 'Adult Arrests', 'number'),
            _field('juvenile_arrests', 'Juvenile Arrests', 'number'),
            _field('dui_arrests', 'DUI Arrests', 'number'),
            _field('domestic_calls', 'Domestic Calls', 'number'),
            _field('disturbance_calls', 'Disturbance Calls', 'number'),
            _field('incident_reports', 'Incident Reports', 'number'),
            _field('accident_reports', 'Accident Reports', 'number'),
            _field('field_interviews', 'Field Interviews', 'number'),
        ]},
        {'id': 'operations', 'title': 'Operational Activity', 'fields': [
            _field('gate_inspections', 'Gate Inspections', 'number'),
            _field('security_checks', 'Security Checks', 'number'),
            _field('foot_patrol_hours', 'Foot Patrol Hours', 'number'),
            _field('vehicle_patrol_hours', 'Vehicle Patrol Hours', 'number'),
            _field('speed_enforcement_hours', 'Speed Enforcement Hours', 'number'),
            _field('training_hours', 'Training Hours', 'number'),
            _field('community_contacts', 'Community Contacts', 'number'),
            _field('court_appearances', 'Court Appearances', 'number'),
            _field('overtime_hours', 'Overtime Hours', 'number'),
            _field('sick_leave_hours', 'Sick Leave Hours', 'number'),
        ]},
        {'id': 'property_evidence', 'title': 'Property and Evidence', 'fields': [
            _field('evidence_items_logged', 'Evidence Items Logged', 'number'),
            _field('impounds', 'Impounds', 'number'),
            _field('towed_vehicles', 'Towed Vehicles', 'number'),
            _field('recovered_property_cases', 'Recovered Property Cases', 'number'),
            _field('lost_found_reports', 'Lost/Found Reports', 'number'),
            _field('weapons_seized', 'Weapons Seized', 'number'),
            _field('narcotics_cases', 'Narcotics Cases', 'number'),
        ]},
        {'id': 'narrative', 'title': 'Narrative and Follow-Up', 'fields': [
            _field('notable_incidents', 'Notable Incidents', 'textarea'),
            _field('follow_up_required', 'Follow-Up Required', 'textarea'),
            _field('supervisor_notes', 'Supervisor Notes', 'textarea'),
        ]},
    ],
    'role_entry': {'title': 'People by Role', 'fields': [], 'role_options': PERSON_ROLE_OPTIONS},
}

GENERIC_SCHEMA = {
    'id': 'generic_form_v1',
    'title': 'General Form',
    'description': 'Structured form entry',
    'sections': [{'id': 'core', 'title': 'Core Details', 'fields': [
        _field('incident_date', 'Incident Date', 'date'),
        _field('location', 'Location'),
        _field('subject', 'Subject'),
        _field('summary', 'Summary', 'textarea'),
    ]}],
    'role_entry': {'title': 'People by Role', 'fields': [], 'role_options': PERSON_ROLE_OPTIONS},
}


def _humanize_field_name(name):
    text = (name or '').strip()
    if not text:
        return 'Field'
    # Purely numeric names (e.g. "1", "2", "3") from PDFs with unnamed fields
    if re.match(r'^[0-9]+$', text):
        return f'Field {text}'
    if text.isupper() and len(text) <= 12:
        return text
    text = text.replace('_', ' ').replace('-', ' ')
    text = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    text = ' '.join(text.split())
    if re.match(r'^[0-9]+[.)]\s+', text):
        return text
    return text.title()


def _normalize_compare_key(value):
    return ''.join(ch for ch in (value or '').lower() if ch.isalnum())


def _mapping_suggestions_for_schema(schema, source_fields):
    source_names = [item.get('name') for item in source_fields.get('fields', []) if isinstance(item, dict) and item.get('name')]
    schema_names = []
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            name = str(field.get('name') or '').strip()
            if name:
                schema_names.append(name)
    suggestions = {}
    normalized_source = {_normalize_compare_key(name): name for name in source_names}
    for key in schema_names:
        hit = normalized_source.get(_normalize_compare_key(key))
        if hit:
            suggestions[key] = hit
    return suggestions


def _checkbox_overrides_from_source(source_fields):
    overrides = {}
    for item in source_fields.get('fields', []):
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if not name:
            continue
        field_type = str(item.get('type') or '').strip()
        if field_type != '/Btn':
            continue
        # Most PDFs accept "Yes" for checked state; override can be refined per form later.
        overrides[name] = 'Yes'
    return overrides


def _sanitize_template_against_pdf(schema, source_fields, payload):
    source_names = {item.get('name') for item in source_fields.get('fields', []) if isinstance(item, dict) and item.get('name')}
    schema_names = {
        str(field.get('name') or '').strip()
        for section in schema.get('sections', [])
        for field in section.get('fields', [])
        if str(field.get('name') or '').strip()
    }
    if not source_names:
        return payload, {'removed_field_map': [], 'removed_ui_fields': [], 'removed_checkbox_overrides': []}

    template = payload if isinstance(payload, dict) else {}
    field_map = template.get('field_map') if isinstance(template.get('field_map'), dict) else {}
    ui_fields = template.get('ui_fields') if isinstance(template.get('ui_fields'), list) else []
    checkbox_overrides = template.get('checkbox_on_values') if isinstance(template.get('checkbox_on_values'), dict) else {}

    clean_field_map = {}
    removed_field_map = []
    for key, target in field_map.items():
        left = str(key or '').strip()
        right = str(target or '').strip()
        if not left or not right:
            continue
        if left not in schema_names:
            removed_field_map.append({'schema_field': left, 'reason': 'not_in_schema'})
            continue
        if right not in source_names:
            removed_field_map.append({'schema_field': left, 'pdf_field': right, 'reason': 'pdf_field_missing'})
            continue
        clean_field_map[left] = right

    clean_ui_fields = []
    removed_ui_fields = []
    for item in ui_fields:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if not name:
            continue
        if name not in schema_names:
            removed_ui_fields.append({'name': name, 'reason': 'not_in_schema'})
            continue
        target = clean_field_map.get(name, name)
        if target not in source_names:
            removed_ui_fields.append({'name': name, 'pdf_target': target, 'reason': 'pdf_field_missing'})
            continue
        clean_ui_fields.append(item)

    clean_checkbox = {}
    removed_checkbox = []
    for key, value in checkbox_overrides.items():
        name = str(key or '').strip()
        if not name:
            continue
        if name not in source_names:
            removed_checkbox.append({'field': name, 'reason': 'pdf_field_missing'})
            continue
        clean_checkbox[name] = str(value or '').strip() or 'Yes'

    cleaned = dict(template)
    cleaned['field_map'] = clean_field_map
    cleaned['ui_fields'] = clean_ui_fields
    cleaned['checkbox_on_values'] = clean_checkbox
    return cleaned, {
        'removed_field_map': removed_field_map,
        'removed_ui_fields': removed_ui_fields,
        'removed_checkbox_overrides': removed_checkbox,
    }


def _pdf_field_type_to_ui(pdf_type):
    raw = (pdf_type or '').strip()
    if raw == '/Btn':
        return 'checkbox'
    if raw == '/Tx':
        return 'text'
    if raw == '/Ch':
        return 'select'
    if raw == '/Sig':
        return 'signature'
    if raw in {'checkbox', 'text', 'select', 'date', 'signature'}:
        return raw
    return 'text'


def _pdf_field_label(source_item):
    label = str(source_item.get('label') or '').strip()
    raw_name = str(source_item.get('raw_name') or source_item.get('name') or '').strip()
    if label and _normalize_compare_key(label) != _normalize_compare_key(raw_name):
        return label.rstrip(':')
    return _humanize_field_name(raw_name)


def _pdf_field_ui_type(source_item):
    name = str(source_item.get('raw_name') or source_item.get('name') or '').strip().lower()
    label = _pdf_field_label(source_item).lower()
    base_type = _pdf_field_type_to_ui(source_item.get('type'))
    combined = f'{name} {label}'
    if any(token in combined for token in ('describe', 'statement', 'utterance', 'explain', 'details', 'remarks', 'notes')):
        return 'textarea'
    if base_type == 'signature' or 'signature' in combined:
        return 'signature'
    if any(token in combined for token in ('initial', 'initials', 'supinit')):
        return 'initial'
    return base_type


def _validate_payload_for_completion(schema, payload):
    """Return {'errors': [...], 'warnings': [...]} for required and signature fields."""
    errors = []
    warnings = []
    values = payload.get('values', {}) if isinstance(payload.get('values'), dict) else {}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            name = str(field.get('name') or '').strip()
            label = str(field.get('label') or name or 'Field').strip()
            value = str(values.get(name) or '').strip()
            field_type = str(field.get('type') or 'text').strip()
            if field.get('required') and not value:
                errors.append({'field': label, 'message': f'{label} is required and is missing.'})
            elif field_type in ('signature', 'initial') and not value:
                warnings.append({'field': label, 'message': f'{label} has not been captured. Draw a signature before finalizing.'})
    return {'errors': errors, 'warnings': warnings}


def _build_section_fields(source_items):
    fields = []
    for item in source_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if not name:
            continue
        fields.append(
            _field(
                name,
                _pdf_field_label(item),
                _pdf_field_ui_type(item),
                required=False,
                placeholder='',
            )
        )
    return fields


def _domestic_supplemental_sections(pdf_fields, visible_keys):
    ordered_fields = [
        item for item in pdf_fields
        if isinstance(item, dict) and str(item.get('name') or '').strip() in visible_keys
    ]
    if not ordered_fields:
        return []

    section_specs = [
        ('dispatch_and_parties', 'Dispatch And Parties', 'SupInitial.1'),
        ('victim_condition_and_statements', 'Victim Condition And Statements', 'SupInitial.2'),
        ('suspect_condition_and_statements', 'Suspect Condition And Statements', 'Angry1'),
        ('scene_relationship_and_prior_violence', 'Scene, Relationship, And Prior Violence', 'FQ'),
        ('witnesses_evidence_and_victim_services', 'Witnesses, Evidence, And Victim Services', 'SupInitial.4'),
        ('medical_response_and_injury_documentation', 'Medical Response And Injury Documentation', 'SupInitial.7'),
    ]

    index_by_raw_name = {}
    for index, item in enumerate(ordered_fields):
        raw_name = str(item.get('raw_name') or '').strip()
        if raw_name and raw_name not in index_by_raw_name:
            index_by_raw_name[raw_name] = index

    boundaries = []
    for section_id, title, raw_name in section_specs:
        start_index = index_by_raw_name.get(raw_name)
        if start_index is None:
            continue
        boundaries.append((section_id, title, start_index))
    if not boundaries:
        return []

    boundaries.sort(key=lambda item: item[2])
    sections = []
    for index, (section_id, title, start_index) in enumerate(boundaries):
        next_start = boundaries[index + 1][2] if index + 1 < len(boundaries) else len(ordered_fields)
        fields = _build_section_fields(ordered_fields[start_index:next_start])
        if fields:
            sections.append({'id': section_id, 'title': title, 'fields': fields})
    return sections


def _schema_from_pdf_fields(form, base_schema, source_pdf):
    try:
        info = inspect_pdf_fields(source_pdf) if source_pdf else {'fields': []}
        pdf_fields = info.get('fields') if isinstance(info.get('fields'), list) else []
    except Exception:
        pdf_fields = []
    if not pdf_fields and source_pdf:
        try:
            info = inspect_xfa_fields(source_pdf)
            pdf_fields = info.get('fields') if isinstance(info.get('fields'), list) else []
        except Exception:
            pdf_fields = []
    visible_keys = set(visible_input_keys_for_pdf(base_schema.get('id') or '', source_pdf))
    if not visible_keys:
        base_schema['sections'] = []
        base_schema['show_role_entry'] = False
        base_schema['show_notes'] = False
        base_schema['pdf_source_warning'] = 'No PDF-backed visible fields are configured for this form.'
        return base_schema

    title_key = _normalize_compare_key(getattr(form, 'title', ''))
    if 'domesticviolence' in title_key and any(str(item.get('raw_name') or '').strip() for item in pdf_fields if isinstance(item, dict)):
        domestic_visible_keys = {
            str(item.get('name') or '').strip()
            for item in pdf_fields
            if isinstance(item, dict) and str(item.get('name') or '').strip()
        }
        domestic_sections = _domestic_supplemental_sections(pdf_fields, domestic_visible_keys)
        if domestic_sections:
            base_schema['sections'] = domestic_sections
            base_schema['show_role_entry'] = False
            base_schema['show_notes'] = False
            return base_schema

    template_payload = get_template_payload(base_schema.get('id') or '')
    ui_fields = template_payload.get('ui_fields') if isinstance(template_payload.get('ui_fields'), list) else []
    pdf_field_names = {
        str(item.get('name') or '').strip()
        for item in pdf_fields
        if isinstance(item, dict) and str(item.get('name') or '').strip()
    }
    source_exists = bool(source_pdf and os.path.exists(source_pdf))
    mapped_targets = {
        str(template_payload.get('field_map', {}).get(str(item.get('name') or '').strip()) or str(item.get('name') or '').strip()).strip()
        for item in ui_fields
        if isinstance(item, dict) and str(item.get('name') or '').strip()
    }
    matched_targets = {name for name in mapped_targets if name in pdf_field_names}
    prefer_exact_pdf_schema = bool(
        source_exists
        and pdf_field_names
        and (
            not ui_fields
            or len(pdf_field_names) > max(len(matched_targets) + 12, int(max(len(matched_targets), 1) * 1.5))
        )
    )
    if prefer_exact_pdf_schema:
        visible_keys = set(pdf_field_names)
    known_names = set()
    sections = []
    if ui_fields and not prefer_exact_pdf_schema:
        ordered_sections = {}
        for item in ui_fields:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name') or '').strip()
            if not name or name not in visible_keys:
                continue
            section_title = str(item.get('section') or 'Form Fields').strip() or 'Form Fields'
            section_id = _normalize_compare_key(section_title) or 'form_fields'
            ordered_sections.setdefault(section_id, {'id': section_id, 'title': section_title, 'fields': []})
            ordered_sections[section_id]['fields'].append(
                _field(
                    name,
                    str(item.get('label') or _humanize_field_name(name)).strip(),
                    str(item.get('type') or 'text').strip() or 'text',
                    bool(item.get('required')),
                    str(item.get('placeholder') or '').strip(),
                )
            )
        if ordered_sections:
            sections.extend(list(ordered_sections.values()))
            known_names.update(
                field.get('name')
                for section in ordered_sections.values()
                for field in section.get('fields', [])
                if field.get('name')
            )

    # Keep existing sections for known fields, then append only allowed inferred keys.
    for section in ([] if prefer_exact_pdf_schema else base_schema.get('sections', [])):
        kept = []
        for field in section.get('fields', []):
            if field.get('name') in visible_keys and field.get('name') not in known_names:
                kept.append(field)
                known_names.add(field.get('name'))
        if kept:
            sections.append({'id': section.get('id'), 'title': section.get('title'), 'fields': kept})

    ordered_visible_keys = [
        str(item.get('name') or '').strip()
        for item in pdf_fields
        if isinstance(item, dict)
        and str(item.get('name') or '').strip() in visible_keys
        and str(item.get('name') or '').strip() not in known_names
    ]
    for key in sorted(visible_keys):
        if key not in known_names and key not in ordered_visible_keys:
            ordered_visible_keys.append(key)

    inferred = []
    for key in ordered_visible_keys:
        if key in known_names:
            continue
        inferred_type = 'text'
        for item in pdf_fields:
            if not isinstance(item, dict):
                continue
            if str(item.get('name') or '').strip() == key:
                inferred_type = _pdf_field_ui_type(item)
                break
        inferred.append(
            _field(
                key,
                _pdf_field_label(next((item for item in pdf_fields if isinstance(item, dict) and str(item.get('name') or '').strip() == key), {'name': key})),
                inferred_type,
                required=False,
                placeholder='',
            )
        )
        known_names.add(key)

    if inferred:
        sections.append({'id': 'pdf_fields', 'title': 'Form Fields', 'fields': inferred})

    if not sections:
        return base_schema

    base_schema['sections'] = sections
    role_keys = {
        'role_1', 'role_2', 'role_3', 'role_4',
        'role_name_1', 'role_name_2', 'role_name_3', 'role_name_4',
        'role_identifier_1', 'role_identifier_2', 'role_identifier_3', 'role_identifier_4',
        'role_phone_1', 'role_phone_2', 'role_phone_3', 'role_phone_4',
        'role_vehicle_1', 'role_vehicle_2', 'role_vehicle_3', 'role_vehicle_4',
        'role_notes_1', 'role_notes_2', 'role_notes_3', 'role_notes_4',
    }
    base_schema['show_role_entry'] = bool(base_schema.get('role_entry')) and bool(visible_keys & role_keys)
    base_schema['show_notes'] = 'general_notes' in visible_keys or 'notes' in visible_keys
    return base_schema


def require_admin():
    if not can_manage_site(current_user):
        abort(403)


def _can_manage_form_maintenance(user):
    return bool(
        user
        and getattr(user, 'is_authenticated', False)
        and user.has_any_role('WEBSITE_CONTROLLER', ROLE_WATCH_COMMANDER, ROLE_DESK_SGT)
    )


def _require_form_maintenance():
    if not _can_manage_form_maintenance(current_user):
        abort(403)


def _repo_root():
    return os.path.abspath(os.path.join(current_app.root_path, '..'))


def _resolve_storage_path(path):
    candidate = (path or '').strip()
    if not candidate:
        return ''
    if os.path.isabs(candidate):
        return os.path.abspath(candidate)
    normalized = candidate.replace('/', os.sep).replace('\\', os.sep).lstrip('.\\/')
    return os.path.abspath(os.path.join(_repo_root(), normalized))


def _recovered_source_name(filename):
    raw_name = os.path.basename(filename or '')
    return re.sub(r'^\d{9,}-\d+-', '', raw_name)


def _sync_forms_from_storage():
    save_dir = _resolve_storage_path(current_app.config.get('FORMS_UPLOAD'))
    if not save_dir or not os.path.isdir(save_dir):
        return 0

    existing_paths = set()
    for form in Form.query.all():
        resolved = _resolve_storage_path(getattr(form, 'file_path', ''))
        if resolved:
            existing_paths.add(os.path.normcase(os.path.abspath(resolved)))

    uploaded_by = current_user.id if getattr(current_user, 'is_authenticated', False) else None
    imported = []
    for entry in sorted(os.scandir(save_dir), key=lambda item: item.stat().st_mtime):
        if not entry.is_file():
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext and ext not in FORM_LIBRARY_EXTENSIONS:
            continue
        normalized_path = os.path.normcase(os.path.abspath(entry.path))
        if normalized_path in existing_paths:
            continue

        detected = heuristic_metadata(_recovered_source_name(entry.name))
        uploaded_at = datetime.utcfromtimestamp(entry.stat().st_mtime)
        form = Form(
            title=detected['title'],
            category=detected['category'],
            version_label=detected['version_label'],
            file_path=os.path.abspath(entry.path),
            uploaded_by=uploaded_by,
            uploaded_at=uploaded_at,
            contains_pii=False,
            retention_mode='full_save_allowed',
            allow_email=True,
            allow_download=True,
            allow_completed_save=True,
            allow_blank_print=True,
            is_active=True,
        )
        db.session.add(form)
        db.session.flush()
        imported.append(form)
        existing_paths.add(normalized_path)

    if not imported:
        return 0

    family_groups = {}
    for form in Form.query.order_by(Form.uploaded_at.desc(), Form.id.desc()).all():
        family = normalize_form_family(form.title)
        if not family:
            continue
        family_groups.setdefault(family, []).append(form)

    for forms_in_family in family_groups.values():
        latest = choose_latest_form(forms_in_family, api_key='')
        latest_id = latest.id if latest else None
        for form in forms_in_family:
            form.is_active = (form.id == latest_id) if latest_id else True

    details = f"Recovered {len(imported)} form file(s) from storage."
    db.session.add(AuditLog(actor_id=uploaded_by, action='forms_storage_recovery', details=details))
    db.session.commit()
    return len(imported)


def _load_saved_form_data(raw_value):
    try:
        parsed = json.loads(raw_value or '{}')
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _schema_for_form(form):
    title = (form.title or '').strip().lower()
    if 'stat' in title and ('sheet' in title or 'mcpd' in title):
        base = copy.deepcopy(MCPD_STAT_SHEET_SCHEMA)
    else:
        base = copy.deepcopy(GENERIC_SCHEMA)
    if getattr(form, 'title', None):
        base['title'] = str(form.title).strip()

    source_pdf = _pdf_source_for_form(form)
    schema = _schema_from_pdf_fields(form, base, source_pdf)
    if 'show_role_entry' not in schema:
        schema['show_role_entry'] = False
    if 'show_notes' not in schema:
        schema['show_notes'] = False
    return schema


def _form_fill_state(form, schema):
    has_visible_fields = any(section.get('fields') for section in schema.get('sections', []))
    source_pdf = _pdf_source_for_form(form)
    has_blank_source = bool(source_pdf and os.path.exists(source_pdf))
    if has_visible_fields:
        return {
            'is_ready': True,
            'fallback_message': '',
            'has_blank_source': has_blank_source,
            'source_of_truth_label': 'Actual PDF-backed form workflow',
        }
    return {
        'is_ready': False,
        'fallback_message': 'This form is not yet available for online completion. You can still print or download the blank form.',
        'has_blank_source': has_blank_source,
        'source_of_truth_label': 'Blank PDF available only',
    }


def _form_policy(form):
    retention_mode = (form.retention_mode or 'full_save_allowed').strip().lower()
    title_hint = (getattr(form, 'title', None) or '').strip().lower()
    if retention_mode == 'full_save_allowed' and 'stat' in title_hint and 'sheet' in title_hint:
        retention_mode = 'no_pii_retention'
    if retention_mode not in RETENTION_MODES:
        retention_mode = 'full_save_allowed'
    allow_completed_save = bool(form.allow_completed_save)
    if retention_mode in {'no_pii_retention', 'temporary_pii_only', 'blank_template_only'}:
        allow_completed_save = False
    return {
        'contains_pii': bool(form.contains_pii),
        'retention_mode': retention_mode,
        'allow_email': bool(form.allow_email) and retention_mode != 'blank_template_only',
        'allow_download': bool(form.allow_download) and retention_mode != 'blank_template_only',
        'allow_completed_save': allow_completed_save,
        'allow_blank_print': bool(form.allow_blank_print),
        'is_no_retention': retention_mode in {'no_pii_retention', 'temporary_pii_only'},
        'is_blank_only': retention_mode == 'blank_template_only',
    }


def _empty_payload(schema):
    values = {}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            values[field['name']] = ''
    return {'schema_id': schema['id'], 'values': values, 'role_entries': [], 'notes': ''}


def _normalize_payload(payload, schema):
    baseline = _empty_payload(schema)
    if not payload:
        return baseline
    if isinstance(payload.get('values'), dict):
        for key, value in payload['values'].items():
            if key in baseline['values']:
                baseline['values'][key] = str(value or '').strip()
        rows = payload.get('role_entries') if isinstance(payload.get('role_entries'), list) else []
        clean = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            clean.append({
                'role': str(row.get('role') or '').strip(),
                'full_name': str(row.get('full_name') or '').strip(),
                'identifier': str(row.get('identifier') or '').strip(),
                'phone': str(row.get('phone') or '').strip(),
                'vehicle': str(row.get('vehicle') or '').strip(),
                'notes': str(row.get('notes') or '').strip(),
            })
        baseline['role_entries'] = clean
        baseline['notes'] = str(payload.get('notes') or '').strip()
        return baseline
    legacy_fields = payload.get('fields') if isinstance(payload.get('fields'), list) else []
    label_to_key = {}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            label_to_key[field['label'].strip().lower()] = field['name']
    for item in legacy_fields:
        if not isinstance(item, dict):
            continue
        mapped = label_to_key.get(str(item.get('key') or '').strip().lower())
        if mapped:
            baseline['values'][mapped] = str(item.get('value') or '').strip()
    baseline['notes'] = str(payload.get('notes') or '').strip()
    return baseline


def _parse_submission_payload(schema):
    payload = _empty_payload(schema)
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            field_name = field['name']
            if field.get('type') == 'checkbox':
                payload['values'][field_name] = 'Yes' if request.form.get(f"field_{field_name}") else ''
            else:
                payload['values'][field_name] = (request.form.get(f"field_{field_name}") or '').strip()
    if schema.get('show_role_entry'):
        role_values = request.form.getlist('role_entry_role')
        name_values = request.form.getlist('role_entry_name')
        id_values = request.form.getlist('role_entry_identifier')
        phone_values = request.form.getlist('role_entry_phone')
        vehicle_values = request.form.getlist('role_entry_vehicle')
        notes_values = request.form.getlist('role_entry_notes')
        rows = []
        for idx, role in enumerate(role_values):
            row = {
                'role': (role or '').strip(),
                'full_name': (name_values[idx] if idx < len(name_values) else '').strip(),
                'identifier': (id_values[idx] if idx < len(id_values) else '').strip(),
                'phone': (phone_values[idx] if idx < len(phone_values) else '').strip(),
                'vehicle': (vehicle_values[idx] if idx < len(vehicle_values) else '').strip(),
                'notes': (notes_values[idx] if idx < len(notes_values) else '').strip(),
            }
            if any(row.values()):
                rows.append(row)
        payload['role_entries'] = rows
    else:
        payload['role_entries'] = []
    payload['notes'] = (request.form.get('notes') or '').strip() if schema.get('show_notes') else ''
    return payload


def _clean_scan_value(value):
    return ' '.join(str(value or '').replace('\x00', ' ').split()).strip()


def _parse_aamva_date(value):
    raw = re.sub(r'[^0-9]', '', str(value or ''))
    if len(raw) != 8:
        return ''
    if raw.startswith(('19', '20')):
        return f'{raw[0:4]}-{raw[4:6]}-{raw[6:8]}'
    return f'{raw[4:8]}-{raw[0:2]}-{raw[2:4]}'


def _parse_id_scan_payload(raw_payload):
    raw = str(raw_payload or '').strip()
    if not raw:
        return {}
    tags = {}
    for line in raw.replace('\r', '\n').split('\n'):
        line = line.strip()
        if len(line) >= 4 and re.match(r'^[A-Z0-9]{3}', line[:3]):
            code = line[:3]
            value = _clean_scan_value(line[3:])
            if value and code not in tags:
                tags[code] = value
    full_name = _clean_scan_value(' '.join(part for part in (tags.get('DAC', ''), tags.get('DAD', ''), tags.get('DCS', '')) if part))
    data = {
        'first_name': tags.get('DAC', ''),
        'middle_name': tags.get('DAD', ''),
        'last_name': tags.get('DCS', ''),
        'full_name': full_name,
        'date_of_birth': _parse_aamva_date(tags.get('DBB', '')),
        'license_number': tags.get('DAQ', ''),
        'issuing_state': tags.get('DAJ', ''),
        'address': tags.get('DAG', ''),
        'city': tags.get('DAI', ''),
        'state': tags.get('DAJ', ''),
        'zip': tags.get('DAK', ''),
        'sex': tags.get('DBC', ''),
        'height': tags.get('DAU', ''),
        'eye_color': tags.get('DAY', ''),
        'hair_color': tags.get('DAZ', ''),
        'expiration_date': _parse_aamva_date(tags.get('DBA', '')),
    }
    return data if any(data.values()) else {}


def _field_match_score(field_name, field_label, aliases):
    field_name = (field_name or '').lower()
    field_label = (field_label or '').lower()
    haystack = f'{field_name} {field_label}'
    score = 0
    for alias in aliases:
        alias_lower = alias.lower()
        if field_name == alias_lower:
            score = max(score, 100)
        elif field_label == alias_lower:
            score = max(score, 96)
        elif alias_lower in haystack:
            score = max(score, 70 + len(alias_lower))
    return score


def _apply_id_scan_to_payload(schema, payload, scan_data, replace_existing=False):
    updated = copy.deepcopy(payload if isinstance(payload, dict) else _empty_payload(schema))
    values = updated.setdefault('values', {})
    imported = []
    skipped = []
    field_aliases = {
        'first_name': ('first name', 'firstname', 'given name'),
        'middle_name': ('middle name', 'middlename', 'middle initial'),
        'last_name': ('last name', 'lastname', 'surname', 'family name'),
        'full_name': ('full name', 'name', 'subject name', 'person name'),
        'date_of_birth': ('date of birth', 'dob', 'birth date'),
        'license_number': ('driver license', 'driver license number', 'license number', 'drivers license', 'id number', 'identifier'),
        'issuing_state': ('issuing state', 'license state'),
        'address': ('address', 'street address'),
        'city': ('city',),
        'state': ('state', 'address state'),
        'zip': ('zip', 'zip code', 'postal code'),
        'sex': ('sex', 'gender'),
        'height': ('height',),
        'eye_color': ('eye color', 'eyes'),
        'hair_color': ('hair color', 'hair'),
        'expiration_date': ('expiration date', 'exp date', 'expires'),
    }
    form_fields = [
        (str(field.get('name') or '').strip(), str(field.get('label') or '').strip())
        for section in schema.get('sections', [])
        for field in section.get('fields', [])
    ]

    def _set_value(field_name, value, label):
        clean_value = _clean_scan_value(value)
        current = _clean_scan_value(values.get(field_name, ''))
        if not clean_value:
            return
        if current and not replace_existing:
            skipped.append(label)
            return
        values[field_name] = clean_value
        imported.append(label)

    for key, raw_value in scan_data.items():
        aliases = field_aliases.get(key, ())
        if not aliases or not _clean_scan_value(raw_value):
            continue
        best_field = ''
        best_score = 0
        for field_name, field_label in form_fields:
            score = _field_match_score(field_name, field_label, aliases)
            if score > best_score:
                best_score = score
                best_field = field_name
        if best_field and best_score >= 75:
            _set_value(best_field, raw_value, best_field)

    if schema.get('show_role_entry'):
        rows = updated.setdefault('role_entries', [])
        target = rows[0] if rows else {'role': '', 'full_name': '', 'identifier': '', 'phone': '', 'vehicle': '', 'notes': ''}
        if not rows:
            rows.append(target)
        if scan_data.get('full_name'):
            current_name = _clean_scan_value(target.get('full_name'))
            if not current_name or replace_existing:
                target['full_name'] = scan_data['full_name']
                imported.append('role full_name')
            else:
                skipped.append('role full_name')
        if scan_data.get('license_number'):
            current_identifier = _clean_scan_value(target.get('identifier'))
            if not current_identifier or replace_existing:
                identifier = scan_data['license_number']
                if scan_data.get('issuing_state'):
                    identifier = f"{identifier} ({scan_data['issuing_state']})"
                target['identifier'] = identifier
                imported.append('role identifier')
            else:
                skipped.append('role identifier')

    return updated, {
        'imported': list(dict.fromkeys(imported)),
        'skipped': list(dict.fromkeys(skipped)),
        'parsed': scan_data,
    }


def _scan_supported(schema):
    supported_tokens = (
        'name',
        'dob',
        'birth',
        'license',
        'identifier',
        'address',
        'city',
        'state',
        'zip',
        'sex',
        'height',
        'eye',
        'hair',
        'subject',
        'driver',
        'owner',
        'operator',
        'person',
        'victim',
        'witness',
        'suspect',
    )
    text_like_fields = 0
    for section in schema.get('sections', []):
        section_title = str(section.get('title') or '').lower()
        if any(token in section_title for token in ('person', 'subject', 'driver', 'owner', 'operator', 'party')):
            return True
        for field in section.get('fields', []):
            haystack = f"{field.get('name', '')} {field.get('label', '')}".lower()
            if any(token in haystack for token in supported_tokens):
                return True
            if str(field.get('type') or 'text').lower() in {'text', 'date', 'textarea'}:
                text_like_fields += 1
    if text_like_fields >= 4:
        return True
    return bool(schema.get('show_role_entry'))


def _allowed_submission_keys(schema):
    allowed = {'action', 'saved_title', 'scan_payload', 'scan_replace_existing'}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            name = str(field.get('name') or '').strip()
            if not name:
                continue
            allowed.add(f'field_{name}')
    if schema.get('show_role_entry'):
        allowed.update({
            'role_entry_role',
            'role_entry_name',
            'role_entry_identifier',
            'role_entry_phone',
            'role_entry_vehicle',
            'role_entry_notes',
        })
    if schema.get('show_notes'):
        allowed.add('notes')
    return allowed


def _unexpected_submission_keys(schema):
    allowed = _allowed_submission_keys(schema)
    return sorted({key for key in request.form.keys() if key not in allowed})


def _flat_export_fields(schema, payload):
    rows = []
    for section in schema.get('sections', []):
        rows.append({'key': f"[{section['title']}]", 'value': ''})
        for field in section.get('fields', []):
            rows.append({'key': field['label'], 'value': str(payload.get('values', {}).get(field['name']) or '').strip()})
    role_entries = payload.get('role_entries') if isinstance(payload.get('role_entries'), list) else []
    if role_entries:
        rows.append({'key': '[People by Role]', 'value': ''})
        for idx, row in enumerate(role_entries, start=1):
            rows.extend([
                {'key': f'Role {idx}', 'value': str(row.get('role') or '')},
                {'key': f'Name {idx}', 'value': str(row.get('full_name') or '')},
                {'key': f'Identifier {idx}', 'value': str(row.get('identifier') or '')},
                {'key': f'Phone {idx}', 'value': str(row.get('phone') or '')},
                {'key': f'Vehicle {idx}', 'value': str(row.get('vehicle') or '')},
                {'key': f'Notes {idx}', 'value': str(row.get('notes') or '')},
            ])
    if payload.get('notes'):
        rows.append({'key': '[Notes]', 'value': payload['notes']})
    return rows


def _print_value(raw_value, blank_mode=False):
    if blank_mode:
        return ''
    value = str(raw_value or '').strip()
    return value if value else 'N/A'


def _build_preview_sections(schema, payload, blank_mode=False):
    sections = []
    for section in schema.get('sections', []):
        rows = []
        for field in section.get('fields', []):
            field_type = field.get('type', 'text')
            raw = payload.get('values', {}).get(field['name'])
            if field_type == 'checkbox':
                value = '' if blank_mode else ('X' if str(raw or '').strip().lower() in {'yes', 'true', '1', 'on', 'x'} else '')
            else:
                value = _print_value(raw, blank_mode)
            rows.append({'label': field['label'], 'value': value, 'type': field_type})
        sections.append({'title': section['title'], 'rows': rows})
    role_rows = []
    for entry in payload.get('role_entries', []):
        role_rows.append({
            'role': _print_value(entry.get('role'), blank_mode),
            'full_name': _print_value(entry.get('full_name'), blank_mode),
            'identifier': _print_value(entry.get('identifier'), blank_mode),
            'phone': _print_value(entry.get('phone'), blank_mode),
            'vehicle': _print_value(entry.get('vehicle'), blank_mode),
            'notes': _print_value(entry.get('notes'), blank_mode),
        })
    if blank_mode and not role_rows:
        role_rows = [{'role': '', 'full_name': '', 'identifier': '', 'phone': '', 'vehicle': '', 'notes': ''}]
    return sections, role_rows


def _safe_display_dt(value):
    if not value:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S ET')


def _can_view_saved_form(record):
    if record.officer_user_id == current_user.id:
        return True
    owner = db.session.get(User, record.officer_user_id)
    return bool(owner and can_view_user(current_user, owner))


def _can_edit_saved_form(record):
    return can_manage_site(current_user) or record.officer_user_id == current_user.id


def _save_audit(saved_form_id, action, details):
    db.session.add(SavedFormAudit(saved_form_id=saved_form_id, actor_user_id=current_user.id, action=action, details=details))


def _clean_email(value):
    return (value or '').strip()


def _cc_recipients():
    recipients = []
    for user in User.query.filter(User.active.is_(True)).all():
        email = _clean_email(user.email)
        if email and user.has_any_role(ROLE_WATCH_COMMANDER, ROLE_DESK_SGT):
            recipients.append(email)
    ordered, seen = [], set()
    for item in recipients:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _email_recipients_for_current_user():
    primary = _clean_email(current_user.email)
    if not primary:
        return '', []
    return primary, [email for email in _cc_recipients() if email.lower() != primary.lower()]


def _smtp_send(recipient, cc_list, subject, body, attachment_name=None, attachment_bytes=None):
    host = os.environ.get('SMTP_HOST', '').strip()
    sender = os.environ.get('SMTP_FROM', '').strip()
    if not host or not sender:
        return False, 'SMTP not configured.'
    port = int(os.environ.get('SMTP_PORT', '587') or '587')
    username = os.environ.get('SMTP_USERNAME', '').strip()
    password = os.environ.get('SMTP_PASSWORD', '').strip()
    use_tls = os.environ.get('SMTP_USE_TLS', '1').strip().lower() in {'1', 'true', 'yes', 'on'}
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)
    msg.set_content(body)
    if attachment_name and attachment_bytes:
        msg.add_attachment(
            attachment_bytes,
            maintype='application',
            subtype='pdf',
            filename=attachment_name,
        )
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg, to_addrs=[recipient] + list(cc_list or []))
    return True, 'sent'


def _determine_status(action_name, fallback='DRAFT'):
    action = (action_name or '').strip().lower()
    if action == 'save_completed':
        return 'COMPLETED'
    if action == 'submit_form':
        return 'SUBMITTED'
    return fallback if fallback in FORM_STATUSES else 'DRAFT'


def _pdf_source_for_form(form):
    file_path = _resolve_storage_path(getattr(form, 'file_path', None))
    if not file_path or not os.path.exists(file_path):
        return None
    if os.path.splitext(file_path)[1].lower() != '.pdf':
        return None
    return file_path


def _send_ephemeral_file(path, download_name):
    @after_this_request
    def _cleanup(response):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        return response
    response = send_file(path, as_attachment=True, download_name=download_name, mimetype='application/pdf')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _preview_pdf_filename(form, blank_mode=False):
    suffix = 'blank' if blank_mode else 'completed'
    return f"{secure_filename(form.title or 'form')}-{suffix}.pdf"


def _requires_compatible_blank_download(source_pdf):
    if not source_pdf or not os.path.exists(source_pdf):
        return False
    if source_pdf_has_adobe_wait_shell(source_pdf):
        return True
    try:
        field_info = inspect_pdf_fields(source_pdf)
        if field_info.get('field_count'):
            return False
    except Exception:
        pass
    try:
        xfa_info = inspect_xfa_fields(source_pdf)
        return bool(xfa_info.get('fields'))
    except Exception:
        return False


def _log_pdf_render_event(form, action, meta, saved_form_id=None, no_retention=False):
    try:
        payload = {
            'form_id': int(form.id),
            'form_title': str(form.title or ''),
            'action': str(action or ''),
            'saved_form_id': int(saved_form_id) if saved_form_id else None,
            'no_retention': bool(no_retention),
            'mode': str((meta or {}).get('mode') or ''),
            'mapped_count': int((meta or {}).get('mapped_count') or 0),
            'truncation_count': len((meta or {}).get('truncations') or []),
            'template_id': str((meta or {}).get('template_id') or ''),
        }
        db.session.add(
            AuditLog(
                actor_id=current_user.id,
                action='forms_pdf_render',
                details=json.dumps(payload, ensure_ascii=True),
            )
        )
    except Exception:
        return


def _render_document_text(form, schema, payload, blank_mode=False):
    lines = [f"Form: {form.title}", f"Generated: {_safe_display_dt(_utcnow_naive())}", ""]
    for section in schema.get('sections', []):
        lines.append(f"[{section['title']}]")
        for field in section.get('fields', []):
            lines.append(f"{field['label']}: {_print_value(payload.get('values', {}).get(field['name']), blank_mode)}")
        lines.append("")
    lines.append("[People by Role]")
    entries = payload.get('role_entries', [])
    if entries:
        for idx, row in enumerate(entries, start=1):
            lines.extend([
                f"Role Entry {idx}:",
                f"  Role: {_print_value(row.get('role'), blank_mode)}",
                f"  Full Name: {_print_value(row.get('full_name'), blank_mode)}",
                f"  ID/DL: {_print_value(row.get('identifier'), blank_mode)}",
                f"  Phone: {_print_value(row.get('phone'), blank_mode)}",
                f"  Vehicle: {_print_value(row.get('vehicle'), blank_mode)}",
                f"  Notes: {_print_value(row.get('notes'), blank_mode)}",
                "",
            ])
    else:
        lines.extend(["No role entries.", ""])
    lines.extend(["[Notes]", _print_value(payload.get('notes'), blank_mode), ""])
    return '\n'.join(lines)


def _log_no_retention_event(form, action_type, status='ok'):
    details = json.dumps({'form_id': form.id, 'form_title': form.title, 'retention_mode': form.retention_mode or 'full_save_allowed', 'action_type': action_type, 'status': status}, ensure_ascii=True)
    db.session.add(AuditLog(actor_id=current_user.id, action='forms_no_retention_event', details=details))


def _cleanup_temp_payloads():
    now = int(time.time())
    bucket = session.get(TEMP_FORM_SESSION_KEY, {})
    if not isinstance(bucket, dict):
        session[TEMP_FORM_SESSION_KEY] = {}
        return
    changed = False
    for token, item in list(bucket.items()):
        created = int(item.get('created_at', 0)) if isinstance(item, dict) else 0
        if not created or (now - created) > TEMP_FORM_TTL_SECONDS:
            bucket.pop(token, None)
            changed = True
    if changed:
        session[TEMP_FORM_SESSION_KEY] = bucket
        session.modified = True


def _store_temp_payload(form, payload):
    _cleanup_temp_payloads()
    token = secrets.token_urlsafe(18)
    bucket = session.get(TEMP_FORM_SESSION_KEY, {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket[token] = {'form_id': form.id, 'created_at': int(time.time()), 'payload': payload}
    session[TEMP_FORM_SESSION_KEY] = bucket
    session.modified = True
    return token


def _read_temp_payload(form_id, token, purge=False):
    _cleanup_temp_payloads()
    bucket = session.get(TEMP_FORM_SESSION_KEY, {})
    if not isinstance(bucket, dict):
        return None
    item = bucket.get(token)
    if not isinstance(item, dict) or int(item.get('form_id') or 0) != int(form_id):
        return None
    payload = item.get('payload') if isinstance(item.get('payload'), dict) else None
    if purge:
        bucket.pop(token, None)
        session[TEMP_FORM_SESSION_KEY] = bucket
        session.modified = True
    return payload


@bp.route('/forms')
@login_required
def list_forms():
    recovered_count = _sync_forms_from_storage()
    if recovered_count:
        flash(f'Recovered {recovered_count} forms from the local form library.', 'success')
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = Form.query.filter_by(is_active=True)
    if q:
        query = query.filter(Form.title.ilike(f'%{q}%'))
    if category:
        query = query.filter(Form.category == category)
    forms = query.order_by(Form.uploaded_at.desc()).all()
    categories = [row[0] for row in db.session.query(Form.category).filter(Form.is_active.is_(True), Form.category.isnot(None)).distinct().order_by(Form.category.asc()).all() if row[0]]
    return render_template(
        'forms.html',
        forms=forms,
        user=current_user,
        categories=categories,
        saved_form_count=SavedForm.query.filter_by(officer_user_id=current_user.id).count(),
        search_term=q,
        category_filter=category,
        can_manage_form_maintenance=_can_manage_form_maintenance(current_user),
        can_manage_uploads=current_user.can_manage_site(),
    )


@bp.route('/forms/maintenance')
@login_required
def forms_maintenance():
    _require_form_maintenance()
    _sync_forms_from_storage()
    forms = Form.query.order_by(Form.uploaded_at.desc()).all()
    rows = []
    for form in forms:
        schema = _schema_for_form(form)
        fill_state = _form_fill_state(form, schema)
        rows.append({
            'form': form,
            'schema_id': schema.get('id') or 'generic_form_v1',
            'online_ready': fill_state['is_ready'],
            'field_count': sum(len(section.get('fields') or []) for section in schema.get('sections', [])),
            'warning': '' if fill_state['is_ready'] else fill_state['fallback_message'],
        })
    return render_template('forms_maintenance.html', user=current_user, rows=rows)


def _form_boolean_from_request(name, default=False):
    raw = request.form.get(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}


def _form_manager_payload(form):
    return {
        'id': form.id if form else '',
        'title': form.title if form else '',
        'category': form.category if form else '',
        'version_label': form.version_label if form else '',
        'notes': form.notes if form else '',
        'contains_pii': bool(form.contains_pii) if form else False,
        'retention_mode': form.retention_mode if form else 'full_save_allowed',
        'allow_email': bool(form.allow_email) if form else True,
        'allow_download': bool(form.allow_download) if form else True,
        'allow_completed_save': bool(form.allow_completed_save) if form else True,
        'allow_blank_print': bool(form.allow_blank_print) if form else True,
        'is_active': bool(form.is_active) if form else True,
        'file_path': form.file_path if form else '',
        'official_source_url': form.official_source_url if form else '',
        'official_source_version': form.official_source_version if form else '',
        'official_source_hash': form.official_source_hash if form else '',
        'official_source_last_checked_at': form.official_source_last_checked_at if form else None,
        'official_source_last_status': form.official_source_last_status if form else '',
        'source_auto_update_enabled': bool(form.source_auto_update_enabled) if form else False,
    }


@bp.route('/forms/manage', methods=['GET', 'POST'])
@login_required
def forms_manager():
    _require_form_maintenance()
    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()
        form_id = request.form.get('form_id', type=int)
        form = _get_or_404(Form, form_id) if form_id else None

        if action == 'hide':
            if not form:
                flash('Choose a form before removing it from the library.', 'error')
                return redirect(url_for('forms.forms_manager'))
            form.is_active = False
            db.session.add(AuditLog(actor_id=current_user.id, action='form_library_hide', details=form.title))
            db.session.commit()
            flash(f'{form.title} was removed from the active forms library.', 'success')
            return redirect(url_for('forms.forms_manager', edit=form.id))

        if action == 'restore':
            if not form:
                flash('Choose a form before restoring it.', 'error')
                return redirect(url_for('forms.forms_manager'))
            form.is_active = True
            db.session.add(AuditLog(actor_id=current_user.id, action='form_library_restore', details=form.title))
            db.session.commit()
            flash(f'{form.title} was restored to the active forms library.', 'success')
            return redirect(url_for('forms.forms_manager', edit=form.id))

        if not form:
            flash('Upload a form file first, then edit it here.', 'error')
            return redirect(url_for('forms.upload_form'))

        title = (request.form.get('title') or '').strip()
        if not title:
            flash('Form title is required.', 'error')
            return redirect(url_for('forms.forms_manager', edit=form.id))

        retention_mode = (request.form.get('retention_mode') or form.retention_mode or 'full_save_allowed').strip().lower()
        if retention_mode not in RETENTION_MODES:
            retention_mode = 'full_save_allowed'

        form.title = title
        form.category = (request.form.get('category') or '').strip() or 'General'
        form.version_label = (request.form.get('version_label') or '').strip() or None
        form.notes = (request.form.get('notes') or '').strip() or None
        form.contains_pii = _form_boolean_from_request('contains_pii', form.contains_pii)
        form.retention_mode = retention_mode
        form.allow_email = _form_boolean_from_request('allow_email', form.allow_email)
        form.allow_download = _form_boolean_from_request('allow_download', form.allow_download)
        form.allow_blank_print = _form_boolean_from_request('allow_blank_print', form.allow_blank_print)
        form.allow_completed_save = _form_boolean_from_request('allow_completed_save', form.allow_completed_save)
        if retention_mode in {'no_pii_retention', 'temporary_pii_only', 'blank_template_only'}:
            form.allow_completed_save = False
        form.is_active = _form_boolean_from_request('is_active', form.is_active)
        form.official_source_url = (request.form.get('official_source_url') or '').strip() or None
        form.official_source_version = (request.form.get('official_source_version') or '').strip() or None
        form.source_auto_update_enabled = _form_boolean_from_request('source_auto_update_enabled', False)

        if action in {'check_source', 'update_source'}:
            result = check_and_update_form_source(
                form,
                _resolve_storage_path(current_app.config['FORMS_UPLOAD']),
                apply_update=(action == 'update_source'),
            )
            form.official_source_last_checked_at = _utcnow_naive()
            form.official_source_last_status = f'{result.status}: {result.message}'
            if result.sha256_hash:
                form.official_source_hash = result.sha256_hash
            if result.downloaded and result.new_path:
                form.file_path = result.new_path
                form.uploaded_at = _utcnow_naive()
                db.session.add(AuditLog(actor_id=current_user.id, action='form_official_source_update', details=f'{form.title}|{result.source_url}'))
            else:
                db.session.add(AuditLog(actor_id=current_user.id, action='form_official_source_check', details=f'{form.title}|{result.status}|{result.source_url}'))
            db.session.commit()
            flash(result.message, 'success' if result.ok else 'error')
            return redirect(url_for('forms.forms_manager', edit=form.id))

        db.session.add(AuditLog(actor_id=current_user.id, action='form_library_update', details=form.title))
        db.session.commit()
        flash(f'Saved form: {form.title}', 'success')
        return redirect(url_for('forms.forms_manager', edit=form.id))

    _sync_forms_from_storage()
    forms = Form.query.order_by(Form.is_active.desc(), Form.uploaded_at.desc(), Form.title.asc()).all()
    edit_id = request.args.get('edit', type=int)
    edit_form = db.session.get(Form, edit_id) if edit_id else (forms[0] if forms else None)
    categories = [
        row[0]
        for row in db.session.query(Form.category)
        .filter(Form.category.isnot(None))
        .distinct()
        .order_by(Form.category.asc())
        .all()
        if row[0]
    ]
    return render_template(
        'forms_manager.html',
        user=current_user,
        forms=forms,
        edit_form=_form_manager_payload(edit_form) if edit_form else _form_manager_payload(None),
        selected_form=edit_form,
        categories=categories or category_options(),
        retention_modes=sorted(RETENTION_MODES),
        can_upload=current_user.can_manage_site(),
    )


@bp.route('/forms/call-types', methods=['GET', 'POST'])
@login_required
def call_type_rules_manager():
    _require_form_maintenance()
    active_forms = Form.query.filter_by(is_active=True).order_by(Form.category.asc(), Form.title.asc()).all()
    rules = load_call_type_rules(include_inactive=True)

    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()
        old_slug = slugify_call_type(request.form.get('old_slug') or request.form.get('slug') or request.form.get('title'))
        if action == 'delete':
            if old_slug in rules:
                deleted_title = rules[old_slug].get('title') or old_slug
                rules.pop(old_slug, None)
                save_call_type_rules(rules)
                db.session.add(AuditLog(actor_id=current_user.id, action='call_type_rule_delete', details=deleted_title))
                db.session.commit()
                flash(f'Removed call type: {deleted_title}', 'success')
            return redirect(url_for('forms.call_type_rules_manager'))

        recommended_forms = split_multivalue(
            request.form.getlist('recommended_forms') + split_multivalue(request.form.get('recommended_forms_extra'))
        )
        optional_forms = split_multivalue(
            request.form.getlist('optional_forms') + split_multivalue(request.form.get('optional_forms_extra'))
        )
        rule = normalize_call_type_rule(
            {
                'slug': request.form.get('slug'),
                'title': request.form.get('title'),
                'shortLabel': request.form.get('short_label'),
                'description': request.form.get('description'),
                'recommendedForms': recommended_forms,
                'optionalForms': optional_forms,
                'statutes': request.form.get('statutes'),
                'checklistItems': request.form.get('checklist_items'),
                'active': request.form.get('active') == 'on',
            }
        )
        if old_slug and old_slug != rule['slug']:
            rules.pop(old_slug, None)
        rules[rule['slug']] = rule
        save_call_type_rules(rules)
        db.session.add(AuditLog(actor_id=current_user.id, action='call_type_rule_save', details=rule['title']))
        db.session.commit()
        flash(f'Saved call type: {rule["title"]}', 'success')
        return redirect(url_for('forms.call_type_rules_manager', edit=rule['slug']))

    edit_slug = slugify_call_type(request.args.get('edit') or '')
    edit_rule = rules.get(edit_slug) if edit_slug else None
    form_titles = {form.title for form in active_forms}
    recommended_extra = [name for name in (edit_rule or {}).get('recommendedForms', []) if name not in form_titles]
    optional_extra = [name for name in (edit_rule or {}).get('optionalForms', []) if name not in form_titles]
    return render_template(
        'forms_call_types.html',
        user=current_user,
        forms=active_forms,
        rules=rules,
        edit_rule=edit_rule,
        edit_slug=edit_slug,
        recommended_extra=recommended_extra,
        optional_extra=optional_extra,
    )


@bp.route('/forms/upload', methods=['GET', 'POST'])
@login_required
def upload_form():
    require_admin()
    if request.method == 'POST':
        files = [file for file in request.files.getlist('files') if file and file.filename]
        if not files:
            single = request.files.get('file')
            if single and single.filename:
                files = [single]
        if not files:
            return render_template('forms_upload.html', error='No files uploaded.', user=current_user)

        notes = request.form.get('notes')
        save_dir = _resolve_storage_path(current_app.config['FORMS_UPLOAD'])
        os.makedirs(save_dir, exist_ok=True)
        title_values = request.form.getlist('file_title')
        category_overrides = request.form.getlist('file_category')
        version_values = request.form.getlist('file_version_label')
        pii_values = request.form.getlist('file_contains_pii')
        retention_values = request.form.getlist('file_retention_mode')
        allow_email_values = request.form.getlist('file_allow_email')
        allow_download_values = request.form.getlist('file_allow_download')
        allow_save_values = request.form.getlist('file_allow_completed_save')
        allow_blank_values = request.form.getlist('file_allow_blank_print')

        for index, file in enumerate(files):
            safe_name = secure_filename(file.filename)
            filename = f"{int(_utcnow_naive().timestamp())}-{index}-{safe_name}"
            path = os.path.join(save_dir, filename)
            file.save(path)
            detected = heuristic_metadata(file.filename)
            title = title_values[index].strip() if index < len(title_values) and title_values[index].strip() else detected['title']
            category = category_overrides[index].strip() if index < len(category_overrides) and category_overrides[index].strip() else detected['category']
            version_label = version_values[index].strip() if index < len(version_values) and version_values[index].strip() else detected['version_label']
            contains_pii = index < len(pii_values) and pii_values[index] == '1'
            retention_mode = retention_values[index].strip().lower() if index < len(retention_values) and retention_values[index].strip() else ('no_pii_retention' if contains_pii else 'full_save_allowed')
            if retention_mode not in RETENTION_MODES:
                retention_mode = 'full_save_allowed'
            allow_email = not (index < len(allow_email_values) and allow_email_values[index] == '0')
            allow_download = not (index < len(allow_download_values) and allow_download_values[index] == '0')
            allow_completed_save = not (index < len(allow_save_values) and allow_save_values[index] == '0')
            allow_blank_print = not (index < len(allow_blank_values) and allow_blank_values[index] == '0')
            if retention_mode in {'no_pii_retention', 'temporary_pii_only', 'blank_template_only'}:
                allow_completed_save = False
            form = Form(
                title=title,
                category=category,
                version_label=version_label,
                file_path=path,
                uploaded_by=current_user.id,
                notes=notes,
                contains_pii=contains_pii,
                retention_mode=retention_mode,
                allow_email=allow_email,
                allow_download=allow_download,
                allow_completed_save=allow_completed_save,
                allow_blank_print=allow_blank_print,
            )
            db.session.add(form)
            db.session.flush()
            db.session.add(AuditLog(actor_id=current_user.id, action='forms_upload', details=title))
            family = normalize_form_family(title)
            if family:
                related = [existing for existing in Form.query.order_by(Form.uploaded_at.desc()).all() if normalize_form_family(existing.title) == family]
                latest = choose_latest_form(related, current_app.config.get('OPENAI_API_KEY'))
                latest_id = latest.id if latest else None
                for existing in related:
                    existing.is_active = (existing.id == latest_id)
        db.session.commit()
        return redirect(url_for('forms.list_forms'))

    return render_template('forms_upload.html', user=current_user, category_options=category_options(), retention_options=sorted(RETENTION_MODES))


@bp.route('/forms/metadata-detect', methods=['POST'])
@login_required
def detect_upload_metadata():
    require_admin()
    files = [file for file in request.files.getlist('files') if file and file.filename]
    results = detect_form_metadata_from_uploads(files, current_app.config.get('OPENAI_API_KEY'))
    return jsonify({'results': results, 'category_options': category_options(), 'retention_options': sorted(RETENTION_MODES)})


@bp.route('/forms/<int:form_id>/download')
@login_required
def download_form(form_id):
    form = _get_or_404(Form, form_id)
    file_path = _resolve_storage_path(form.file_path)
    if not file_path or not os.path.exists(file_path):
        abort(404)
    if _requires_compatible_blank_download(file_path):
        schema = _schema_for_form(form)
        payload = _empty_payload(schema)
        pdf_path, render_meta = render_form_pdf(file_path, schema, payload, blank_mode=True)
        _log_pdf_render_event(form, 'blank_download_compatible', render_meta, no_retention=_form_policy(form).get('is_no_retention', False))
        db.session.commit()
        return _send_ephemeral_file(pdf_path, _preview_pdf_filename(form, blank_mode=True))
    return send_file(file_path, as_attachment=True)


@bp.route('/forms/<int:form_id>/blank-print')
@login_required
def blank_form_preview(form_id):
    form = _get_or_404(Form, form_id)
    policy = _form_policy(form)
    if not policy['allow_blank_print']:
        abort(403)
    schema = _schema_for_form(form)
    payload = _empty_payload(schema)
    sections, role_rows = _build_preview_sections(schema, payload, blank_mode=True)
    return render_template(
        'forms_preview.html',
        user=current_user,
        form=form,
        schema=schema,
        payload=payload,
        sections=sections,
        role_rows=role_rows,
        blank_mode=True,
        print_mode=request.args.get('print') == '1',
        preview_title='Blank Form Preview',
                generated_at=_safe_display_dt(datetime.now(timezone.utc).replace(tzinfo=None)),
        saved_record=None,
        temp_token='',
        no_retention_mode=policy['is_no_retention'],
        preview_pdf_url=url_for('forms.blank_form_pdf', form_id=form.id, v=int(time.time())),
        preview_pdf_download_name=_preview_pdf_filename(form, blank_mode=True),
    )


@bp.route('/forms/<int:form_id>/blank-print/pdf')
@login_required
def blank_form_pdf(form_id):
    form = _get_or_404(Form, form_id)
    policy = _form_policy(form)
    if not policy['allow_blank_print']:
        abort(403)
    schema = _schema_for_form(form)
    payload = _empty_payload(schema)
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form), schema, payload, blank_mode=True)
    _log_pdf_render_event(form, 'blank_pdf', render_meta, no_retention=_form_policy(form).get('is_no_retention', False))
    db.session.commit()
    return _send_ephemeral_file(pdf_path, _preview_pdf_filename(form, blank_mode=True))


@bp.route('/forms/<int:form_id>/pdf-debug')
@login_required
def form_pdf_debug(form_id):
    _require_form_maintenance()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    source_pdf = _pdf_source_for_form(form)
    payload = _normalize_payload({}, schema)
    render_path, meta = render_form_pdf(source_pdf, schema, payload, blank_mode=True)
    try:
        schema_field_names = []
        for section in schema.get('sections', []):
            for field in section.get('fields', []):
                name = str(field.get('name') or '').strip()
                if name:
                    schema_field_names.append(name)
        source_field_rows = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
        source_field_names = [item.get('name') for item in source_field_rows.get('fields', []) if isinstance(item, dict) and item.get('name')]
        mapped_field_names = meta.get('mapped_fields') if isinstance(meta.get('mapped_fields'), list) else []
        schema_set = set(schema_field_names)
        source_set = set(source_field_names)
        mapped_set = set(mapped_field_names)
        schema_unmapped = sorted(schema_set - mapped_set)
        mapped_not_in_schema = sorted(mapped_set - schema_set)
        schema_not_in_pdf = sorted(schema_set - source_set) if source_set else []
        suggestions = {}
        pdf_norm = {_normalize_compare_key(name): name for name in source_field_names}
        for field_name in schema_field_names:
            if field_name in mapped_set:
                continue
            candidate = pdf_norm.get(_normalize_compare_key(field_name))
            if candidate:
                suggestions[field_name] = candidate
        suggested_template = {
            'template_id': schema.get('id') or 'generic_form_v1',
            'description': 'Auto-generated suggestion from /pdf-debug',
            'field_map': suggestions,
            'checkbox_on_values': {},
            'ui_fields': [],
        }
        debug = {
            'form_id': form.id,
            'title': form.title,
            'schema_id': schema.get('id'),
            'source_pdf': source_pdf or '',
            'render_meta': meta,
            'source_fields': source_field_rows,
            'coverage': {
                'schema_field_count': len(schema_field_names),
                'source_pdf_field_count': len(source_field_names),
                'mapped_field_count': len(mapped_field_names),
                'schema_unmapped_fields': schema_unmapped,
                'mapped_not_in_schema': mapped_not_in_schema,
                'schema_not_in_pdf': schema_not_in_pdf,
            },
            'mapping_suggestions': suggestions,
            'suggested_template_payload': suggested_template,
        }
    finally:
        try:
            if render_path and os.path.exists(render_path):
                os.remove(render_path)
        except Exception:
            pass
    return jsonify(debug)


@bp.route('/forms/<int:form_id>/pdf-debug/view')
@login_required
def form_pdf_debug_view(form_id):
    _require_form_maintenance()
    issues_only = (request.args.get('issues_only') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
    q = (request.args.get('q') or '').strip().lower()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    schema_id = schema.get('id') or 'generic_form_v1'
    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    source_names = [item.get('name') for item in source_fields.get('fields', []) if isinstance(item, dict) and item.get('name')]
    source_set = set(source_names)
    template = get_template_payload(schema_id)
    field_map = template.get('field_map') if isinstance(template.get('field_map'), dict) else {}

    rows = []
    mapped_counts = {}
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            name = str(field.get('name') or '').strip()
            if not name:
                continue
            mapped_pdf_name = str(field_map.get(name) or name).strip()
            if mapped_pdf_name:
                mapped_counts[mapped_pdf_name] = mapped_counts.get(mapped_pdf_name, 0) + 1
            rows.append({
                'section': section.get('title') or 'Form Fields',
                'schema_field': name,
                'label': field.get('label') or name,
                'mapped_pdf_field': mapped_pdf_name,
                'exists_on_pdf': mapped_pdf_name in source_set,
            })

    for row in rows:
        target = row.get('mapped_pdf_field') or ''
        row['duplicate_target'] = bool(target and mapped_counts.get(target, 0) > 1)

    if q:
        rows = [
            row for row in rows
            if q in str(row.get('schema_field') or '').lower()
            or q in str(row.get('label') or '').lower()
            or q in str(row.get('mapped_pdf_field') or '').lower()
            or q in str(row.get('section') or '').lower()
        ]

    if issues_only:
        rows = [row for row in rows if (not row.get('exists_on_pdf')) or row.get('duplicate_target')]

    pdf_only = []
    known = {row['mapped_pdf_field'] for row in rows}
    for pdf_name in source_names:
        if pdf_name not in known:
            pdf_only.append(pdf_name)

    counts = {
        'total_rows': len(rows),
        'missing_pdf_fields': len([row for row in rows if not row.get('exists_on_pdf')]),
        'duplicate_target_rows': len([row for row in rows if row.get('duplicate_target')]),
        'pdf_only_fields': len(pdf_only),
    }

    return render_template(
        'forms_pdf_debug_view.html',
        user=current_user,
        form=form,
        schema_id=schema_id,
        source_pdf=source_pdf or '',
        source_field_count=len(source_names),
        rows=rows,
        pdf_only_fields=pdf_only,
        duplicate_targets=sorted([name for name, count in mapped_counts.items() if count > 1]),
        issues_only=issues_only,
        q=q,
        counts=counts,
    )


@bp.route('/forms/<int:form_id>/pdf-template', methods=['GET', 'POST'])
@login_required
def form_pdf_template(form_id):
    _require_form_maintenance()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    schema_id = schema.get('id') or 'generic_form_v1'

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        field_map = payload.get('field_map')
        if not isinstance(field_map, dict):
            return jsonify({'ok': False, 'error': 'field_map must be an object'}), 400
        checkbox_on_values = payload.get('checkbox_on_values')
        if checkbox_on_values is not None and not isinstance(checkbox_on_values, dict):
            return jsonify({'ok': False, 'error': 'checkbox_on_values must be an object'}), 400
        ui_fields = payload.get('ui_fields')
        if ui_fields is not None and not isinstance(ui_fields, list):
            return jsonify({'ok': False, 'error': 'ui_fields must be an array'}), 400
        clean_map = {}
        for key, value in field_map.items():
            left = str(key or '').strip()
            right = str(value or '').strip()
            if left and right:
                clean_map[left] = right
        clean_checkbox = {}
        if isinstance(checkbox_on_values, dict):
            for key, value in checkbox_on_values.items():
                left = str(key or '').strip()
                right = str(value or '').strip()
                if left and right:
                    clean_checkbox[left] = right
        clean_ui_fields = []
        if isinstance(ui_fields, list):
            for item in ui_fields:
                if not isinstance(item, dict):
                    continue
                name = str(item.get('name') or '').strip()
                if not name:
                    continue
                clean_ui_fields.append({
                    'name': name,
                    'label': str(item.get('label') or _humanize_field_name(name)).strip(),
                    'type': str(item.get('type') or 'text').strip() or 'text',
                    'section': str(item.get('section') or 'Form Fields').strip() or 'Form Fields',
                    'required': bool(item.get('required')),
                    'placeholder': str(item.get('placeholder') or '').strip(),
                })
        auto_apply = bool(payload.get('auto_apply_suggestions'))
        if auto_apply:
            source_pdf = _pdf_source_for_form(form)
            source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
            source_names = [item.get('name') for item in source_fields.get('fields', []) if isinstance(item, dict) and item.get('name')]
            schema_names = []
            for section in schema.get('sections', []):
                for field in section.get('fields', []):
                    name = str(field.get('name') or '').strip()
                    if name:
                        schema_names.append(name)
            normalized_source = {_normalize_compare_key(name): name for name in source_names}
            for key in schema_names:
                if key in clean_map:
                    continue
                hit = normalized_source.get(_normalize_compare_key(key))
                if hit:
                    clean_map[key] = hit
        template = {
            'template_id': schema_id,
            'description': str(payload.get('description') or 'PDF field mapping template').strip(),
            'field_map': clean_map,
            'checkbox_on_values': clean_checkbox,
            'ui_fields': clean_ui_fields,
        }
        source_pdf = _pdf_source_for_form(form)
        source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
        template, _removed = _sanitize_template_against_pdf(schema, source_fields, template)
        path = save_template_payload(schema_id, template)
        return jsonify({
            'ok': True,
            'schema_id': schema_id,
            'path': path,
            'field_count': len(template.get('field_map') or {}),
            'checkbox_override_count': len(template.get('checkbox_on_values') or {}),
            'ui_field_count': len(template.get('ui_fields') or []),
        })

    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    suggestions = _mapping_suggestions_for_schema(schema, source_fields)
    schema_names = []
    for section in schema.get('sections', []):
        for field in section.get('fields', []):
            name = str(field.get('name') or '').strip()
            if name:
                schema_names.append(name)
    current_map = get_template_payload(schema_id).get('field_map') or {}
    unmapped_suggestions = {}
    current_map = get_template_payload(schema_id).get('field_map') or {}
    for key, value in suggestions.items():
        if key not in current_map:
            unmapped_suggestions[key] = value
    suggested_template = {
        'template_id': schema_id,
        'description': 'Auto-generated suggestion from /pdf-template',
        'field_map': unmapped_suggestions,
        'checkbox_on_values': _checkbox_overrides_from_source(source_fields),
        'ui_fields': [
            {
                'name': str(field.get('name') or '').strip(),
                'label': str(field.get('label') or _humanize_field_name(str(field.get('name') or ''))).strip(),
                'type': str(field.get('type') or 'text').strip() or 'text',
                'section': str(section.get('title') or 'Form Fields').strip() or 'Form Fields',
                'required': bool(field.get('required')),
                'placeholder': str(field.get('placeholder') or '').strip(),
            }
            for section in schema.get('sections', [])
            for field in section.get('fields', [])
            if str(field.get('name') or '').strip()
        ],
    }
    return jsonify({
        'ok': True,
        'form_id': form.id,
        'title': form.title,
        'schema_id': schema_id,
        'source_pdf': source_pdf or '',
        'source_fields': source_fields,
        'template': get_template_payload(schema_id),
        'mapping_suggestions': unmapped_suggestions,
        'suggested_template_payload': suggested_template,
    })


@bp.route('/forms/<int:form_id>/pdf-template/validate', methods=['POST'])
@login_required
def form_pdf_template_validate(form_id):
    _require_form_maintenance()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({'ok': False, 'error': 'payload must be an object'}), 400
    cleaned, removed = _sanitize_template_against_pdf(schema, source_fields, payload)
    return jsonify({
        'ok': True,
        'removed': removed,
        'cleaned_counts': {
            'field_map': len(cleaned.get('field_map') or {}),
            'ui_fields': len(cleaned.get('ui_fields') or []),
            'checkbox_on_values': len(cleaned.get('checkbox_on_values') or {}),
        },
    })


@bp.route('/forms/<int:form_id>/pdf-template/validate-current')
@login_required
def form_pdf_template_validate_current(form_id):
    _require_form_maintenance()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    schema_id = schema.get('id') or 'generic_form_v1'
    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    current_payload = get_template_payload(schema_id)
    _, removed = _sanitize_template_against_pdf(schema, source_fields, current_payload)
    removed_field_map = len(removed.get('removed_field_map') or [])
    removed_ui_fields = len(removed.get('removed_ui_fields') or [])
    removed_checkbox = len(removed.get('removed_checkbox_overrides') or [])
    removed_total = removed_field_map + removed_ui_fields + removed_checkbox
    if removed_total:
        flash(
            'Current template has invalid items '
            f'(field_map={removed_field_map}, ui_fields={removed_ui_fields}, checkbox_overrides={removed_checkbox}). '
            'Open Template Editor and save to clean.',
            'warning',
        )
    else:
        flash('Current template validation passed. No invalid mapping items found.', 'success')
    return redirect(url_for('forms.form_pdf_debug_view', form_id=form.id))


@bp.route('/forms/<int:form_id>/pdf-template/clean-current', methods=['POST'])
@login_required
def form_pdf_template_clean_current(form_id):
    _require_form_maintenance()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    schema_id = schema.get('id') or 'generic_form_v1'
    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    current_payload = get_template_payload(schema_id)
    cleaned, removed = _sanitize_template_against_pdf(schema, source_fields, current_payload)
    save_template_payload(schema_id, cleaned)
    removed_field_map = len(removed.get('removed_field_map') or [])
    removed_ui_fields = len(removed.get('removed_ui_fields') or [])
    removed_checkbox = len(removed.get('removed_checkbox_overrides') or [])
    removed_total = removed_field_map + removed_ui_fields + removed_checkbox
    if removed_total:
        flash(
            'Template cleaned and saved. Removed '
            f'{removed_total} invalid items '
            f'(field_map={removed_field_map}, ui_fields={removed_ui_fields}, checkbox_overrides={removed_checkbox}).',
            'success',
        )
    else:
        flash('Template was already clean. No changes made.', 'success')
    return redirect(url_for('forms.form_pdf_debug_view', form_id=form.id))


@bp.route('/forms/<int:form_id>/pdf-template/auto', methods=['POST'])
@login_required
def form_pdf_template_auto(form_id):
    _require_form_maintenance()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    schema_id = schema.get('id') or 'generic_form_v1'
    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    suggestions = _mapping_suggestions_for_schema(schema, source_fields)
    current = get_template_payload(schema_id)
    current_map = current.get('field_map') if isinstance(current.get('field_map'), dict) else {}
    merged_map = dict(current_map)
    for key, value in suggestions.items():
        if key not in merged_map:
            merged_map[key] = value
    current_checkbox = current.get('checkbox_on_values') if isinstance(current.get('checkbox_on_values'), dict) else {}
    merged_checkbox = dict(current_checkbox)
    for key, value in _checkbox_overrides_from_source(source_fields).items():
        if key not in merged_checkbox:
            merged_checkbox[key] = value
    template = {
        'template_id': schema_id,
        'description': str(current.get('description') or 'Auto-updated mapping template').strip(),
        'field_map': merged_map,
        'checkbox_on_values': merged_checkbox,
        'ui_fields': current.get('ui_fields') if isinstance(current.get('ui_fields'), list) and current.get('ui_fields') else [
            {
                'name': str(field.get('name') or '').strip(),
                'label': str(field.get('label') or _humanize_field_name(str(field.get('name') or ''))).strip(),
                'type': str(field.get('type') or 'text').strip() or 'text',
                'section': str(section.get('title') or 'Form Fields').strip() or 'Form Fields',
                'required': bool(field.get('required')),
                'placeholder': str(field.get('placeholder') or '').strip(),
            }
            for section in schema.get('sections', [])
            for field in section.get('fields', [])
            if str(field.get('name') or '').strip()
        ],
    }
    path = save_template_payload(schema_id, template)
    response_payload = {
        'ok': True,
        'form_id': form.id,
        'schema_id': schema_id,
        'path': path,
        'field_count': len(merged_map),
        'checkbox_override_count': len(merged_checkbox),
        'added_fields': sorted([k for k in suggestions.keys() if k not in current_map]),
    }
    wants_json = (
        request.is_json
        or 'application/json' in (request.headers.get('Accept') or '').lower()
        or str(request.args.get('format') or '').lower() == 'json'
    )
    if wants_json:
        return jsonify(response_payload)
    flash(
        f"Auto-applied PDF template suggestions. Added {len(response_payload['added_fields'])} new field mappings.",
        'success',
    )
    return redirect(url_for('forms.form_pdf_template_editor', form_id=form.id))


@bp.route('/forms/<int:form_id>/pdf-template/editor', methods=['GET', 'POST'])
@login_required
def form_pdf_template_editor(form_id):
    _require_form_maintenance()
    load_suggested = (request.args.get('load_suggested') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    schema_id = schema.get('id') or 'generic_form_v1'
    source_pdf = _pdf_source_for_form(form)
    source_fields = inspect_pdf_fields(source_pdf) if source_pdf else {'field_count': 0, 'fields': []}
    template_payload = get_template_payload(schema_id)
    suggestions = _mapping_suggestions_for_schema(schema, source_fields)
    suggested_payload = {
        'template_id': schema_id,
        'description': 'Suggested template from editor',
        'field_map': suggestions,
        'checkbox_on_values': _checkbox_overrides_from_source(source_fields),
        'ui_fields': [
            {
                'name': str(field.get('name') or '').strip(),
                'label': str(field.get('label') or _humanize_field_name(str(field.get('name') or ''))).strip(),
                'type': str(field.get('type') or 'text').strip() or 'text',
                'section': str(section.get('title') or 'Form Fields').strip() or 'Form Fields',
                'required': bool(field.get('required')),
                'placeholder': str(field.get('placeholder') or '').strip(),
            }
            for section in schema.get('sections', [])
            for field in section.get('fields', [])
            if str(field.get('name') or '').strip()
        ],
    }
    if request.method == 'POST':
        raw = (request.form.get('template_json') or '').strip()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            flash('Template JSON is invalid. Fix syntax and try again.', 'error')
            return render_template(
                'forms_pdf_template_editor.html',
                user=current_user,
                form=form,
                schema=schema,
                schema_id=schema_id,
                source_pdf=source_pdf or '',
                source_fields=source_fields,
                suggestions=suggestions,
                template_json=raw,
                suggested_template_json=json.dumps(suggested_payload, indent=2),
            )
        field_map = payload.get('field_map')
        if not isinstance(field_map, dict):
            flash('Template must include field_map as an object.', 'error')
            return render_template(
                'forms_pdf_template_editor.html',
                user=current_user,
                form=form,
                schema=schema,
                schema_id=schema_id,
                source_pdf=source_pdf or '',
                source_fields=source_fields,
                suggestions=suggestions,
                template_json=raw,
                suggested_template_json=json.dumps(suggested_payload, indent=2),
            )
        cleaned, removed = _sanitize_template_against_pdf(schema, source_fields, payload)
        save_path = save_template_payload(schema_id, cleaned)
        removed_total = (
            len(removed.get('removed_field_map') or [])
            + len(removed.get('removed_ui_fields') or [])
            + len(removed.get('removed_checkbox_overrides') or [])
        )
        if removed_total:
            flash(f'PDF template saved with {removed_total} invalid mapping items removed.', 'warning')
        else:
            flash(f'PDF template saved: {save_path}', 'success')
        return redirect(url_for('forms.form_pdf_template_editor', form_id=form.id))

    return render_template(
        'forms_pdf_template_editor.html',
        user=current_user,
        form=form,
        schema=schema,
        schema_id=schema_id,
        source_pdf=source_pdf or '',
        source_fields=source_fields,
        suggestions=suggestions,
        template_json=json.dumps((suggested_payload if load_suggested else template_payload), indent=2),
        suggested_template_json=json.dumps(suggested_payload, indent=2),
    )


@bp.route('/forms/<int:form_id>/preview-temp/<token>')
@login_required
def preview_temp_form(form_id, token):
    form = _get_or_404(Form, form_id)
    policy = _form_policy(form)
    if not policy['is_no_retention']:
        return redirect(url_for('forms.fill_form', form_id=form.id))
    payload_raw = _read_temp_payload(form.id, token, purge=False)
    if not payload_raw:
        flash('Temporary form session expired. Re-enter the form data and try again.', 'error')
        return redirect(url_for('forms.fill_form', form_id=form.id))
    schema = _schema_for_form(form)
    payload = _normalize_payload(payload_raw, schema)
    sections, role_rows = _build_preview_sections(schema, payload, blank_mode=False)
    _log_no_retention_event(form, 'preview_temp')
    db.session.commit()
    return render_template('forms_preview.html', user=current_user, form=form, schema=schema, payload=payload, sections=sections, role_rows=role_rows, blank_mode=False, print_mode=request.args.get('print') == '1', preview_title='Completed Form Preview (No-Retention)', generated_at=_safe_display_dt(_utcnow_naive()), saved_record=None, temp_token=token, no_retention_mode=True, preview_pdf_url=url_for('forms.preview_temp_form_pdf', form_id=form.id, token=token, v=int(time.time())), preview_pdf_download_name=_preview_pdf_filename(form, blank_mode=False))


@bp.route('/forms/<int:form_id>/temp/<token>/preview-pdf')
@login_required
def preview_temp_form_pdf(form_id, token):
    form = _get_or_404(Form, form_id)
    policy = _form_policy(form)
    if not policy['is_no_retention']:
        abort(403)
    payload_raw = _read_temp_payload(form.id, token, purge=False)
    if not payload_raw:
        abort(404)
    schema = _schema_for_form(form)
    payload = _normalize_payload(payload_raw, schema)
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form), schema, payload, blank_mode=False)
    _log_pdf_render_event(form, 'preview_temp_pdf', render_meta, no_retention=True)
    db.session.commit()
    return _send_ephemeral_file(pdf_path, _preview_pdf_filename(form, blank_mode=False))


@bp.route('/forms/<int:form_id>/temp/<token>/download')
@login_required
def download_temp_form(form_id, token):
    form = _get_or_404(Form, form_id)
    policy = _form_policy(form)
    if not policy['is_no_retention'] or not policy['allow_download']:
        abort(403)
    payload_raw = _read_temp_payload(form.id, token, purge=True)
    if not payload_raw:
        flash('Temporary form session expired. Re-enter the form data and try again.', 'error')
        return redirect(url_for('forms.fill_form', form_id=form.id))
    schema = _schema_for_form(form)
    payload = _normalize_payload(payload_raw, schema)
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form), schema, payload, blank_mode=False)
    filename = f"{secure_filename(form.title or 'form')}-{_utcnow_naive().strftime('%Y%m%d-%H%M%S')}.pdf"
    _log_no_retention_event(form, 'download_temp')
    _log_pdf_render_event(form, 'download_temp', render_meta, no_retention=True)
    db.session.commit()
    return _send_ephemeral_file(pdf_path, filename)


@bp.route('/forms/<int:form_id>/temp/<token>/email', methods=['GET', 'POST'])
@login_required
def email_temp_form(form_id, token):
    form = _get_or_404(Form, form_id)
    policy = _form_policy(form)
    if not policy['is_no_retention'] or not policy['allow_email']:
        abort(403)
    payload_raw = _read_temp_payload(form.id, token, purge=True)
    if not payload_raw:
        flash('Temporary form session expired. Re-enter the form data and try again.', 'error')
        return redirect(url_for('forms.fill_form', form_id=form.id))
    schema = _schema_for_form(form)
    payload = _normalize_payload(payload_raw, schema)
    recipient, cc_list = _email_recipients_for_current_user()
    if not recipient:
        flash('Your profile email is required before sending forms. Update Profile and try again.', 'error')
        return redirect(url_for('forms.fill_form', form_id=form.id))
    subject = f"{form.title} - Completed (No-Retention)"
    body = _render_document_text(form, schema, payload, blank_mode=False)
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form), schema, payload, blank_mode=False)
    pdf_bytes = b''
    try:
        with open(pdf_path, 'rb') as handle:
            pdf_bytes = handle.read()
    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
    try:
        sent, info = _smtp_send(
            recipient,
            cc_list,
            subject,
            body,
            attachment_name=f"{secure_filename(form.title or 'form')}.pdf",
            attachment_bytes=pdf_bytes or None,
        )
    except Exception as exc:
        sent, info = False, str(exc)
    if sent:
        _log_no_retention_event(form, 'email_temp', status='sent')
        _log_pdf_render_event(form, 'email_temp', render_meta, no_retention=True)
        db.session.commit()
        flash('Form emailed to your profile address. CC sent to Watch Commander and Desk Sgt. No retained copy remains on site.', 'success')
    else:
        mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body[:1200])}"
        _log_no_retention_event(form, 'email_temp', status='fallback')
        _log_pdf_render_event(form, 'email_temp_fallback', render_meta, no_retention=True)
        db.session.commit()
        flash(f'SMTP not configured or failed. Use this fallback link: {mailto}', 'error')
    return redirect(url_for('forms.fill_form', form_id=form.id))


@bp.route('/forms/<int:form_id>/fill', methods=['GET', 'POST'])
@login_required
def fill_form(form_id):
    _cleanup_temp_payloads()
    form = _get_or_404(Form, form_id)
    schema = _schema_for_form(form)
    policy = _form_policy(form)
    fill_state = _form_fill_state(form, schema)
    saved_form_id = request.args.get('saved_form_id', type=int)
    saved_record = db.session.get(SavedForm, saved_form_id) if saved_form_id else None
    if saved_record and saved_record.form_id != form.id:
        abort(404)
    if saved_record and not _can_view_saved_form(saved_record):
        abort(403)
    scan_result = None

    if request.method == 'POST':
        unexpected_keys = _unexpected_submission_keys(schema)
        if unexpected_keys:
            flash('Form submission contained unsupported fields. Reloaded the form with PDF-backed fields only.', 'error')
            db.session.add(
                AuditLog(
                    actor_id=current_user.id,
                    action='form_submission_rejected',
                    details=f"form_id={form.id}|unexpected_keys={','.join(unexpected_keys[:20])}",
                )
            )
            db.session.commit()
            if saved_form_id:
                return redirect(url_for('forms.fill_form', form_id=form.id, saved_form_id=saved_form_id))
            return redirect(url_for('forms.fill_form', form_id=form.id))

        action = (request.form.get('action') or 'save_draft').strip().lower()
        payload = _parse_submission_payload(schema)
        if action == 'scan_id':
            scan_data = _parse_id_scan_payload(request.form.get('scan_payload'))
            if not scan_data:
                flash('No readable ID barcode data was found. Use Scan ID again or complete the fields manually.', 'error')
            else:
                payload, scan_result = _apply_id_scan_to_payload(
                    schema,
                    payload,
                    scan_data,
                    replace_existing=(request.form.get('scan_replace_existing') or '').strip().lower() in {'1', 'true', 'yes', 'on'},
                )
                if scan_result['imported']:
                    flash('ID data imported. Review the fields before previewing or saving.', 'success')
                else:
                    flash('ID data was read, but existing values were kept. Use Replace Existing if you want to overwrite them.', 'error')
            return render_template(
                'forms_fill.html',
                user=current_user,
                form=form,
                schema=schema,
                payload=payload,
                saved_record=saved_record,
                can_edit=(saved_record is None or _can_edit_saved_form(saved_record)),
                policy=policy,
                fill_state=fill_state,
                scan_supported=_scan_supported(schema),
                scan_result=scan_result,
            )
        if not fill_state['is_ready']:
            flash(fill_state['fallback_message'], 'error')
            return redirect(url_for('forms.fill_form', form_id=form.id))
        if policy['is_blank_only']:
            flash('This form is blank-template-only. Use Print Blank Form.', 'error')
            return redirect(url_for('forms.fill_form', form_id=form.id))
        if policy['is_no_retention']:
            if action in {'preview_completed', 'print_completed', 'email_form', 'download_completed'}:
                token = _store_temp_payload(form, payload)
                if action == 'preview_completed':
                    return redirect(url_for('forms.preview_temp_form', form_id=form.id, token=token))
                if action == 'print_completed':
                    return redirect(url_for('forms.preview_temp_form', form_id=form.id, token=token, print='1'))
                if action == 'download_completed':
                    return redirect(url_for('forms.download_temp_form', form_id=form.id, token=token))
                return redirect(url_for('forms.email_temp_form', form_id=form.id, token=token))
            flash('This form is in no-retention mode. Use Preview, Print, Email, or Download. Completed data is not saved to the website.', 'error')
            return redirect(url_for('forms.fill_form', form_id=form.id))
        if not policy['allow_completed_save'] and action in {'save_completed', 'submit_form'}:
            flash('Completed form saving is disabled by policy for this form.', 'error')
            return redirect(url_for('forms.fill_form', form_id=form.id))

        if action == 'review_before_save':
            validation = _validate_payload_for_completion(schema, payload)
            return render_template(
                'forms_fill.html',
                user=current_user,
                form=form,
                schema=schema,
                payload=payload,
                saved_record=saved_record,
                can_edit=True,
                policy=policy,
                fill_state=fill_state,
                scan_supported=False,
                scan_result=None,
                validation_summary=validation,
            )

        if action == 'save_completed':
            validation = _validate_payload_for_completion(schema, payload)
            if validation['errors']:
                return render_template(
                    'forms_fill.html',
                    user=current_user,
                    form=form,
                    schema=schema,
                    payload=payload,
                    saved_record=saved_record,
                    can_edit=True,
                    policy=policy,
                    fill_state=fill_state,
                    scan_supported=False,
                    scan_result=None,
                    validation_summary=validation,
                )

        target = saved_record
        if target is None:
            target = SavedForm(form_id=form.id, officer_user_id=current_user.id, status='DRAFT', title=form.title)
            db.session.add(target)
            db.session.flush()
            _save_audit(target.id, 'create', 'Created from forms fill page')
        elif not _can_edit_saved_form(target):
            abort(403)
        target.title = (request.form.get('saved_title') or '').strip() or form.title
        target.status = _determine_status(action, fallback=target.status or 'DRAFT')
        target.field_data_json = json.dumps(payload, ensure_ascii=True)
        _save_audit(target.id, 'update', f'Updated action={action}')
        db.session.add(AuditLog(actor_id=current_user.id, action='saved_form_upsert', details=f'form_id={form.id}|saved_form_id={target.id}|status={target.status}|action={action}'))
        db.session.commit()
        if action == 'preview_completed':
            return redirect(url_for('forms.preview_saved_form', saved_form_id=target.id))
        if action == 'print_completed':
            return redirect(url_for('forms.preview_saved_form', saved_form_id=target.id, print='1'))
        if action == 'email_form':
            return redirect(url_for('forms.email_saved_form', saved_form_id=target.id, mode='completed'))
        if action == 'download_completed':
            return redirect(url_for('forms.download_saved_form', saved_form_id=target.id))
        flash('Form saved.', 'success')
        return redirect(url_for('forms.view_saved_form', saved_form_id=target.id))

    payload = _normalize_payload(_load_saved_form_data(saved_record.field_data_json if saved_record else '{}'), schema)
    return render_template(
        'forms_fill.html',
        user=current_user,
        form=form,
        schema=schema,
        payload=payload,
        saved_record=saved_record,
        can_edit=(saved_record is None or _can_edit_saved_form(saved_record)),
        policy=policy,
        fill_state=fill_state,
        scan_supported=_scan_supported(schema),
        scan_result=scan_result,
        validation_summary=None,
    )


@bp.route('/forms/saved')
@login_required
def saved_forms():
    status = (request.args.get('status') or '').strip().upper()
    form_type = (request.args.get('form_type') or '').strip()
    search_term = (request.args.get('q') or '').strip()
    rows = SavedForm.query.order_by(SavedForm.updated_at.desc()).all()
    visible = []
    for row in rows:
        if not _can_view_saved_form(row):
            continue
        if status and row.status != status:
            continue
        if form_type and row.title and form_type.lower() not in row.title.lower():
            continue
        if search_term:
            owner = db.session.get(User, row.officer_user_id)
            owner_name = owner.display_name.lower() if owner else ''
            row_title = (row.title or '').lower()
            if search_term.lower() not in owner_name and search_term.lower() not in row_title:
                continue
        visible.append(row)
    events = AuditLog.query.filter_by(action='forms_no_retention_event', actor_id=current_user.id).order_by(AuditLog.created_at.desc()).limit(30).all()
    parsed_events = []
    for event in events:
        details = _load_saved_form_data(event.details)
        parsed_events.append({'created_at': event.created_at, 'form_title': details.get('form_title') or 'Form', 'retention_mode': details.get('retention_mode') or '', 'action_type': details.get('action_type') or '', 'status': details.get('status') or ''})
    draft_count = sum(1 for row in visible if row.status == 'DRAFT')
    completed_count = sum(1 for row in visible if row.status == 'COMPLETED')
    submitted_count = sum(1 for row in visible if row.status == 'SUBMITTED')
    return render_template(
        'saved_forms.html',
        user=current_user,
        saved_forms=visible,
        status=status,
        form_type=form_type,
        search_term=search_term,
        draft_count=draft_count,
        completed_count=completed_count,
        submitted_count=submitted_count,
        no_retention_events=parsed_events,
        display_dt=_safe_display_dt,
        show_admin_retention_events=current_user.can_manage_site(),
    )


@bp.route('/forms/saved/<int:saved_form_id>')
@login_required
def view_saved_form(saved_form_id):
    record = _get_or_404(SavedForm, saved_form_id)
    if not _can_view_saved_form(record):
        abort(403)
    owner = db.session.get(User, record.officer_user_id)
    form = db.session.get(Form, record.form_id)
    schema = _schema_for_form(form) if form else GENERIC_SCHEMA
    payload = _normalize_payload(_load_saved_form_data(record.field_data_json), schema)
    sections, role_rows = _build_preview_sections(schema, payload, blank_mode=False)
    audits = SavedFormAudit.query.filter_by(saved_form_id=record.id).order_by(SavedFormAudit.created_at.desc()).limit(30).all()
    policy = _form_policy(form) if form else {'allow_email': True, 'allow_download': True, 'allow_blank_print': True, 'is_no_retention': False}
    return render_template('saved_form_detail.html', user=current_user, record=record, owner=owner, form=form, schema=schema, payload=payload, sections=sections, role_rows=role_rows, audits=audits, can_edit=_can_edit_saved_form(record), email_requested=request.args.get('email') == '1', display_dt=_safe_display_dt, policy=policy)


@bp.route('/forms/saved/<int:saved_form_id>/preview')
@login_required
def preview_saved_form(saved_form_id):
    record = _get_or_404(SavedForm, saved_form_id)
    if not _can_view_saved_form(record):
        abort(403)
    form = _get_or_404(Form, record.form_id)
    schema = _schema_for_form(form)
    payload = _normalize_payload(_load_saved_form_data(record.field_data_json), schema)
    blank_mode = request.args.get('blank') == '1'
    print_mode = request.args.get('print') == '1'
    sections, role_rows = _build_preview_sections(schema, payload, blank_mode=blank_mode)
    _save_audit(record.id, 'print_preview', f'blank={blank_mode}|print={print_mode}')
    db.session.commit()
    return render_template('forms_preview.html', user=current_user, form=form, schema=schema, payload=payload, sections=sections, role_rows=role_rows, blank_mode=blank_mode, print_mode=print_mode, preview_title='Completed Form Preview' if not blank_mode else 'Blank Form Preview', generated_at=_safe_display_dt(_utcnow_naive()), saved_record=record, temp_token='', no_retention_mode=False, preview_pdf_url=url_for('forms.preview_saved_form_pdf', saved_form_id=record.id, blank='1' if blank_mode else '0', v=int(time.time())), preview_pdf_download_name=_preview_pdf_filename(form, blank_mode=blank_mode))


@bp.route('/forms/saved/<int:saved_form_id>/preview-pdf')
@login_required
def preview_saved_form_pdf(saved_form_id):
    record = _get_or_404(SavedForm, saved_form_id)
    if not _can_view_saved_form(record):
        abort(403)
    form = _get_or_404(Form, record.form_id)
    schema = _schema_for_form(form)
    payload = _normalize_payload(_load_saved_form_data(record.field_data_json), schema)
    blank_mode = request.args.get('blank') == '1'
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form), schema, payload, blank_mode=blank_mode)
    _log_pdf_render_event(form, 'preview_saved_pdf', render_meta, saved_form_id=record.id, no_retention=False)
    db.session.commit()
    return _send_ephemeral_file(pdf_path, _preview_pdf_filename(form, blank_mode=blank_mode))


@bp.route('/forms/saved/<int:saved_form_id>/email', methods=['GET', 'POST'])
@login_required
def email_saved_form(saved_form_id):
    record = _get_or_404(SavedForm, saved_form_id)
    if not _can_view_saved_form(record):
        abort(403)
    mode = (request.values.get('mode') or 'completed').strip().lower()
    if mode not in {'completed', 'blank'}:
        mode = 'completed'
    recipient, cc_list = _email_recipients_for_current_user()
    if not recipient:
        flash('Your profile email is required before sending forms. Update Profile and try again.', 'error')
        return redirect(url_for('forms.view_saved_form', saved_form_id=record.id, email='1'))
    form = db.session.get(Form, record.form_id)
    schema = _schema_for_form(form) if form else GENERIC_SCHEMA
    payload = _normalize_payload(_load_saved_form_data(record.field_data_json), schema)
    blank_mode = mode == 'blank'
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form) if form else None, schema, payload, blank_mode=blank_mode)
    pdf_bytes = b''
    try:
        with open(pdf_path, 'rb') as handle:
            pdf_bytes = handle.read()
    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
    preview_url = url_for('forms.preview_saved_form', saved_form_id=record.id, blank='1' if blank_mode else '0', _external=True)
    subject = f"{record.title or 'MCPD Form'} - {'Blank' if mode == 'blank' else 'Completed'}"
    body = f"Form: {record.title or 'MCPD Form'}\nStatus: {record.status}\nGenerated: {_safe_display_dt(_utcnow_naive())}\nPreview/Print link: {preview_url}\nCC Recipients: {', '.join(cc_list) if cc_list else 'None'}\n"
    try:
        sent, info = _smtp_send(
            recipient,
            cc_list,
            subject,
            body,
            attachment_name=f"{secure_filename(record.title or 'form')}.pdf",
            attachment_bytes=pdf_bytes or None,
        )
    except Exception as exc:
        sent, info = False, str(exc)
    if sent:
        _save_audit(record.id, 'email_sent', f'mode={mode}|recipient={recipient}|cc={len(cc_list)}')
        if form:
            _log_pdf_render_event(form, 'email_saved', render_meta, saved_form_id=record.id, no_retention=False)
        db.session.add(AuditLog(actor_id=current_user.id, action='saved_form_email', details=f'saved_form_id={record.id}|mode={mode}|recipient={recipient}|cc={len(cc_list)}'))
        db.session.commit()
        flash('Form emailed to your profile address and CC sent to Watch Commander and Desk Sgt.', 'success')
    else:
        mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body)}"
        _save_audit(record.id, 'email_fallback', f'mode={mode}|recipient={recipient}|reason={info}')
        if form:
            _log_pdf_render_event(form, 'email_saved_fallback', render_meta, saved_form_id=record.id, no_retention=False)
        db.session.commit()
        flash(f'SMTP not configured or failed. Use this fallback link in your browser: {mailto}', 'error')
    return redirect(url_for('forms.view_saved_form', saved_form_id=record.id))


@bp.route('/forms/saved/<int:saved_form_id>/download')
@login_required
def download_saved_form(saved_form_id):
    record = _get_or_404(SavedForm, saved_form_id)
    if not _can_view_saved_form(record):
        abort(403)
    if record.rendered_output_path:
        render_path = _resolve_storage_path(record.rendered_output_path)
        if render_path and os.path.exists(render_path):
            return send_file(render_path, as_attachment=True)
    form = db.session.get(Form, record.form_id)
    schema = _schema_for_form(form) if form else GENERIC_SCHEMA
    payload = _normalize_payload(_load_saved_form_data(record.field_data_json), schema)
    pdf_path, render_meta = render_form_pdf(_pdf_source_for_form(form) if form else None, schema, payload, blank_mode=False)
    if form:
        _log_pdf_render_event(form, 'download_saved', render_meta, saved_form_id=record.id, no_retention=False)
    db.session.commit()
    filename = f"{secure_filename(record.title or 'saved-form')}-{record.id}.pdf"
    return _send_ephemeral_file(pdf_path, filename)


@bp.route('/forms/pdf-renders')
@login_required
def forms_pdf_renders():
    _require_form_maintenance()
    rows = (
        AuditLog.query.filter_by(action='forms_pdf_render')
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    events = []
    for row in rows:
        details = _load_saved_form_data(row.details)
        events.append({
            'created_at': row.created_at,
            'actor_id': row.actor_id,
            'form_id': details.get('form_id'),
            'form_title': details.get('form_title') or '',
            'action': details.get('action') or '',
            'saved_form_id': details.get('saved_form_id'),
            'no_retention': bool(details.get('no_retention')),
            'mode': details.get('mode') or '',
            'mapped_count': int(details.get('mapped_count') or 0),
            'truncation_count': int(details.get('truncation_count') or 0),
            'template_id': details.get('template_id') or '',
        })
    return jsonify({
        'ok': True,
        'count': len(events),
        'events': events,
    })


@bp.route('/forms/pdf-renders/view')
@login_required
def forms_pdf_renders_view():
    _require_form_maintenance()
    form_id_filter = request.args.get('form_id', type=int)
    truncations_only = (request.args.get('truncations_only') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
    rows = (
        AuditLog.query.filter_by(action='forms_pdf_render')
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    events = []
    by_form = {}
    for row in rows:
        details = _load_saved_form_data(row.details)
        item = {
            'created_at': row.created_at,
            'actor_id': row.actor_id,
            'form_id': details.get('form_id'),
            'form_title': details.get('form_title') or '',
            'action': details.get('action') or '',
            'saved_form_id': details.get('saved_form_id'),
            'no_retention': bool(details.get('no_retention')),
            'mode': details.get('mode') or '',
            'mapped_count': int(details.get('mapped_count') or 0),
            'truncation_count': int(details.get('truncation_count') or 0),
            'template_id': details.get('template_id') or '',
        }
        if form_id_filter and int(item['form_id'] or 0) != int(form_id_filter):
            continue
        if truncations_only and item['truncation_count'] <= 0:
            continue
        events.append(item)
        form_key = f"{item['form_id']}::{item['form_title']}"
        bucket = by_form.setdefault(
            form_key,
            {
                'form_id': item['form_id'],
                'form_title': item['form_title'],
                'count': 0,
                'truncation_events': 0,
                'max_truncations': 0,
                'fillable_count': 0,
                'overlay_count': 0,
            },
        )
        bucket['count'] += 1
        if item['truncation_count'] > 0:
            bucket['truncation_events'] += 1
        bucket['max_truncations'] = max(bucket['max_truncations'], item['truncation_count'])
        if item['mode'] == 'fillable':
            bucket['fillable_count'] += 1
        elif item['mode'] == 'overlay':
            bucket['overlay_count'] += 1
    summary = sorted(
        by_form.values(),
        key=lambda x: (-x['truncation_events'], -x['count'], str(x['form_title']).lower()),
    )
    for item in summary:
        total = int(item.get('count') or 0)
        trunc = int(item.get('truncation_events') or 0)
        item['truncation_rate'] = round((trunc / total) * 100.0, 1) if total > 0 else 0.0
    risk_summary = sorted(
        [item for item in summary if int(item.get('count') or 0) >= 3],
        key=lambda x: (-x['truncation_rate'], -x['truncation_events'], -x['count']),
    )[:12]
    return render_template(
        'forms_pdf_renders.html',
        user=current_user,
        events=events,
        summary=summary,
        risk_summary=risk_summary,
        form_id_filter=form_id_filter,
        truncations_only=truncations_only,
        display_dt=_safe_display_dt,
    )


@bp.route('/forms/pdf-renders/export.csv')
@login_required
def forms_pdf_renders_export_csv():
    _require_form_maintenance()
    form_id_filter = request.args.get('form_id', type=int)
    truncations_only = (request.args.get('truncations_only') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
    rows = (
        AuditLog.query.filter_by(action='forms_pdf_render')
        .order_by(AuditLog.created_at.desc())
        .limit(500)
        .all()
    )
    events = []
    for row in rows:
        details = _load_saved_form_data(row.details)
        item = {
            'created_at': row.created_at.isoformat() if row.created_at else '',
            'actor_id': row.actor_id,
            'form_id': details.get('form_id'),
            'form_title': details.get('form_title') or '',
            'action': details.get('action') or '',
            'saved_form_id': details.get('saved_form_id'),
            'no_retention': bool(details.get('no_retention')),
            'mode': details.get('mode') or '',
            'mapped_count': int(details.get('mapped_count') or 0),
            'truncation_count': int(details.get('truncation_count') or 0),
            'template_id': details.get('template_id') or '',
        }
        if form_id_filter and int(item['form_id'] or 0) != int(form_id_filter):
            continue
        if truncations_only and item['truncation_count'] <= 0:
            continue
        events.append(item)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'created_at', 'actor_id', 'form_id', 'form_title', 'action',
        'saved_form_id', 'no_retention', 'mode', 'mapped_count',
        'truncation_count', 'template_id',
    ])
    for item in events:
        writer.writerow([
            item['created_at'],
            item['actor_id'],
            item['form_id'],
            item['form_title'],
            item['action'],
            item['saved_form_id'],
            '1' if item['no_retention'] else '0',
            item['mode'],
            item['mapped_count'],
            item['truncation_count'],
            item['template_id'],
        ])
    filename = 'forms-pdf-renders.csv'
    return current_app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
