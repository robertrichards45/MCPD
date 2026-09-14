import hashlib
import re
from copy import deepcopy

from ..services.form_field_registry import get_registry_entry


_TEXT_LIMIT = 4000
_TEXTAREA_LIMIT = 12000


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _token(value, size=12):
    raw = str(value or '').encode('utf-8')
    return hashlib.sha1(raw).hexdigest()[:size]


def _fallback_fields(document_name):
    low = _text(document_name).lower()
    if 'statement' in low:
        return [
            {'name': 'declarant_name', 'label': 'Declarant / Statement Source', 'type': 'text', 'required': True, 'status': 'TRAINING'},
            {'name': 'statement_date', 'label': 'Statement Date', 'type': 'date', 'required': True, 'status': 'TRAINING'},
            {'name': 'statement_time', 'label': 'Statement Time', 'type': 'time', 'required': False, 'status': 'TRAINING'},
            {'name': 'statement_location', 'label': 'Statement Location', 'type': 'text', 'required': True, 'status': 'TRAINING'},
            {'name': 'statement_text', 'label': 'Statement', 'type': 'textarea', 'required': True, 'status': 'TRAINING'},
            {'name': 'declarant_initials', 'label': 'Declarant Initials (Synthetic Training)', 'type': 'initial', 'required': False, 'status': 'TRAINING'},
        ]
    return [
        {'name': 'reference_number', 'label': 'Reference / Case Number', 'type': 'text', 'required': False, 'status': 'TRAINING'},
        {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True, 'status': 'TRAINING'},
        {'name': 'location', 'label': 'Location', 'type': 'text', 'required': True, 'status': 'TRAINING'},
        {'name': 'details', 'label': 'Required Details', 'type': 'textarea', 'required': True, 'status': 'TRAINING'},
        {'name': 'officer_name', 'label': 'Officer Name', 'type': 'text', 'required': False, 'status': 'TRAINING'},
    ]


def training_form_definition(document_name):
    """Return a synthetic form definition based on the controlled official field registry.

    The definition contains no operational Form/SavedForm record identifier and cannot
    itself create an official document. It is a training replica attached to a simulator run.
    """
    document_name = _text(document_name)
    entry = get_registry_entry(document_name)
    source_fields = deepcopy(entry.get('fields') or []) if entry else _fallback_fields(document_name)
    fields = []
    doc_token = _token(document_name)

    for index, raw in enumerate(source_fields):
        name = _text(raw.get('name')) or f'field_{index + 1}'
        field_type = _text(raw.get('type')).lower() or 'text'
        if field_type not in {'text', 'date', 'time', 'textarea', 'checkbox', 'signature', 'initial', 'select', 'number'}:
            field_type = 'text'
        sig_role = _text(raw.get('sig_role')).lower()
        fields.append({
            'name': name,
            'label': _text(raw.get('label')) or name,
            'type': field_type,
            'required': bool(raw.get('required')),
            'officer_only': bool(raw.get('officer_only')),
            'person_field': bool(raw.get('person_field')),
            'sig_role': sig_role,
            'mapping_status': _text(raw.get('status')) or ('TRAINING' if not entry else 'UNSPECIFIED'),
            'input_name': f'tf_{doc_token}_{index}',
            'index': index,
            'training_signature': field_type in {'signature', 'initial'},
        })

    return {
        'document_name': document_name,
        'document_id': doc_token,
        'registry_pattern': _text((entry or {}).get('form_title_pattern')),
        'source': 'official_form_field_registry' if entry else 'training_fallback_schema',
        'notes': _text((entry or {}).get('notes')),
        'fields': fields,
    }


def training_form_definitions(document_names):
    definitions = []
    seen = set()
    for name in document_names or []:
        clean = _text(name)
        key = clean.lower()
        if not clean or key in seen:
            continue
        if 'blotter' in key or 'desk journal' in key or 'desk-journal' in key:
            continue
        definitions.append(training_form_definition(clean))
        seen.add(key)
    return definitions


def _clean_value(raw, field_type):
    if field_type == 'checkbox':
        return 'Yes' if str(raw or '').strip().lower() in {'1', 'yes', 'true', 'on', 'x'} else ''
    value = str(raw or '').strip()
    limit = _TEXTAREA_LIMIT if field_type == 'textarea' else _TEXT_LIMIT
    return value[:limit]


def parse_training_form_submission(document_names, form_data):
    """Parse one immutable training-form snapshot from a Flask form-like mapping."""
    definitions = training_form_definitions(document_names)
    documents = []
    errors = []

    for definition in definitions:
        values = {}
        fields_snapshot = []
        for field in definition['fields']:
            value = _clean_value(form_data.get(field['input_name']), field['type'])
            values[field['name']] = value
            fields_snapshot.append({
                'name': field['name'],
                'label': field['label'],
                'type': field['type'],
                'required': field['required'],
                'sig_role': field['sig_role'],
                'mapping_status': field['mapping_status'],
                'value': value,
            })
            if field['required'] and not value:
                errors.append(f"{definition['document_name']}: {field['label']} is required.")

        documents.append({
            'document_name': definition['document_name'],
            'document_id': definition['document_id'],
            'registry_pattern': definition['registry_pattern'],
            'source': definition['source'],
            'fields': fields_snapshot,
            'values': values,
        })

    return documents, errors


def existing_values_by_document(submission):
    """Return latest saved form values keyed by training document id."""
    result = {}
    for item in (submission or {}).get('training_forms') or []:
        if not isinstance(item, dict):
            continue
        document_id = _text(item.get('document_id'))
        if document_id:
            result[document_id] = dict(item.get('values') or {})
    return result


def narrative_lines(text):
    raw = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in raw.split('\n') if line.strip()]
    if len(lines) <= 1 and raw.strip():
        parts = [part.strip() for part in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', raw.strip()) if part.strip()]
        if len(parts) > 1:
            lines = parts
    return [{'number': index + 1, 'text': line} for index, line in enumerate(lines)]
