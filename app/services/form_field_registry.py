"""
MCPD Form Field Registry
========================
Defines the controlled field-mapping structure for official MCPD PDF forms.

Each entry documents:
  - form_title_pattern : substring matched against Form.title (case-insensitive)
  - pdf_filename_hint  : optional fragment of the uploaded filename for disambiguation
  - fields             : list of field descriptors

Field descriptor keys:
  name          : schema/form field name (maps to payload['values'][name])
  label         : human-readable label shown in the fill UI
  type          : 'text' | 'date' | 'time' | 'textarea' | 'checkbox' |
                  'signature' | 'initial' | 'select' | 'number'
  required      : True if the form cannot be finalised without this field
  officer_only  : True if only the responding/submitting officer fills this
  person_field  : True if the value comes from an involved person (victim/suspect/etc.)
  date_field    : True if the value is a date (redundant with type=='date' but
                  useful for programmatic queries)
  sig_role      : (signature/initial only) who signs — 'officer' | 'subject' |
                  'victim' | 'witness' | 'supervisor'
  pdf_field_name: actual AcroForm / XFA field name in the source PDF.
                  Empty string means coordinate mapping is still needed.
  notes         : free-text notes for future coordinate mapping work

STATUS KEY
----------
  MAPPED      — field_name confirmed against live PDF; rendering tested
  PARTIAL     — field_name guessed from PDF debug output; needs confirmation
  PLACEHOLDER — field exists in schema but PDF coordinate not yet mapped
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Registry data
# ---------------------------------------------------------------------------

_REGISTRY: list[dict[str, Any]] = [

    # ── MCPD Stat Sheet ────────────────────────────────────────────────────
    {
        'form_title_pattern': 'stat sheet',
        'pdf_filename_hint': 'stat_sheet',
        'fields': [
            {'name': 'report_date',        'label': 'Report Date',         'type': 'date',      'required': True,  'officer_only': True},
            {'name': 'reporting_officer',  'label': 'Reporting Officer',   'type': 'text',      'required': True,  'officer_only': True},
            {'name': 'shift',              'label': 'Shift',               'type': 'text',      'required': True,  'officer_only': True},
            {'name': 'watch_commander',    'label': 'Watch Commander',     'type': 'text',      'required': False, 'officer_only': True},
            {'name': 'calls_for_service',  'label': 'Calls for Service',   'type': 'number',    'required': False, 'officer_only': True},
            {'name': 'adult_arrests',      'label': 'Adult Arrests',       'type': 'number',    'required': False, 'officer_only': True},
            {'name': 'notable_incidents',  'label': 'Notable Incidents',   'type': 'textarea',  'required': False, 'officer_only': True},
        ],
        'notes': 'No-retention form. Signatures not applicable for stat sheet.',
    },

    # ── OPNAV 5580-2 Voluntary Statement ──────────────────────────────────
    {
        'form_title_pattern': 'voluntary statement',
        'pdf_filename_hint': 'opnav_5580_2',
        'fields': [
            {'name': 'VicName',      'label': 'Name',             'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'form1.VicName',    'status': 'PARTIAL'},
            {'name': 'Date',         'label': 'Date',             'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': 'form1.Date',       'status': 'PARTIAL'},
            {'name': 'RespTime',     'label': 'Time',             'type': 'time',      'required': True,                         'pdf_field_name': 'form1.RespTime',   'status': 'PARTIAL'},
            {'name': 'Location',     'label': 'Location',         'type': 'text',      'required': True,                         'pdf_field_name': 'form1.Location',   'status': 'PARTIAL'},
            {'name': 'Statement',    'label': 'Statement',        'type': 'textarea',  'required': True,  'person_field': True,  'pdf_field_name': '',                 'status': 'PLACEHOLDER'},
            {'name': 'Initials',     'label': 'Declarant Initials','type': 'initial',  'required': False, 'sig_role': 'subject', 'pdf_field_name': '',                 'status': 'PLACEHOLDER',
             'notes': 'Needs coordinate mapping — appears at page bottom alongside each paragraph.'},
            {'name': 'Signature',    'label': 'Declarant Signature','type': 'signature','required': False,'sig_role': 'subject', 'pdf_field_name': '',                 'status': 'PLACEHOLDER',
             'notes': 'Needs coordinate mapping — bottom of last page near SUBSCRIBED AND SWORN block.'},
            {'name': 'WitnessSign',  'label': 'Witness Signature','type': 'signature', 'required': False, 'sig_role': 'witness', 'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER',
             'notes': 'Needs coordinate mapping — adjacent to declarant signature block.'},
            {'name': 'OfficerSign',  'label': 'Officer Signature','type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
        ],
        'notes': (
            'XFA dynamic form — rendered via xfa_sectioned path. '
            'Signature/initial fields need exact XFA layout coordinates before live placement. '
            'Current render places them in allocated boxes within the sectioned output.'
        ),
    },

    # ── NAVMAC 11337 Domestic Violence Supplement ─────────────────────────
    {
        'form_title_pattern': 'domestic violence',
        'pdf_filename_hint': 'navmac_11337',
        'fields': [
            {'name': 'VicName',        'label': 'Victim Name',          'type': 'text',  'required': True,  'person_field': True,  'pdf_field_name': 'form1.VicName',        'status': 'MAPPED'},
            {'name': 'ResponseDate',   'label': 'Response Date',        'type': 'date',  'required': True,  'date_field': True,    'pdf_field_name': 'form1.ResponseDate',   'status': 'MAPPED'},
            {'name': 'RespTime',       'label': 'Response Time',        'type': 'time',  'required': True,                         'pdf_field_name': 'form1.RespTime',       'status': 'MAPPED'},
            {'name': 'Reported',       'label': 'Violation Reported',   'type': 'text',  'required': True,                         'pdf_field_name': 'form1.Reported',       'status': 'MAPPED'},
            {'name': 'SupInitial1',    'label': 'Supervisor Initials 1','type': 'initial','required': False, 'sig_role': 'supervisor','pdf_field_name': 'SupInitial.1',       'status': 'PARTIAL',
             'notes': 'XFA named node — coordinate placement needed.'},
            {'name': 'SupInitial2',    'label': 'Supervisor Initials 2','type': 'initial','required': False, 'sig_role': 'supervisor','pdf_field_name': 'SupInitial.2',       'status': 'PARTIAL'},
            {'name': 'SupInitial4',    'label': 'Supervisor Initials 4','type': 'initial','required': False, 'sig_role': 'supervisor','pdf_field_name': 'SupInitial.4',       'status': 'PARTIAL'},
            {'name': 'SupInitial7',    'label': 'Supervisor Initials 7','type': 'initial','required': False, 'sig_role': 'supervisor','pdf_field_name': 'SupInitial.7',       'status': 'PARTIAL'},
            {'name': 'OfficerSign',    'label': 'Officer Signature',    'type': 'signature','required': False,'sig_role': 'officer','officer_only': True,'pdf_field_name': '','status': 'PLACEHOLDER'},
        ],
        'notes': 'Mobile-native domestic supplemental flow in incident-core.js captures key fields directly.',
    },

    # ── NAVMC 11130 Use of Force / Detention ──────────────────────────────
    {
        'form_title_pattern': 'use of detention',
        'pdf_filename_hint': 'navmc_11130',
        'fields': [
            {'name': 'OfficerName',    'label': 'Officer Name',     'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Date',           'label': 'Date',             'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'SubjectName',    'label': 'Subject Name',     'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Location',       'label': 'Location',         'type': 'text',      'required': True,                         'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'ForceType',      'label': 'Type of Force',    'type': 'textarea',  'required': True,                         'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Justification',  'label': 'Justification',    'type': 'textarea',  'required': True,                         'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'OfficerSign',    'label': 'Officer Signature','type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'SupervisorSign', 'label': 'Supervisor Signature','type': 'signature','required': False,'sig_role': 'supervisor','officer_only': True,'pdf_field_name': '','status': 'PLACEHOLDER'},
        ],
        'notes': 'All fields are PLACEHOLDER — run /forms/<id>/pdf-debug to extract XFA field names and coordinates.',
    },

    # ── DD Form 2701 VWAP ─────────────────────────────────────────────────
    {
        'form_title_pattern': 'vwap',
        'pdf_filename_hint': 'dd_form_2701',
        'fields': [
            {'name': 'VictimName',  'label': 'Victim Name',      'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'CaseNumber',  'label': 'Case Number',      'type': 'text',      'required': False,                        'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Date',        'label': 'Date',             'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'OfficerName', 'label': 'Officer Name',     'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'OfficerSign', 'label': 'Officer Signature','type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'VictimSign',  'label': 'Victim Signature', 'type': 'signature', 'required': False, 'sig_role': 'victim',  'person_field': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
        ],
        'notes': 'AcroForm PDF — run /forms/<id>/pdf-debug to extract field names and rects for coordinate mapping.',
    },

    # ── SF 91 Motor Vehicle Accident ──────────────────────────────────────
    {
        'form_title_pattern': 'motor vehicle accident',
        'pdf_filename_hint': 'sf_91',
        'fields': [
            {'name': 'Date',         'label': 'Date of Accident',  'type': 'date',  'required': True,  'date_field': True,   'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Time',         'label': 'Time of Accident',  'type': 'time',  'required': True,                        'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Location',     'label': 'Location',          'type': 'text',  'required': True,                        'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Driver1Name',  'label': 'Driver 1 Name',     'type': 'text',  'required': True,  'person_field': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Driver2Name',  'label': 'Driver 2 Name',     'type': 'text',  'required': False, 'person_field': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Description',  'label': 'Accident Description','type': 'textarea','required': True,                   'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'OfficerSign',  'label': 'Officer Signature', 'type': 'signature','required': False,'sig_role': 'officer','officer_only': True,'pdf_field_name': '','status': 'PLACEHOLDER'},
            {'name': 'Driver1Sign',  'label': 'Driver 1 Signature','type': 'signature','required': False,'sig_role': 'subject','person_field': True,'pdf_field_name': '','status': 'PLACEHOLDER'},
        ],
        'notes': 'AcroForm PDF. Run pdf-debug to extract field rects before coordinate mapping.',
    },

    # ── OPNAV 5580-22 Evidence Custody Document ───────────────────────────
    {
        'form_title_pattern': 'evidence custody',
        'pdf_filename_hint': 'opnav_5580_22',
        'fields': [
            {'name': 'CaseNumber',     'label': 'Case Number',       'type': 'text',  'required': True,                        'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Date',           'label': 'Date',              'type': 'date',  'required': True,  'date_field': True,   'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'ItemDesc',       'label': 'Item Description',  'type': 'textarea','required': True,                      'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'CollectedBy',    'label': 'Collected By',      'type': 'text',  'required': True,  'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'CollectorSign',  'label': 'Collector Signature','type': 'signature','required': False,'sig_role': 'officer','officer_only': True,'pdf_field_name': '','status': 'PLACEHOLDER'},
            {'name': 'CustodianSign',  'label': 'Custodian Signature','type': 'signature','required': False,'sig_role': 'supervisor','officer_only': True,'pdf_field_name': '','status': 'PLACEHOLDER'},
        ],
        'notes': 'Chain of custody form. Both signatures required before evidence is logged.',
    },
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def get_registry_entry(form_title: str) -> dict | None:
    """Return the registry entry whose form_title_pattern matches form_title."""
    key = _normalize(form_title)
    for entry in _REGISTRY:
        if _normalize(entry.get('form_title_pattern', '')) in key:
            return entry
    return None


def get_signature_fields(form_title: str) -> list[dict]:
    """Return all signature and initial field descriptors for a given form title."""
    entry = get_registry_entry(form_title)
    if not entry:
        return []
    return [f for f in entry.get('fields', []) if f.get('type') in ('signature', 'initial')]


def get_required_fields(form_title: str) -> list[dict]:
    """Return all required field descriptors for a given form title."""
    entry = get_registry_entry(form_title)
    if not entry:
        return []
    return [f for f in entry.get('fields', []) if f.get('required')]


def classify_field(field_name: str, field_label: str = '') -> str:
    """
    Classify a field as 'signature', 'initial', 'date', 'textarea', or 'text'
    based on name/label heuristics. Used by _pdf_field_ui_type as a fallback.
    """
    combined = f'{field_name} {field_label}'.lower()
    if 'signature' in combined or combined.endswith('sign') or combined.endswith('sig'):
        return 'signature'
    if 'initial' in combined or 'initials' in combined or 'supinit' in combined:
        return 'initial'
    if any(tok in combined for tok in ('date', 'dob', 'birthdate', 'expir')):
        return 'date'
    if any(tok in combined for tok in ('statement', 'description', 'remarks', 'notes', 'details', 'explain')):
        return 'textarea'
    return 'text'


def fields_needing_coordinate_mapping() -> list[dict]:
    """
    Return all field descriptors across all registry entries where
    pdf_field_name is empty (coordinate mapping still required).
    Useful for generating a mapping TODO list.
    """
    todo = []
    for entry in _REGISTRY:
        for field in entry.get('fields', []):
            if field.get('type') in ('signature', 'initial') and not field.get('pdf_field_name'):
                todo.append({
                    'form': entry.get('form_title_pattern'),
                    'field_name': field.get('name'),
                    'label': field.get('label'),
                    'type': field.get('type'),
                    'sig_role': field.get('sig_role', ''),
                    'status': field.get('status', 'PLACEHOLDER'),
                    'notes': field.get('notes', ''),
                })
    return todo
