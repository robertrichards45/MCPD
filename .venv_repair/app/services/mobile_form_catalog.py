from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from flask import url_for

from .form_metadata_ai import normalize_form_family
from .forms_pdf_renderer import inspect_pdf_fields, inspect_xfa_fields


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_storage_path(path: str | None) -> str:
    candidate = str(path or '').strip()
    if not candidate:
        return ''
    if os.path.isabs(candidate):
        return os.path.abspath(candidate)
    normalized = candidate.replace('/', os.sep).replace('\\', os.sep).lstrip('.\\/')
    return os.path.abspath(_repo_root() / normalized)


def _normalize_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def _humanize(value: str) -> str:
    text = str(value or '').replace('_', ' ').replace('-', ' ')
    text = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', text)
    text = ' '.join(text.split())
    return text.strip().title() or 'Field'


def _actionable_acro_fields(fields: list[dict]) -> list[dict]:
    actionable = []
    for item in fields:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        field_type = str(item.get('type') or '').strip()
        if not name or field_type not in {'/Btn', '/Tx', '/Ch', '/Sig'}:
            continue
        actionable.append({
            'name': name,
            'raw_name': name,
            'label': _humanize(name),
            'type': field_type,
            'group_names': [],
        })
    return actionable


def _field_metrics(fields: list[dict]) -> dict[str, int]:
    checkbox_count = 0
    text_count = 0
    signature_count = 0
    initial_count = 0
    for field in fields:
        field_type = str(field.get('type') or '')
        label = str(field.get('label') or '').lower()
        raw_name = str(field.get('raw_name') or field.get('name') or '').lower()
        if field_type in {'/Btn', 'checkbox'}:
            checkbox_count += 1
        elif field_type in {'/Sig', 'signature'}:
            signature_count += 1
        else:
            text_count += 1
        if 'initial' in raw_name or 'initial' in label:
            initial_count += 1
    return {
        'checkboxes': checkbox_count,
        'texts': text_count,
        'signatures': signature_count,
        'initials': initial_count,
    }


def _domestic_section_summaries(fields: list[dict]) -> list[dict]:
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
        if raw_name and raw_name not in index_lookup:
            index_lookup[raw_name] = index
    sections = []
    ordered_boundaries = []
    for title, raw_name in section_specs:
        start = index_lookup.get(raw_name)
        if start is None:
            continue
        ordered_boundaries.append((title, start))
    ordered_boundaries.sort(key=lambda item: item[1])
    for index, (title, start) in enumerate(ordered_boundaries):
        end = ordered_boundaries[index + 1][1] if index + 1 < len(ordered_boundaries) else len(fields)
        section_fields = fields[start:end]
        sections.append({
            'title': title,
            'fieldCount': len(section_fields),
            'sampleLabels': [str(item.get('label') or '') for item in section_fields[:4] if str(item.get('label') or '')],
        })
    return sections


def _generic_section_summaries(form) -> list[dict]:
    from ..routes.forms import _schema_for_form

    schema = _schema_for_form(form)
    sections = []
    for section in schema.get('sections', []):
        fields = section.get('fields') if isinstance(section.get('fields'), list) else []
        if not fields:
            continue
        sections.append({
            'title': str(section.get('title') or 'Form Fields'),
            'fieldCount': len(fields),
            'sampleLabels': [str(field.get('label') or '') for field in fields[:4] if str(field.get('label') or '')],
        })
    return sections


def _inspect_form_structure(form) -> dict:
    source_path = _resolve_storage_path(getattr(form, 'file_path', ''))
    if not source_path or not os.path.exists(source_path):
        return {
            'sourceKind': 'missing',
            'fields': [],
            'conditionalGroups': [],
            'sectionSummaries': [],
        }

    try:
        acro_info = inspect_pdf_fields(source_path)
        acro_fields = _actionable_acro_fields(acro_info.get('fields', []))
    except Exception:
        acro_fields = []

    if acro_fields:
        return {
            'sourceKind': 'acroform',
            'fields': acro_fields,
            'conditionalGroups': [],
            'sectionSummaries': _generic_section_summaries(form),
        }

    try:
        xfa_info = inspect_xfa_fields(source_path)
        xfa_fields = xfa_info.get('fields', []) if isinstance(xfa_info.get('fields'), list) else []
        if xfa_fields:
            title_key = _normalize_key(getattr(form, 'title', ''))
            if 'domesticviolence' in title_key:
                sections = _domestic_section_summaries(xfa_fields)
            else:
                sections = _generic_section_summaries(form)
                if not sections:
                    sections = [{
                        'title': 'Mapped XFA Fields',
                        'fieldCount': len(xfa_fields),
                        'sampleLabels': [str(field.get('label') or '') for field in xfa_fields[:4] if str(field.get('label') or '')],
                    }]
            return {
                'sourceKind': 'xfa',
                'fields': xfa_fields,
                'conditionalGroups': xfa_info.get('conditional_groups', []),
                'sectionSummaries': sections,
            }
    except Exception:
        pass

    return {
        'sourceKind': 'static',
        'fields': [],
        'conditionalGroups': [],
        'sectionSummaries': [],
    }


def _forms_cache_key(forms) -> tuple[tuple[int, str, str, str], ...]:
    return tuple(
        (
            int(getattr(form, 'id', 0) or 0),
            str(getattr(form, 'title', '') or ''),
            str(getattr(form, 'category', '') or ''),
            str(getattr(form, 'file_path', '') or ''),
        )
        for form in forms or []
    )


@lru_cache(maxsize=8)
def _build_static_mobile_form_catalog(forms_key: tuple[tuple[int, str, str, str], ...]) -> tuple[dict, ...]:
    from ..routes.forms import _form_fill_state, _schema_for_form

    catalog = []
    for form_id, title, category, file_path in forms_key:
        form = SimpleNamespace(id=form_id, title=title, category=category, file_path=file_path)
        structure = _inspect_form_structure(form)
        fields = structure['fields']
        metrics = _field_metrics(fields)
        schema = _schema_for_form(form)
        fill_state = _form_fill_state(form, schema)
        catalog.append({
            'id': form_id,
            'title': title,
            'category': category or 'General',
            'familyKey': normalize_form_family(title),
            'sourceKind': structure['sourceKind'],
            'fieldCount': len(fields),
            'checkboxCount': metrics['checkboxes'],
            'textCount': metrics['texts'],
            'signatureCount': metrics['signatures'],
            'initialCount': metrics['initials'],
            'conditionalGroupCount': len(structure['conditionalGroups']),
            'sectionSummaries': structure['sectionSummaries'],
            'mappingNote': (
                'XFA field map extracted from the live domestic supplemental package.'
                if structure['sourceKind'] == 'xfa'
                else 'PDF-backed field map extracted from the live form file.'
            ),
            'isReady': bool(fill_state.get('is_ready')),
        })
    return tuple(sorted(catalog, key=lambda item: (str(item['category']).lower(), str(item['title']).lower())))


def build_mobile_form_catalog(forms, latest_saved_by_form: dict[int, object]) -> list[dict]:
    catalog = []
    form_lookup = {int(getattr(form, 'id', 0) or 0): form for form in forms or []}
    static_catalog = _build_static_mobile_form_catalog(_forms_cache_key(forms))
    for base_record in static_catalog:
        form_id = int(base_record['id'])
        form = form_lookup.get(form_id)
        latest_saved = latest_saved_by_form.get(form_id)
        status = str(getattr(latest_saved, 'status', '') or '').strip().upper() or 'NOT_STARTED'
        preview_url = (
            url_for('forms.preview_saved_form', saved_form_id=latest_saved.id)
            if latest_saved
            else url_for('forms.blank_form_preview', form_id=form.id)
        )
        record = dict(base_record)
        record.update({
            'status': status,
            'statusLabel': status.replace('_', ' ').title(),
            'latestSavedFormId': getattr(latest_saved, 'id', None),
            'editUrl': url_for('forms.fill_form', form_id=form.id, saved_form_id=getattr(latest_saved, 'id', None)) if latest_saved else url_for('forms.fill_form', form_id=form.id),
            'previewUrl': preview_url,
            'downloadUrl': url_for('forms.download_form', form_id=form.id),
            'previewMode': 'saved' if latest_saved else 'blank',
        })
        catalog.append(record)
    return sorted(catalog, key=lambda item: (str(item['category']).lower(), str(item['title']).lower()))
