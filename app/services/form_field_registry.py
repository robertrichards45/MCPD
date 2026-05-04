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

    # ── OPNAV 5580-2 Voluntary Statement (Traffic variant) ────────────────
    # Must appear BEFORE the generic voluntary statement entry so traffic forms
    # match the more-specific pattern first.
    {
        'form_title_pattern': 'voluntary statement traffic',
        'pdf_filename_hint': 'opnav_5580_2_voluntary_statement_traffic',
        'fields': [
            {'name': 'CCN',          'label': 'CCN / Case Number',    'type': 'text',     'required': False,                        'pdf_field_name': 'CCN',         'status': 'MAPPED'},
            {'name': '1 PLACE',      'label': 'Place',                'type': 'text',     'required': True,                         'pdf_field_name': '1 PLACE',     'status': 'MAPPED'},
            {'name': '2 DATE',       'label': 'Date',                 'type': 'date',     'required': True,  'date_field': True,    'pdf_field_name': '2 DATE',      'status': 'MAPPED'},
            {'name': 'I Name',       'label': 'Name of Declarant',    'type': 'text',     'required': True,  'person_field': True,  'pdf_field_name': 'I Name',      'status': 'MAPPED'},
            {'name': 'SSN',          'label': 'SSN',                  'type': 'text',     'required': False, 'person_field': True,  'pdf_field_name': 'SSN',         'status': 'MAPPED'},
            {'name': 'free and voluntary statement to', 'label': 'Statement Given To (Officer)', 'type': 'text', 'required': True, 'officer_only': True,
             'pdf_field_name': 'free and voluntary statement to', 'status': 'MAPPED'},
            {'name': 'concerning my knowledge of a Traffic Accident that occurred on Date',
             'label': 'Date of Traffic Accident',  'type': 'date',     'required': True,  'date_field': True,
             'pdf_field_name': 'concerning my knowledge of a Traffic Accident that occurred on Date', 'status': 'MAPPED'},
            {'name': 'Time',         'label': 'Time of Accident',     'type': 'time',     'required': True,                         'pdf_field_name': 'Time',        'status': 'MAPPED'},
            {'name': 'A',            'label': 'Statement (Page 1)',   'type': 'textarea', 'required': True,  'person_field': True,  'pdf_field_name': 'A',           'status': 'MAPPED'},
            {'name': 'Initials of person making statement', 'label': 'Declarant Initials', 'type': 'initial', 'required': False,
             'sig_role': 'subject', 'pdf_field_name': 'Initials of person making statement', 'status': 'MAPPED'},
        ],
        'notes': 'AcroForm PDF. Traffic-specific variant of OPNAV 5580-2.',
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
        'notes': 'PDF is AES-encrypted — run /forms/<id>/pdf-debug to extract XFA field names after providing the decryption key.',
    },

    # ── OPNAV 5580-3 Military Suspect's Rights ────────────────────────────
    {
        'form_title_pattern': 'military suspect',
        'pdf_filename_hint': 'opnav_5580_3',
        'fields': [
            {'name': 'Place 1',          'label': 'Location (Line 1)',       'type': 'text',      'required': True,                         'pdf_field_name': 'Place 1',          'status': 'MAPPED'},
            {'name': 'Place 2',          'label': 'Location (Line 2)',       'type': 'text',      'required': False,                        'pdf_field_name': 'Place 2',          'status': 'MAPPED'},
            {'name': 'I',                'label': 'Subject Name',            'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'I',                'status': 'MAPPED'},
            {'name': 'have been advised by', 'label': 'Advised By (Officer)','type': 'text',     'required': True,  'officer_only': True,  'pdf_field_name': 'have been advised by', 'status': 'MAPPED'},
            {'name': 'that I am suspected of', 'label': 'Suspected Offense', 'type': 'text',     'required': True,                         'pdf_field_name': 'that I am suspected of', 'status': 'MAPPED'},
            {'name': 'At this time I',   'label': 'Decision (waive/invoke rights)', 'type': 'text', 'required': True,                      'pdf_field_name': 'At this time I',   'status': 'MAPPED'},
            {'name': 'Date  Time',       'label': 'Date/Time Rights Read',   'type': 'text',      'required': True,                         'pdf_field_name': 'Date  Time',       'status': 'MAPPED'},
            {'name': 'Date  Time_2',     'label': 'Date/Time Signed',        'type': 'text',      'required': False,                        'pdf_field_name': 'Date  Time_2',     'status': 'MAPPED'},
            {'name': 'Statement Line 1', 'label': 'Statement (Line 1)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 1', 'status': 'MAPPED'},
            {'name': 'Statement Line 2', 'label': 'Statement (Line 2)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 2', 'status': 'MAPPED'},
            {'name': 'Statement Line 3', 'label': 'Statement (Line 3)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 3', 'status': 'MAPPED'},
            {'name': 'Statement Line 4', 'label': 'Statement (Line 4)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 4', 'status': 'MAPPED'},
            {'name': 'Statement Line 5', 'label': 'Statement (Line 5)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 5', 'status': 'MAPPED'},
            {'name': 'Statement Line 6', 'label': 'Statement (Line 6)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 6', 'status': 'MAPPED'},
            {'name': 'Witnessed 1',      'label': 'Witness 1',               'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'Witnessed 1',      'status': 'MAPPED'},
            {'name': 'Witnessed 2',      'label': 'Witness 2',               'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'Witnessed 2',      'status': 'MAPPED'},
            {'name': 'Signature',        'label': 'Subject Signature',       'type': 'signature', 'required': False, 'sig_role': 'subject', 'pdf_field_name': 'Signature',        'status': 'MAPPED'},
        ],
        'notes': 'AcroForm PDF. All text field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-4 Civilian Suspect's Rights ────────────────────────────
    {
        'form_title_pattern': 'civilian suspect',
        'pdf_filename_hint': 'opnav_5580_4',
        'fields': [
            {'name': 'Place 1',          'label': 'Location (Line 1)',       'type': 'text',      'required': True,                         'pdf_field_name': 'Place 1',          'status': 'MAPPED'},
            {'name': 'Place 2',          'label': 'Location (Line 2)',       'type': 'text',      'required': False,                        'pdf_field_name': 'Place 2',          'status': 'MAPPED'},
            {'name': 'I',                'label': 'Subject Name',            'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'I',                'status': 'MAPPED'},
            {'name': 'have been advised by', 'label': 'Advised By (Officer)','type': 'text',     'required': True,  'officer_only': True,  'pdf_field_name': 'have been advised by', 'status': 'MAPPED'},
            {'name': 'that I am suspected of', 'label': 'Suspected Offense', 'type': 'text',     'required': True,                         'pdf_field_name': 'that I am suspected of', 'status': 'MAPPED'},
            {'name': 'At this time I',   'label': 'Decision (waive/invoke rights)', 'type': 'text', 'required': True,                      'pdf_field_name': 'At this time I',   'status': 'MAPPED'},
            {'name': 'Date  Time',       'label': 'Date/Time Rights Read',   'type': 'text',      'required': True,                         'pdf_field_name': 'Date  Time',       'status': 'MAPPED'},
            {'name': 'Date  Time_2',     'label': 'Date/Time Signed',        'type': 'text',      'required': False,                        'pdf_field_name': 'Date  Time_2',     'status': 'MAPPED'},
            {'name': 'Statement Line 1', 'label': 'Statement (Line 1)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 1', 'status': 'MAPPED'},
            {'name': 'Statement Line 2', 'label': 'Statement (Line 2)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 2', 'status': 'MAPPED'},
            {'name': 'Statement Line 3', 'label': 'Statement (Line 3)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 3', 'status': 'MAPPED'},
            {'name': 'Statement Line 4', 'label': 'Statement (Line 4)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 4', 'status': 'MAPPED'},
            {'name': 'Statement Line 5', 'label': 'Statement (Line 5)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 5', 'status': 'MAPPED'},
            {'name': 'Statement Line 6', 'label': 'Statement (Line 6)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 6', 'status': 'MAPPED'},
            {'name': 'Statement Line 7', 'label': 'Statement (Line 7)',      'type': 'text',      'required': False, 'person_field': True,
             'pdf_field_name': 'forth above It is made with no threats or promises having been extended to me 7', 'status': 'MAPPED'},
            {'name': 'Witnessed 1',      'label': 'Witness 1',               'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'Witnessed 1',      'status': 'MAPPED'},
            {'name': 'Witnessed 2',      'label': 'Witness 2',               'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'Witnessed 2',      'status': 'MAPPED'},
            {'name': 'Signature',        'label': 'Subject Signature',       'type': 'signature', 'required': False, 'sig_role': 'subject', 'pdf_field_name': 'Signature',        'status': 'MAPPED'},
        ],
        'notes': 'AcroForm PDF. All text field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-8 Telephonic Threat Complaint ──────────────────────────
    {
        'form_title_pattern': 'telephonic threat',
        'pdf_filename_hint': 'opnav_5580-8',
        'fields': [
            {'name': 'nameadd',       'label': 'Name / Address of Location',  'type': 'text',      'required': True,                         'pdf_field_name': 'F[0].P1[0].nameadd[0]',       'status': 'MAPPED'},
            {'name': 'Telephone',     'label': 'Telephone Number Called',     'type': 'text',      'required': True,                         'pdf_field_name': 'F[0].P1[0].Telephone[0]',     'status': 'MAPPED'},
            {'name': 'comname',       'label': 'Command Name',                'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'F[0].P1[0].comname[0]',       'status': 'MAPPED'},
            {'name': 'pername',       'label': 'Person Notified',             'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'F[0].P1[0].pername[0]',       'status': 'MAPPED'},
            {'name': 'commname',      'label': 'Commanding Officer',          'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'F[0].P1[0].commname[0]',      'status': 'MAPPED'},
            {'name': 'date1',         'label': 'Date/Time of Call',           'type': 'text',      'required': True,                         'pdf_field_name': 'F[0].P1[0].date1[0]',         'status': 'MAPPED'},
            {'name': 'place',         'label': 'Place',                       'type': 'text',      'required': True,                         'pdf_field_name': 'F[0].P1[0].place[0]',         'status': 'MAPPED'},
            {'name': 'LOCO',          'label': 'Location',                    'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].LOCO[0]',          'status': 'MAPPED'},
            {'name': 'date2',         'label': 'Date Reported',               'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': 'F[0].P1[0].date2[0]',         'status': 'MAPPED'},
            {'name': 'hourtime',      'label': 'Time of Call',                'type': 'time',      'required': True,                         'pdf_field_name': 'F[0].P1[0].hourtime[0]',      'status': 'MAPPED'},
            {'name': 'hometelephone', 'label': 'Home Telephone',              'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].hometelephone[0]', 'status': 'MAPPED'},
            {'name': 'worktelephone', 'label': 'Work Telephone',              'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].worktelephone[0]', 'status': 'MAPPED'},
            {'name': 'contextname1',  'label': 'Exact Words of Threat (1)',   'type': 'text',      'required': True,                         'pdf_field_name': 'F[0].P1[0].contextname1[0]',  'status': 'MAPPED'},
            {'name': 'contextname2',  'label': 'Exact Words of Threat (2)',   'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].contextname2[0]',  'status': 'MAPPED'},
            {'name': 'contextname3',  'label': 'Exact Words of Threat (3)',   'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].contextname3[0]',  'status': 'MAPPED'},
            {'name': 'contextname4',  'label': 'Exact Words of Threat (4)',   'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].contextname4[0]',  'status': 'MAPPED'},
            {'name': 'contextname5',  'label': 'Exact Words of Threat (5)',   'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].contextname5[0]',  'status': 'MAPPED'},
            {'name': 'contextname6',  'label': 'Exact Words of Threat (6)',   'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].contextname6[0]',  'status': 'MAPPED'},
            {'name': 'background',    'label': 'Background Noise',            'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].background[0]',    'status': 'MAPPED'},
            {'name': 'age',           'label': 'Caller Age',                  'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].age[0]',           'status': 'MAPPED'},
            {'name': 'edulevel',      'label': 'Education Level',             'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].edulevel[0]',      'status': 'MAPPED'},
            {'name': 'accent',        'label': 'Accent',                      'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].accent[0]',        'status': 'MAPPED'},
            {'name': 'attitude',      'label': 'Attitude',                    'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].attitude[0]',      'status': 'MAPPED'},
            {'name': 'other1',        'label': 'Other Caller Description',    'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].other1[0]',        'status': 'MAPPED'},
            {'name': 'witname',       'label': 'Witness Name',                'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].witname[0]',       'status': 'MAPPED'},
            {'name': 'identname',     'label': 'Identity (if known)',         'type': 'text',      'required': False,                        'pdf_field_name': 'F[0].P1[0].identname[0]',     'status': 'MAPPED'},
        ],
        'notes': 'XFA PDF. All field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-9 Command Search Authorization ─────────────────────────
    {
        'form_title_pattern': 'command search authorization',
        'pdf_filename_hint': 'opnav_5580-9',
        'fields': [
            {'name': 'NameOfPerson',          'label': 'Name of Person to be Searched',  'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].NameOfPerson[0]',          'status': 'MAPPED'},
            {'name': 'To',                    'label': 'Authorized To (Officer Name)',   'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].To[0]',                    'status': 'MAPPED'},
            {'name': 'PremisisDetail',        'label': 'Premises Description',           'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].PremisisDetail[0]',        'status': 'MAPPED'},
            {'name': 'DescribeProperty',      'label': 'Property / Evidence to Seize',  'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].DescribeProperty[0]',      'status': 'MAPPED'},
            {'name': 'Affidavit',             'label': 'Affidavit / Probable Cause',    'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Affidavit[0]',             'status': 'MAPPED'},
            {'name': 'Day',                   'label': 'Day',                            'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Day[0]',                   'status': 'MAPPED'},
            {'name': 'Month',                 'label': 'Month',                          'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Month[0]',                 'status': 'MAPPED'},
            {'name': 'Year',                  'label': 'Year',                           'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Year[0]',                  'status': 'MAPPED'},
            {'name': 'Command',               'label': 'Command',                        'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].Command[0]',               'status': 'MAPPED'},
            {'name': 'RankSerTitle',          'label': 'Rank / Serial / Title',          'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].RankSerTitle[0]',          'status': 'MAPPED'},
            {'name': 'SignatureAuthorization','label': 'Authorizing Signature',          'type': 'signature', 'required': False, 'sig_role': 'officer', 'pdf_field_name': 'form1[0].#subform[0].SignatureAuthorization[0]','status': 'MAPPED'},
        ],
        'notes': 'XFA PDF. All field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-10 Affidavit for Search and Seizure ────────────────────
    {
        'form_title_pattern': 'affidavit for search',
        'pdf_filename_hint': 'opnav_5580-10',
        'fields': [
            {'name': 'Rank',           'label': 'Rank / Grade / Title',          'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].Rank[0]',          'status': 'MAPPED'},
            {'name': 'Who',            'label': 'Name of Affiant',               'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].Who[0]',            'status': 'MAPPED'},
            {'name': 'Personbytitle',  'label': 'Person by Title',               'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].Personbytitle[0]', 'status': 'MAPPED'},
            {'name': 'Property',       'label': 'Property / Evidence Sought',    'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Property[0]',      'status': 'MAPPED'},
            {'name': 'Auth',           'label': 'Location to be Searched',       'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Auth[0]',           'status': 'MAPPED'},
            {'name': 'Request',        'label': 'Request / Probable Cause',      'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Request[0]',       'status': 'MAPPED'},
            {'name': 'AddOath',        'label': 'Additional Oath Details',       'type': 'textarea',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].AddOath[0]',       'status': 'MAPPED'},
            {'name': 'Day',            'label': 'Day',                            'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Day[0]',            'status': 'MAPPED'},
            {'name': 'Month',          'label': 'Month',                          'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Month[0]',          'status': 'MAPPED'},
            {'name': 'Year',           'label': 'Year',                           'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Year[0]',           'status': 'MAPPED'},
            {'name': 'SigAff',         'label': 'Affiant Signature',             'type': 'signature', 'required': False, 'sig_role': 'officer', 'pdf_field_name': 'form1[0].#subform[0].SigAff[0]',        'status': 'MAPPED'},
        ],
        'notes': 'XFA PDF. All field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-11 Complaint of Stolen Motor Vehicle ───────────────────
    {
        'form_title_pattern': 'stolen motor vehicle',
        'pdf_filename_hint': 'opnav_5580-11',
        'fields': [
            {'name': 'Date1',              'label': 'Date Received',              'type': 'date',  'required': True,  'date_field': True,    'pdf_field_name': 'form1[0].#subform[0].Date1[0]',              'status': 'MAPPED'},
            {'name': 'TimeRecieved',       'label': 'Time Received',              'type': 'time',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].TimeRecieved[0]',       'status': 'MAPPED'},
            {'name': 'RegistedOwner',      'label': 'Registered Owner',           'type': 'text',  'required': True,  'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].RegistedOwner[0]',      'status': 'MAPPED'},
            {'name': 'Telephone1',         'label': 'Owner Telephone',            'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].Telephone1[0]',         'status': 'MAPPED'},
            {'name': 'LocationStolen',     'label': 'Location Vehicle Was Stolen','type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].LocationStolen[0]',     'status': 'MAPPED'},
            {'name': 'Date2',              'label': 'Date Last Seen',             'type': 'date',  'required': False, 'date_field': True,    'pdf_field_name': 'form1[0].#subform[0].Date2[0]',              'status': 'MAPPED'},
            {'name': 'Time2',              'label': 'Time Last Seen',             'type': 'time',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Time2[0]',              'status': 'MAPPED'},
            {'name': 'Name',               'label': 'Complainant Name',           'type': 'text',  'required': True,  'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].Name[0]',               'status': 'MAPPED'},
            {'name': 'Rate',               'label': 'Rank / Rate',                'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].Rate[0]',               'status': 'MAPPED'},
            {'name': 'SSN',                'label': 'SSN',                        'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].SSN[0]',                'status': 'MAPPED'},
            {'name': 'HomeAddPhone',       'label': 'Home Address / Phone',       'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].HomeAddPhone[0]',       'status': 'MAPPED'},
            {'name': 'DutyStation',        'label': 'Duty Station',               'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].DutyStation[0]',        'status': 'MAPPED'},
            {'name': 'DutyStationTelephone','label': 'Duty Station Telephone',   'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].DutyStationTelephone[0]','status': 'MAPPED'},
            {'name': 'Make',               'label': 'Vehicle Make',               'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Make[0]',               'status': 'MAPPED'},
            {'name': 'bodyStyle',          'label': 'Body Style',                 'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].bodyStyle[0]',          'status': 'MAPPED'},
            {'name': 'Top',                'label': 'Color (Top)',                 'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Top[0]',                'status': 'MAPPED'},
            {'name': 'Bottom',             'label': 'Color (Bottom)',              'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Bottom[0]',             'status': 'MAPPED'},
            {'name': 'Year',               'label': 'Vehicle Year',               'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Year[0]',               'status': 'MAPPED'},
            {'name': 'Value',              'label': 'Estimated Value',            'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Value[0]',              'status': 'MAPPED'},
            {'name': 'LicenseNumber',      'label': 'License Plate Number',       'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].LicenseNumber[0]',      'status': 'MAPPED'},
            {'name': 'State',              'label': 'License State',              'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].State[0]',              'status': 'MAPPED'},
            {'name': 'Vin',                'label': 'VIN',                        'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].Vin[0]',                'status': 'MAPPED'},
            {'name': 'Identifing',         'label': 'Identifying Marks / Features','type': 'text', 'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Identifing[0]',         'status': 'MAPPED'},
            {'name': 'KeyInCar',           'label': 'Keys in Car?',               'type': 'checkbox','required': False,                       'pdf_field_name': 'form1[0].#subform[0].KeyInCar[0]',           'status': 'MAPPED'},
            {'name': 'DoorsLocked',        'label': 'Doors Locked?',              'type': 'checkbox','required': False,                       'pdf_field_name': 'form1[0].#subform[0].DoorsLocked[0]',        'status': 'MAPPED'},
            {'name': 'ComSignature',       'label': 'Commanding Officer Signature','type': 'signature','required': False,'sig_role': 'supervisor',
             'pdf_field_name': 'form1[0].#subform[0].ComSignature[0]', 'status': 'MAPPED'},
        ],
        'notes': 'XFA PDF. All field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-16 Permissive Authorization for Search and Seizure ─────
    {
        'form_title_pattern': 'permissive authorization',
        'pdf_filename_hint': 'opnav_5580-16',
        'fields': [
            {'name': 'FillIn1',        'label': 'Name of Person Consenting',   'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].FillIn1[0]',        'status': 'MAPPED'},
            {'name': 'FillIn2',        'label': 'Premises / Property Address', 'type': 'text',      'required': True,                         'pdf_field_name': 'form1[0].#subform[0].FillIn2[0]',        'status': 'MAPPED'},
            {'name': 'FillIn3',        'label': 'Requesting Officer Name',     'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].FillIn3[0]',        'status': 'MAPPED'},
            {'name': 'FillIn4',        'label': 'Requesting Officer Rank',     'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].FillIn4[0]',        'status': 'MAPPED'},
            {'name': 'FillIn5',        'label': 'Items / Area to be Searched', 'type': 'textarea',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].FillIn5[0]',        'status': 'MAPPED'},
            {'name': 'FillIn6',        'label': 'Property / Evidence Sought',  'type': 'textarea',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FillIn6[0]',        'status': 'MAPPED'},
            {'name': 'FillIn7',        'label': 'Additional Details (7)',      'type': 'text',      'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FillIn7[0]',        'status': 'MAPPED'},
            {'name': 'FillIn8',        'label': 'Additional Details (8)',      'type': 'text',      'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FillIn8[0]',        'status': 'MAPPED'},
            {'name': 'FillIn9',        'label': 'Additional Details (9)',      'type': 'text',      'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FillIn9[0]',        'status': 'MAPPED'},
            {'name': 'FillIn10',       'label': 'Additional Details (10)',     'type': 'text',      'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FillIn10[0]',       'status': 'MAPPED'},
            {'name': 'Start',          'label': 'Search Start Time',           'type': 'time',      'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Start[0]',          'status': 'MAPPED'},
            {'name': 'End',            'label': 'Search End Time',             'type': 'time',      'required': False,                        'pdf_field_name': 'form1[0].#subform[0].End[0]',            'status': 'MAPPED'},
            {'name': 'DNSDate1_0',     'label': 'Date (Authorization)',        'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': 'form1[0].#subform[0].DNSDate1[0]',       'status': 'MAPPED'},
            {'name': 'WitnessesSig',   'label': 'Witness Signature',           'type': 'signature', 'required': False, 'sig_role': 'witness', 'pdf_field_name': 'form1[0].#subform[0].WitnessesSig[0]',  'status': 'MAPPED'},
            {'name': 'WitnessesSig2',  'label': 'Witness Signature 2',         'type': 'signature', 'required': False, 'sig_role': 'witness', 'pdf_field_name': 'form1[0].#subform[0].WitnessesSig2[0]', 'status': 'MAPPED'},
            {'name': 'by',             'label': 'Authorization By (Officer)',  'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].by[0]',             'status': 'MAPPED'},
        ],
        'notes': 'XFA PDF. All field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-20 Field Test Results ──────────────────────────────────
    {
        'form_title_pattern': 'field test results',
        'pdf_filename_hint': 'opnav_5580-20',
        'fields': [
            {'name': 'Suspect0',              'label': 'Suspect Name',                   'type': 'text',  'required': True,  'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].Suspect0[0]',              'status': 'MAPPED'},
            {'name': 'Suspect1',              'label': 'Suspect SSN / DOB',              'type': 'text',  'required': False, 'person_field': True,  'pdf_field_name': 'form1[0].#subform[0].Suspect1[0]',              'status': 'MAPPED'},
            {'name': 'CommandAddress',        'label': 'Command / Address',              'type': 'text',  'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].CommandAddress[0]',        'status': 'MAPPED'},
            {'name': 'RecoveredFrom',         'label': 'Recovered From (Location)',      'type': 'text',  'required': True,                         'pdf_field_name': 'form1[0].#subform[0].RecoveredFrom[0]',         'status': 'MAPPED'},
            {'name': 'ExaminedBy',            'label': 'Examined By (Officer)',          'type': 'text',  'required': True,  'officer_only': True,  'pdf_field_name': 'form1[0].#subform[0].ExaminedBy[0]',            'status': 'MAPPED'},
            {'name': 'DNSDate3',              'label': 'Date of Test',                   'type': 'date',  'required': True,  'date_field': True,    'pdf_field_name': 'form1[0].#subform[0].DNSDate3[0]',              'status': 'MAPPED'},
            {'name': 'ItemNumber1',           'label': 'Item 1 — Item Number',           'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].ItemNumber1[0]',           'status': 'MAPPED'},
            {'name': 'DesEvid1',              'label': 'Item 1 — Description of Evidence','type': 'text', 'required': False,                        'pdf_field_name': 'form1[0].#subform[0].DesEvid1[0]',              'status': 'MAPPED'},
            {'name': 'FieldTestUtilized1',    'label': 'Item 1 — Field Test Used',       'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FieldTestUtilized1[0]',    'status': 'MAPPED'},
            {'name': 'Results1',              'label': 'Item 1 — Results',               'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Results1[0]',              'status': 'MAPPED'},
            {'name': 'RecValue1',             'label': 'Item 1 — Recovered Value',       'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].RecValue1[0]',             'status': 'MAPPED'},
            {'name': 'ItemNumber2',           'label': 'Item 2 — Item Number',           'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].ItemNumber2[0]',           'status': 'MAPPED'},
            {'name': 'DesEvid2',              'label': 'Item 2 — Description of Evidence','type': 'text', 'required': False,                        'pdf_field_name': 'form1[0].#subform[0].DesEvid2[0]',              'status': 'MAPPED'},
            {'name': 'FieldTestUtilized2',    'label': 'Item 2 — Field Test Used',       'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FieldTestUtilized2[0]',    'status': 'MAPPED'},
            {'name': 'Results2',              'label': 'Item 2 — Results',               'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Results2[0]',              'status': 'MAPPED'},
            {'name': 'RecValue2',             'label': 'Item 2 — Recovered Value',       'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].RecValue2[0]',             'status': 'MAPPED'},
            {'name': 'ItemNumber3',           'label': 'Item 3 — Item Number',           'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].ItemNumber3[0]',           'status': 'MAPPED'},
            {'name': 'DesEvid3',              'label': 'Item 3 — Description of Evidence','type': 'text', 'required': False,                        'pdf_field_name': 'form1[0].#subform[0].DesEvid3[0]',              'status': 'MAPPED'},
            {'name': 'FieldTestUtilized3',    'label': 'Item 3 — Field Test Used',       'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].FieldTestUtilized3[0]',    'status': 'MAPPED'},
            {'name': 'Results3',              'label': 'Item 3 — Results',               'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].Results3[0]',              'status': 'MAPPED'},
            {'name': 'RecValue3',             'label': 'Item 3 — Recovered Value',       'type': 'text',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].RecValue3[0]',             'status': 'MAPPED'},
        ],
        'notes': 'XFA PDF. All field names confirmed against live PDF.',
    },

    # ── OPNAV 5580-21 Field Interview Card ───────────────────────────────
    {
        'form_title_pattern': 'field interview',
        'pdf_filename_hint': 'opnav_5580_21',
        'fields': [
            {'name': '1 NAME',     'label': 'Name',                                     'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': '1 NAME',     'status': 'MAPPED'},
            {'name': '2 SSN',      'label': 'SSN',                                       'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': '2 SSN',      'status': 'MAPPED'},
            {'name': '3 TELEPHONE','label': 'Telephone',                                 'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': '3 TELEPHONE','status': 'MAPPED'},
            {'name': '4 DATE  PLACE OF BIRTH', 'label': 'Date / Place of Birth',        'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': '4 DATE  PLACE OF BIRTH', 'status': 'MAPPED'},
            {'name': '5 ADDRESS',  'label': 'Address',                                   'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': '5 ADDRESS',  'status': 'MAPPED'},
            {'name': '6 SEX  RACE  HEIGHT  WEIGHT  HAIR  EYES', 'label': 'Physical Description (Sex / Race / Ht / Wt / Hair / Eyes)',
             'type': 'text', 'required': False, 'person_field': True, 'pdf_field_name': '6 SEX  RACE  HEIGHT  WEIGHT  HAIR  EYES', 'status': 'MAPPED'},
            {'name': '7 SCARS MARKS TATOOS', 'label': 'Scars / Marks / Tattoos',        'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': '7 SCARS MARKS TATOOS', 'status': 'MAPPED'},
            {'name': '8 DATE TIME LOCATION AND CIRCUMSTANCES SURROUNDING INTERVIEW',
             'label': 'Date / Time / Location / Circumstances of Interview',
             'type': 'textarea', 'required': True,  'officer_only': True,
             'pdf_field_name': '8 DATE TIME LOCATION AND CIRCUMSTANCES SURROUNDING INTERVIEW', 'status': 'MAPPED'},
            {'name': '9 STATED REASON FOR BEING IN AREA', 'label': 'Stated Reason for Being in Area',
             'type': 'text', 'required': True, 'person_field': True,  'pdf_field_name': '9 STATED REASON FOR BEING IN AREA', 'status': 'MAPPED'},
            {'name': '10 INTEVIEWERS',  'label': 'Interviewing Officer(s)',              'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': '10 INTEVIEWERS',  'status': 'MAPPED'},
            {'name': '11 REMARKS',      'label': 'Remarks',                              'type': 'textarea',  'required': False, 'officer_only': True,  'pdf_field_name': '11 REMARKS',      'status': 'MAPPED'},
            {'name': '12 SIGNATURE OF INTERVIEWING OFFICIALS', 'label': 'Officer Signature',
             'type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True,
             'pdf_field_name': '12 SIGNATURE OF INTERVIEWING OFFICIALS', 'status': 'MAPPED'},
            {'name': '13 LOCATION OF INTERVIEW', 'label': 'Location of Interview',      'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': '13 LOCATION OF INTERVIEW', 'status': 'MAPPED'},
        ],
        'notes': 'AcroForm PDF. All field names confirmed against live PDF.',
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
        'notes': 'AES-encrypted PDF — cannot be inspected without decryption key. Run pdf-debug after providing key.',
    },

    # ── SF 91 Motor Vehicle Accident ──────────────────────────────────────
    {
        'form_title_pattern': 'motor vehicle accident',
        'pdf_filename_hint': 'sf_91',
        'fields': [
            {'name': 'COOWNED',      'label': 'Government Owned?',          'type': 'checkbox',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].COOWNED[0]',       'status': 'MAPPED'},
            {'name': 'LEASED',       'label': 'Leased?',                    'type': 'checkbox',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].LEASED[0]',        'status': 'MAPPED'},
            {'name': 'RENTAL',       'label': 'Rental?',                    'type': 'checkbox',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].RENTAL[0]',        'status': 'MAPPED'},
            {'name': 'PRIVATELYOWNED','label': 'Privately Owned?',          'type': 'checkbox',  'required': False,                        'pdf_field_name': 'form1[0].#subform[0].PRIVATELYOWNED[0]','status': 'MAPPED'},
            {'name': 'Date',         'label': 'Date of Accident',           'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Time',         'label': 'Time of Accident',           'type': 'time',      'required': True,                         'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Location',     'label': 'Location',                   'type': 'text',      'required': True,                         'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Driver1Name',  'label': 'Driver 1 Name',              'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Driver2Name',  'label': 'Driver 2 Name',              'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Description',  'label': 'Accident Description',       'type': 'textarea',  'required': True,                         'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'OfficerSign',  'label': 'Officer Signature',          'type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
            {'name': 'Driver1Sign',  'label': 'Driver 1 Signature',         'type': 'signature', 'required': False, 'sig_role': 'subject', 'person_field': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
        ],
        'notes': 'XFA PDF with 188 fields. Vehicle ownership checkboxes mapped; remaining text/date fields need XFA coordinate lookup.',
    },

    # ── OPNAV 5580-22 Evidence Custody Document ───────────────────────────
    {
        'form_title_pattern': 'evidence custody',
        'pdf_filename_hint': 'opnav_5580_22',
        'fields': [
            {'name': '1',   'label': 'Report / Case Number',               'type': 'text',      'required': True,                         'pdf_field_name': '1',   'status': 'MAPPED'},
            {'name': '2',   'label': 'Date',                               'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': '2',   'status': 'MAPPED'},
            {'name': '3',   'label': 'Time',                               'type': 'time',      'required': True,                         'pdf_field_name': '3',   'status': 'MAPPED'},
            {'name': '4',   'label': 'Agency / ORI',                       'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': '4',   'status': 'MAPPED'},
            {'name': '5',   'label': 'Item Number',                        'type': 'text',      'required': True,                         'pdf_field_name': '5',   'status': 'MAPPED'},
            {'name': '6',   'label': 'Description of Evidence',            'type': 'textarea',  'required': True,                         'pdf_field_name': '6',   'status': 'MAPPED'},
            {'name': '7',   'label': 'Make / Model / Serial Number',       'type': 'text',      'required': False,                        'pdf_field_name': '7',   'status': 'MAPPED'},
            {'name': '8E',  'label': 'Class of Property — Other (specify)','type': 'text',      'required': False,                        'pdf_field_name': '8E',  'status': 'MAPPED'},
            {'name': '9',   'label': 'Released From (Name)',               'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': '9',   'status': 'MAPPED'},
            {'name': '10',  'label': 'Date Released',                      'type': 'date',      'required': False, 'date_field': True,    'pdf_field_name': '10',  'status': 'MAPPED'},
            {'name': '11',  'label': 'Time Released',                      'type': 'time',      'required': False,                        'pdf_field_name': '11',  'status': 'MAPPED'},
            {'name': '12',  'label': 'Received By (Officer)',              'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': '12',  'status': 'MAPPED'},
            {'name': '13',  'label': 'Disposition',                        'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': '13',  'status': 'MAPPED'},
            {'name': '14',  'label': 'Disposition Date',                   'type': 'date',      'required': False, 'date_field': True,    'pdf_field_name': '14',  'status': 'MAPPED'},
            {'name': '15',  'label': 'Custodian Signature',               'type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True,  'pdf_field_name': '15',  'status': 'MAPPED'},
            {'name': '16',  'label': 'Released To / Final Disposition',   'type': 'text',      'required': False,                        'pdf_field_name': '16',  'status': 'MAPPED'},
            {'name': 'CollectorSign',  'label': 'Collector Signature',    'type': 'signature', 'required': False, 'sig_role': 'officer', 'officer_only': True, 'pdf_field_name': '', 'status': 'PLACEHOLDER'},
        ],
        'notes': 'AcroForm PDF. Primary evidence block fields (1–16) confirmed against live PDF. Chain-of-custody table rows (7-*, 17-*, 18-*, 19-*, 20-*, 21-*) are continuation rows filled directly in the PDF.',
    },

    # ── Unsecured Building Notice ─────────────────────────────────────────
    {
        'form_title_pattern': 'unsecured building',
        'pdf_filename_hint': 'unsecured_building',
        'fields': [
            {'name': 'TO',                            'label': 'To (Unit / Command)',              'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'TO',                                    'status': 'MAPPED'},
            {'name': 'TIMEDATE FOUND UNSECURED',      'label': 'Time/Date Found Unsecured',        'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'TIMEDATE FOUND UNSECURED',              'status': 'MAPPED'},
            {'name': 'TIME THIS BUILDING HAS BEEN FOUND UNSECURED SINCE',
             'label': 'Number of Times Found Unsecured',                                           'type': 'text',      'required': False, 'officer_only': True,
             'pdf_field_name': 'TIME THIS BUILDING HAS BEEN FOUND UNSECURED SINCE',               'status': 'MAPPED'},
            {'name': 'REPORTING PERSON',              'label': 'Reporting Person',                 'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'REPORTING PERSON',                      'status': 'MAPPED'},
            {'name': 'PERSON CONTACTED',              'label': 'Person Contacted',                 'type': 'text',      'required': False,                        'pdf_field_name': 'PERSON CONTACTED',                      'status': 'MAPPED'},
            {'name': 'TIMEDATE NOTIFIED',             'label': 'Time/Date Notified',               'type': 'text',      'required': False,                        'pdf_field_name': 'TIMEDATE NOTIFIED',                     'status': 'MAPPED'},
            {'name': 'NAME RANK SSN',                 'label': 'Name / Rank / SSN (Person Contacted)', 'type': 'text', 'required': False,                        'pdf_field_name': 'NAME RANK SSN',                         'status': 'MAPPED'},
            {'name': 'UNIT ADDRESS PHONE',            'label': 'Unit / Address / Phone',           'type': 'text',      'required': False,                        'pdf_field_name': 'UNIT ADDRESS PHONE',                    'status': 'MAPPED'},
            {'name': 'DATE TIME SECURED',             'label': 'Date/Time Secured',                'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'DATE TIME SECURED',                     'status': 'MAPPED'},
            {'name': 'ACTIONS TAKEN 1',               'label': 'Actions Taken by Police (1)',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'ACTIONS TAKEN BY MARINE CORPS POLICE 1','status': 'MAPPED'},
            {'name': 'ACTIONS TAKEN 2',               'label': 'Actions Taken by Police (2)',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'ACTIONS TAKEN BY MARINE CORPS POLICE 2','status': 'MAPPED'},
            {'name': 'ACTIONS TAKEN 3',               'label': 'Actions Taken by Police (3)',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'ACTIONS TAKEN BY MARINE CORPS POLICE 3','status': 'MAPPED'},
            {'name': 'ACTIONS TAKEN 4',               'label': 'Actions Taken by Police (4)',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'ACTIONS TAKEN BY MARINE CORPS POLICE 4','status': 'MAPPED'},
            {'name': 'DATE',                          'label': 'Review Date',                      'type': 'date',      'required': False, 'date_field': True,    'pdf_field_name': 'DATE',                                  'status': 'MAPPED'},
            {'name': 'SIGNATURE OF REVIEWING OFFICAL','label': 'Reviewing Official Signature',     'type': 'signature', 'required': False, 'sig_role': 'supervisor', 'officer_only': True,
             'pdf_field_name': 'SIGNATURE OF REVIEWING OFFICAL',                                                                                                  'status': 'MAPPED'},
        ],
        'notes': 'AcroForm PDF. All field names confirmed against live PDF.',
    },

    # ── DD Form 1920 Alcohol Incident Report ──────────────────────────────
    {
        'form_title_pattern': 'alcohol incident',
        'pdf_filename_hint': 'dd_form_1920',
        'fields': [
            {'name': 'installation', 'label': 'Installation',             'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'installation', 'status': 'MAPPED'},
            {'name': 'ori_no',       'label': 'ORI Number',               'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'ori_no',       'status': 'MAPPED'},
            {'name': 'case_no',      'label': 'Case Number',              'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'case_no',      'status': 'MAPPED'},
            {'name': 'lastname',     'label': 'Last Name',                'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'lastname',     'status': 'MAPPED'},
            {'name': 'firstname',    'label': 'First Name',               'type': 'text',      'required': True,  'person_field': True,  'pdf_field_name': 'firstname',    'status': 'MAPPED'},
            {'name': 'middle',       'label': 'Middle Initial',           'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': 'middle',       'status': 'MAPPED'},
            {'name': 'grade',        'label': 'Grade / Rank',             'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': 'grade',        'status': 'MAPPED'},
            {'name': 'ssn',          'label': 'SSN',                      'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': 'ssn',          'status': 'MAPPED'},
            {'name': 'dob',          'label': 'Date of Birth',            'type': 'date',      'required': False, 'person_field': True,  'date_field': True, 'pdf_field_name': 'dob', 'status': 'MAPPED'},
            {'name': 'unit',         'label': 'Unit',                     'type': 'text',      'required': False, 'person_field': True,  'pdf_field_name': 'unit',         'status': 'MAPPED'},
            {'name': 'incloc',       'label': 'Incident Location',        'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'incloc',       'status': 'MAPPED'},
            {'name': 'incdate',      'label': 'Incident Date',            'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': 'incdate',      'status': 'MAPPED'},
            {'name': 'synopsis',     'label': 'Incident Synopsis',        'type': 'textarea',  'required': True,  'officer_only': True,  'pdf_field_name': 'synopsis',     'status': 'MAPPED'},
            {'name': 'prearrtime',   'label': 'Pre-Arrest Observation Time','type': 'time',    'required': False, 'officer_only': True,  'pdf_field_name': 'prearrtime',   'status': 'MAPPED'},
            {'name': 'prearrloc',    'label': 'Pre-Arrest Location',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'prearrloc',    'status': 'MAPPED'},
            {'name': 'prearrcond',   'label': 'Pre-Arrest Conditions Observed', 'type': 'textarea', 'required': False, 'officer_only': True, 'pdf_field_name': 'prearrcond', 'status': 'MAPPED'},
            {'name': 'intname',      'label': 'Interviewer Name',         'type': 'text',      'required': True,  'officer_only': True,  'pdf_field_name': 'intname',      'status': 'MAPPED'},
            {'name': 'whatdate',     'label': 'Date of Interview',        'type': 'date',      'required': True,  'date_field': True,    'pdf_field_name': 'whatdate',     'status': 'MAPPED'},
            {'name': 'drinking',     'label': 'Was Subject Drinking?',    'type': 'text',      'required': False,                        'pdf_field_name': 'drinking',     'status': 'MAPPED'},
            {'name': 'whatdrink',    'label': 'What Was Consumed',        'type': 'text',      'required': False,                        'pdf_field_name': 'whatdrink',    'status': 'MAPPED'},
            {'name': 'howmuch',      'label': 'How Much Consumed',        'type': 'text',      'required': False,                        'pdf_field_name': 'howmuch',      'status': 'MAPPED'},
            {'name': 'wheredrink',   'label': 'Where Consumed',           'type': 'text',      'required': False,                        'pdf_field_name': 'wheredrink',   'status': 'MAPPED'},
            {'name': 'startdrink',   'label': 'Started Drinking (Time)',  'type': 'time',      'required': False,                        'pdf_field_name': 'startdrink',   'status': 'MAPPED'},
            {'name': 'stopdrink',    'label': 'Stopped Drinking (Time)',  'type': 'time',      'required': False,                        'pdf_field_name': 'stopdrink',    'status': 'MAPPED'},
            {'name': 'lasteat',      'label': 'Last Ate (Time)',          'type': 'time',      'required': False,                        'pdf_field_name': 'lasteat',      'status': 'MAPPED'},
            {'name': 'whateat',      'label': 'What Was Eaten',          'type': 'text',      'required': False,                        'pdf_field_name': 'whateat',      'status': 'MAPPED'},
            {'name': 'physdef',      'label': 'Physical Defect?',         'type': 'text',      'required': False,                        'pdf_field_name': 'physdef',      'status': 'MAPPED'},
            {'name': 'injured',      'label': 'Injured?',                 'type': 'text',      'required': False,                        'pdf_field_name': 'injured',      'status': 'MAPPED'},
            {'name': 'howinj',       'label': 'How Injured',             'type': 'text',      'required': False,                        'pdf_field_name': 'howinj',       'status': 'MAPPED'},
            {'name': 'pills',        'label': 'Taking Medication?',       'type': 'text',      'required': False,                        'pdf_field_name': 'pills',        'status': 'MAPPED'},
            {'name': 'whatpills',    'label': 'Medication Name',          'type': 'text',      'required': False,                        'pdf_field_name': 'whatpills',    'status': 'MAPPED'},
            {'name': 'whensleep',    'label': 'Last Slept',               'type': 'text',      'required': False,                        'pdf_field_name': 'whensleep',    'status': 'MAPPED'},
            {'name': 'muchsleep',    'label': 'Hours of Sleep',           'type': 'number',    'required': False,                        'pdf_field_name': 'muchsleep',    'status': 'MAPPED'},
            {'name': 'bwtest',       'label': 'Breath/Blood/Urine Test',  'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'bwtest',       'status': 'MAPPED'},
            {'name': 'bwperf',       'label': 'Test Performed By',        'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'bwperf',       'status': 'MAPPED'},
            {'name': 'testres',      'label': 'Chemical Test Result',     'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'testres',      'status': 'MAPPED'},
            {'name': 'chemoff',      'label': 'Chemical Test Officer',    'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'chemoff',      'status': 'MAPPED'},
            {'name': 'chemtime',     'label': 'Chemical Test Time',       'type': 'time',      'required': False, 'officer_only': True,  'pdf_field_name': 'chemtime',     'status': 'MAPPED'},
            {'name': 'totalhgn',     'label': 'HGN Test — Total Clues',   'type': 'number',    'required': False, 'officer_only': True,  'pdf_field_name': 'totalhgn',     'status': 'MAPPED'},
            {'name': 'totalwalk',    'label': 'Walk-and-Turn — Total Clues','type': 'number',  'required': False, 'officer_only': True,  'pdf_field_name': 'totalwalk',    'status': 'MAPPED'},
            {'name': 'totaloneleg',  'label': 'One-Leg Stand — Total Clues','type': 'number',  'required': False, 'officer_only': True,  'pdf_field_name': 'totaloneleg',  'status': 'MAPPED'},
            {'name': 'observer',     'label': 'Observation Officer',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'observer',     'status': 'MAPPED'},
            {'name': 'appl',         'label': 'Approving Authority',      'type': 'text',      'required': False, 'officer_only': True,  'pdf_field_name': 'appl',         'status': 'MAPPED'},
        ],
        'notes': 'AcroForm PDF with 163 fields. Key narrative and test result fields mapped. Vehicle/person-type checkboxes (xveh*, xpers*) and sobriety test detail checkboxes are filled directly in the PDF.',
    },

    # ── Enclosure Checklist ───────────────────────────────────────────────
    {
        'form_title_pattern': 'enclosure checklist',
        'pdf_filename_hint': 'enclosure_checklist',
        'fields': [
            {'name': 'CASE',                        'label': 'Case Number',              'type': 'text',   'required': True,  'officer_only': True, 'pdf_field_name': 'CASE',                        'status': 'MAPPED'},
            {'name': 'INCIDENT TYPE',               'label': 'Incident Type',            'type': 'text',   'required': True,  'officer_only': True, 'pdf_field_name': 'INCIDENT TYPE',               'status': 'MAPPED'},
            {'name': 'CLEOC CCN CASE',              'label': 'CLEOC / CCN / Case',       'type': 'text',   'required': False, 'officer_only': True, 'pdf_field_name': 'CLEOC CCN CASE',              'status': 'MAPPED'},
            {'name': 'Initials',                    'label': 'Reviewer Initials (1)',    'type': 'initial','required': False, 'sig_role': 'officer','pdf_field_name': 'Initials',                    'status': 'MAPPED'},
            {'name': 'Initials_2',                  'label': 'Reviewer Initials (2)',    'type': 'initial','required': False, 'sig_role': 'officer','pdf_field_name': 'Initials_2',                  'status': 'MAPPED'},
            {'name': 'Initials_3',                  'label': 'Reviewer Initials (3)',    'type': 'initial','required': False, 'sig_role': 'officer','pdf_field_name': 'Initials_3',                  'status': 'MAPPED'},
            {'name': 'Initials_4',                  'label': 'Reviewer Initials (4)',    'type': 'initial','required': False, 'sig_role': 'officer','pdf_field_name': 'Initials_4',                  'status': 'MAPPED'},
            {'name': 'DDMMMYYYY',                   'label': 'Date (1)',                 'type': 'date',   'required': False, 'date_field': True,   'pdf_field_name': 'DDMMMYYYY',                   'status': 'MAPPED'},
            {'name': 'DDMMMYYYY_2',                 'label': 'Date (2)',                 'type': 'date',   'required': False, 'date_field': True,   'pdf_field_name': 'DDMMMYYYY_2',                 'status': 'MAPPED'},
            {'name': 'DDMMMYYYY_3',                 'label': 'Date (3)',                 'type': 'date',   'required': False, 'date_field': True,   'pdf_field_name': 'DDMMMYYYY_3',                 'status': 'MAPPED'},
            {'name': 'DDMMMYYYY_4',                 'label': 'Date (4)',                 'type': 'date',   'required': False, 'date_field': True,   'pdf_field_name': 'DDMMMYYYY_4',                 'status': 'MAPPED'},
            {'name': 'MISCADDITIONAL DOCUMENTS If applicable 1', 'label': 'Additional Document (1)', 'type': 'text', 'required': False, 'officer_only': True,
             'pdf_field_name': 'MISCADDITIONAL DOCUMENTS If applicable 1', 'status': 'MAPPED'},
            {'name': 'MISCADDITIONAL DOCUMENTS If applicable 2', 'label': 'Additional Document (2)', 'type': 'text', 'required': False, 'officer_only': True,
             'pdf_field_name': 'MISCADDITIONAL DOCUMENTS If applicable 2', 'status': 'MAPPED'},
            {'name': 'MISCADDITIONAL DOCUMENTS If applicable 3', 'label': 'Additional Document (3)', 'type': 'text', 'required': False, 'officer_only': True,
             'pdf_field_name': 'MISCADDITIONAL DOCUMENTS If applicable 3', 'status': 'MAPPED'},
        ],
        'notes': (
            'AcroForm PDF with 46 fields. Header and initials/date blocks mapped. '
            'Checkboxes (Check Box1–30) correspond to specific enclosure items on the printed form and '
            'are best checked directly in the PDF after download.'
        ),
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
