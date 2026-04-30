from types import SimpleNamespace
from pathlib import Path

from app.routes import forms
from app.services import mobile_form_catalog
from app.services import forms_pdf_renderer
from flask import Flask
from pypdf import PdfReader


DOMESTIC_SUPPLEMENTAL_PDF = (
    Path(r'C:\Users\rober\Desktop\mcpd-portal\data\uploads\forms')
    / '1772379338-14-NAVMAC_11337_MILITARY_POLICE_DOMESTIC_VIOLENCE_SIPPLEMENT_REPORT_AND_CHECKLIST.pdf'
)
VOLUNTARY_STATEMENT_PDF = (
    Path(r'C:\Users\rober\Desktop\mcpd-portal\data\uploads\forms')
    / '1772379338-18-OPNAV_5580_2_Voluntary_Statement.pdf'
)
SF91_CRASH_REPORT_PDF = (
    Path(r'C:\Users\rober\Desktop\mcpd-portal\data\uploads\forms')
    / '1772379338-29-SF-91_MOTOR_VEHICLE_ACCIDENT_CRASH_REPORT.pdf'
)
ABANDONED_VEHICLE_NOTICE_PDF = (
    Path(r'C:\Users\rober\Desktop\mcpd-portal\data\uploads\forms')
    / '1772379338-5-DD_Form_2504Abandoned_Vehicle_Notice.pdf'
)


def test_stat_schema_selected_for_stat_title():
    class DummyForm:
        title = 'MCPD Stat Sheet - March'

    schema = forms._schema_for_form(DummyForm())
    assert schema['id'] == 'mcpd_stat_sheet_v1'


def test_generic_schema_selected_for_other_title():
    class DummyForm:
        title = 'General Incident Worksheet'

    schema = forms._schema_for_form(DummyForm())
    assert schema['id'] == 'generic_form_v1'


def test_normalize_legacy_payload_maps_known_labels():
    schema = forms.MCPD_STAT_SHEET_SCHEMA
    legacy = {
        'fields': [
            {'key': 'Report Date', 'value': '2026-03-10'},
            {'key': 'Traffic Stops', 'value': '12'},
        ],
        'notes': 'legacy notes',
    }
    payload = forms._normalize_payload(legacy, schema)
    assert payload['values']['report_date'] == '2026-03-10'
    assert payload['values']['traffic_stops'] == '12'
    assert payload['notes'] == 'legacy notes'


def test_flat_export_includes_section_markers_and_role_rows():
    schema = forms.MCPD_STAT_SHEET_SCHEMA
    payload = forms._empty_payload(schema)
    payload['values']['report_date'] = '2026-03-10'
    payload['role_entries'] = [
        {
            'role': 'Victim',
            'full_name': 'Jane Doe',
            'identifier': '123',
            'phone': '555-1000',
            'vehicle': 'Blue Sedan',
            'notes': 'Primary complainant',
        }
    ]
    rows = forms._flat_export_fields(schema, payload)
    keys = [row['key'] for row in rows]
    assert '[Reporting Information]' in keys
    assert 'Report Date' in keys
    assert '[People by Role]' in keys
    assert 'Role 1' in keys


def test_print_value_uses_na_for_empty_completed():
    assert forms._print_value('', blank_mode=False) == 'N/A'
    assert forms._print_value('', blank_mode=True) == ''


def test_no_retention_policy_disables_completed_save():
    class DummyForm:
        retention_mode = 'no_pii_retention'
        contains_pii = True
        allow_email = True
        allow_download = True
        allow_completed_save = True
        allow_blank_print = True

    policy = forms._form_policy(DummyForm())
    assert policy['is_no_retention'] is True
    assert policy['allow_completed_save'] is False


def test_parse_id_scan_payload_reads_aamva_fields():
    payload = forms._parse_id_scan_payload(
        '\n'.join([
            'DCSDOE',
            'DACJANE',
            'DADQ',
            'DBB01021990',
            'DAQD1234567',
            'DAG123 MAIN ST',
            'DAIALBANY',
            'DAJGA',
            'DAK31705',
            'DBC2',
            'DBA01022030',
        ])
    )
    assert payload['full_name'] == 'JANE Q DOE'
    assert payload['date_of_birth'] == '1990-01-02'
    assert payload['license_number'] == 'D1234567'
    assert payload['state'] == 'GA'


def test_apply_id_scan_to_payload_populates_first_role_entry_without_overwrite():
    schema = {
        'id': 'generic_form_v1',
        'sections': [{'title': 'Core', 'fields': [{'name': 'subject_name', 'label': 'Subject Name'}, {'name': 'date_of_birth', 'label': 'Date of Birth'}]}],
        'show_role_entry': True,
        'show_notes': False,
    }
    payload = {'schema_id': 'generic_form_v1', 'values': {'subject_name': '', 'date_of_birth': ''}, 'role_entries': [], 'notes': ''}
    updated, scan_result = forms._apply_id_scan_to_payload(
        schema,
        payload,
        {'full_name': 'Jane Doe', 'date_of_birth': '1990-01-02', 'license_number': 'D1234567', 'issuing_state': 'GA'},
        replace_existing=False,
    )
    assert updated['values']['subject_name'] == 'Jane Doe'
    assert updated['values']['date_of_birth'] == '1990-01-02'
    assert updated['role_entries'][0]['full_name'] == 'Jane Doe'
    assert updated['role_entries'][0]['identifier'] == 'D1234567 (GA)'
    assert 'role identifier' in scan_result['imported']


def test_schema_from_pdf_fields_only_uses_visible_pdf_backed_keys():
    class DummyForm:
        title = 'MCPD Stat Sheet'
        file_path = ''

    base_schema = forms.MCPD_STAT_SHEET_SCHEMA.copy()
    original_visible = forms.visible_input_keys_for_pdf
    original_inspect = forms.inspect_pdf_fields
    try:
        forms.visible_input_keys_for_pdf = lambda *_args, **_kwargs: {'report_date'}
        forms.inspect_pdf_fields = lambda *_args, **_kwargs: {'fields': [{'name': 'report_date', 'type': '/Tx'}, {'name': 'extra_pdf', 'type': '/Tx'}]}
        schema = forms._schema_from_pdf_fields(DummyForm(), base_schema, source_pdf='dummy.pdf')
    finally:
        forms.visible_input_keys_for_pdf = original_visible
        forms.inspect_pdf_fields = original_inspect
    field_names = [field['name'] for section in schema.get('sections', []) for field in section.get('fields', [])]
    assert field_names == ['report_date']
    assert schema.get('show_role_entry') is False
    assert schema.get('show_notes') is False


def test_pdf_field_extraction_preserves_form_order_and_real_labels():
    info = forms_pdf_renderer.inspect_pdf_fields(str(SF91_CRASH_REPORT_PDF))
    labels = [row.get('label') for row in info.get('fields', [])[:8]]
    assert any('Driver' in label for label in labels)
    assert not labels[0].startswith('Form1')


def test_voluntary_statement_rows_get_readable_labels():
    info = forms_pdf_renderer.inspect_pdf_fields(str(VOLUNTARY_STATEMENT_PDF))
    labels = [row.get('label') for row in info.get('fields', [])]
    assert 'Statement Row 1' in labels
    assert 'Statement Row 2' in labels


def test_xfa_control_fields_are_not_shown_as_officer_inputs():
    info = forms_pdf_renderer.inspect_xfa_fields(str(ABANDONED_VEHICLE_NOTICE_PDF))
    names = [row.get('name') for row in info.get('fields', [])]
    assert not any('SaveButton' in name for name in names)
    assert not any('CurrentPage' in name for name in names)
    assert not any('PageCount' in name for name in names)


def test_visible_input_keys_fillable_pdf_respects_template_mapping_only():
    schema_id = 'test_pdf_source_truth_case'
    forms_pdf_renderer.save_template_payload(
        schema_id,
        {
            'template_id': schema_id,
            'field_map': {'report_date': 'ReportDateField'},
            'ui_fields': [{'name': 'report_date', 'label': 'Report Date', 'type': 'date', 'section': 'Core'}],
        },
    )
    original_inspect = forms_pdf_renderer.inspect_pdf_fields
    try:
        forms_pdf_renderer.inspect_pdf_fields = lambda *_args, **_kwargs: {
            'field_count': 2,
            'fields': [{'name': 'ReportDateField', 'type': '/Tx'}, {'name': 'UnmappedField', 'type': '/Tx'}],
        }
        keys = forms_pdf_renderer.visible_input_keys_for_pdf(schema_id, pdf_path=__file__)
    finally:
        forms_pdf_renderer.inspect_pdf_fields = original_inspect
    assert keys == {'report_date'}


def test_domestic_xfa_inspection_reads_live_field_map():
    info = forms_pdf_renderer.inspect_xfa_fields(str(DOMESTIC_SUPPLEMENTAL_PDF))
    assert info['field_count'] == 220
    assert len(info['conditional_groups']) == 13
    assert info['fields'][0]['name'] == 'form1.SupInitial.1'


def test_domestic_schema_groups_live_xfa_form_into_six_sections():
    schema = forms._schema_for_form(
        SimpleNamespace(
            title='NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
            file_path=str(DOMESTIC_SUPPLEMENTAL_PDF),
        )
    )
    section_titles = [section['title'] for section in schema['sections']]
    assert section_titles == [
        'Dispatch And Parties',
        'Victim Condition And Statements',
        'Suspect Condition And Statements',
        'Scene, Relationship, And Prior Violence',
        'Witnesses, Evidence, And Victim Services',
        'Medical Response And Injury Documentation',
    ]
    assert sum(len(section['fields']) for section in schema['sections']) == 220
    assert schema['sections'][0]['fields'][0]['label'] == "Supervisor's Initial"


def test_mobile_catalog_marks_domestic_form_as_xfa_with_six_sections():
    structure = mobile_form_catalog._inspect_form_structure(
        SimpleNamespace(
            title='NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
            file_path=str(DOMESTIC_SUPPLEMENTAL_PDF),
        )
    )
    assert structure['sourceKind'] == 'xfa'
    assert len(structure['fields']) == 220
    assert len(structure['conditionalGroups']) == 13
    assert [section['title'] for section in structure['sectionSummaries']] == [
        'Dispatch And Parties',
        'Victim Condition And Statements',
        'Suspect Condition And Statements',
        'Scene, Relationship, And Prior Violence',
        'Witnesses, Evidence, And Victim Services',
        'Medical Response And Injury Documentation',
    ]


def test_wait_shell_xfa_generates_sectioned_compatible_pdf_without_adobe_wait_text():
    form = SimpleNamespace(
        title='NAVMAC 11337 MILITARY POLICE DOMESTIC VIOLENCE SIPPLEMENT REPORT AND CHECKLIST',
        file_path=str(DOMESTIC_SUPPLEMENTAL_PDF),
    )
    schema = forms._schema_for_form(form)
    first_field = schema['sections'][0]['fields'][0]['name']
    payload = forms._empty_payload(schema)
    payload['values'][first_field] = 'RR'

    pdf_path, meta = forms_pdf_renderer.render_form_pdf(str(DOMESTIC_SUPPLEMENTAL_PDF), schema, payload, blank_mode=False)
    try:
        assert meta['mode'] == 'xfa_sectioned_compatible'
        assert meta['xfa_field_count'] == 220
        text = ' '.join((page.extract_text() or '') for page in PdfReader(pdf_path).pages[:1])
        assert 'Please wait' not in text
        assert 'NAVMAC 11337' in text
        assert 'Supervisor' in text
        assert 'RR' in text
        assert 'Browser-compatible official field render' in text
    finally:
        Path(pdf_path).unlink(missing_ok=True)


def test_allowed_submission_keys_only_include_visible_pdf_fields_and_action_controls():
    schema = {
        'sections': [{'fields': [{'name': 'report_date'}, {'name': 'traffic_stops'}]}],
        'show_role_entry': False,
        'show_notes': False,
    }
    allowed = forms._allowed_submission_keys(schema)
    assert 'action' in allowed
    assert 'saved_title' in allowed
    assert 'field_report_date' in allowed
    assert 'field_traffic_stops' in allowed
    assert 'notes' not in allowed
    assert 'role_entry_name' not in allowed


def test_unexpected_submission_keys_detects_non_pdf_inputs():
    schema = {
        'sections': [{'fields': [{'name': 'report_date'}]}],
        'show_role_entry': False,
        'show_notes': False,
    }
    app = Flask(__name__)
    with app.test_request_context(
        '/forms/1/fill',
        method='POST',
        data={
            'action': 'save_draft',
            'saved_title': 'MCPD Stat Sheet',
            'field_report_date': '2026-03-10',
            'field_extra_hidden': 'should_not_be_allowed',
            'notes': 'not allowed when show_notes=false',
        },
    ):
        unexpected = forms._unexpected_submission_keys(schema)
    assert unexpected == ['field_extra_hidden', 'notes']


def test_form_maintenance_access_allows_desk_sergeant():
    user = SimpleNamespace(is_authenticated=True, has_any_role=lambda *roles: 'DESK_SGT' in roles)
    assert forms._can_manage_form_maintenance(user) is True


def test_fill_template_hides_pdf_tools_for_normal_officer():
    app = Flask(__name__, template_folder=r'C:\Users\rober\Desktop\mcpd-portal\app\templates')
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    app.add_url_rule('/forms', 'forms.list_forms', lambda: '')
    app.add_url_rule('/forms/saved', 'forms.saved_forms', lambda: '')
    app.add_url_rule('/forms/1/blank-print', 'forms.blank_form_preview', lambda form_id: '')
    app.add_url_rule('/forms/1/download', 'forms.download_form', lambda form_id: '')
    fake_user = SimpleNamespace(
        can_manage_site=lambda: False,
        can_manage_team=lambda: False,
        display_name='Officer Test',
    )
    with app.test_request_context('/forms/1/fill'):
        html = app.jinja_env.get_template('forms_fill.html').render(
            user=fake_user,
            form=SimpleNamespace(id=1, title='Incident Worksheet', category='Patrol'),
            schema={
                'sections': [{'title': 'Core Details', 'fields': [{'name': 'incident_date', 'label': 'Incident Date', 'type': 'date', 'required': False, 'placeholder': ''}]}],
                'show_role_entry': False,
                'show_notes': False,
            },
            payload={'values': {'incident_date': ''}, 'role_entries': [], 'notes': ''},
            saved_record=None,
            can_edit=True,
            policy=SimpleNamespace(is_no_retention=False, allow_completed_save=True, allow_download=True, allow_email=True, allow_blank_print=True),
            fill_state=SimpleNamespace(is_ready=True, fallback_message=''),
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'PDF Template Editor' not in html
    assert 'PDF Debug Table' not in html
    assert 'Render Diagnostics' not in html
    assert 'PDF Mapping Required' not in html
    assert 'Preview' in html


def test_fill_template_shows_scan_id_for_supported_form():
    app = Flask(__name__, template_folder=r'C:\Users\rober\Desktop\mcpd-portal\app\templates')
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    app.add_url_rule('/forms', 'forms.list_forms', lambda: '')
    app.add_url_rule('/forms/saved', 'forms.saved_forms', lambda: '')
    app.add_url_rule('/forms/1/blank-print', 'forms.blank_form_preview', lambda form_id: '')
    app.add_url_rule('/forms/1/download', 'forms.download_form', lambda form_id: '')
    fake_user = SimpleNamespace(
        can_manage_site=lambda: False,
        can_manage_team=lambda: False,
        display_name='Officer Test',
    )
    with app.test_request_context('/forms/1/fill'):
        html = app.jinja_env.get_template('forms_fill.html').render(
            user=fake_user,
            form=SimpleNamespace(id=1, title='Subject Interview', category='Patrol'),
            schema={
                'sections': [{'title': 'Person', 'fields': [{'name': 'subject_name', 'label': 'Subject Name', 'type': 'text', 'required': False, 'placeholder': ''}]}],
                'show_role_entry': True,
                'role_entry': {'role_options': ['Victim']},
                'show_notes': False,
            },
            payload={'values': {'subject_name': ''}, 'role_entries': [], 'notes': ''},
            saved_record=None,
            can_edit=True,
            policy=SimpleNamespace(is_no_retention=False, allow_completed_save=True, allow_download=True, allow_email=True, allow_blank_print=True),
            fill_state=SimpleNamespace(is_ready=True, fallback_message='', source_of_truth_label='PDF-backed'),
            scan_supported=True,
            scan_result=None,
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'Scan Driver License' in html
    assert 'Import Barcode Data' in html
    assert 'Auto Fill' in html


def test_fill_template_shows_clean_fallback_for_unconfigured_form():
    app = Flask(__name__, template_folder=r'C:\Users\rober\Desktop\mcpd-portal\app\templates')
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    app.add_url_rule('/forms', 'forms.list_forms', lambda: '')
    app.add_url_rule('/forms/saved', 'forms.saved_forms', lambda: '')
    app.add_url_rule('/forms/1/blank-print', 'forms.blank_form_preview', lambda form_id: '')
    app.add_url_rule('/forms/1/download', 'forms.download_form', lambda form_id: '')
    fake_user = SimpleNamespace(
        can_manage_site=lambda: False,
        can_manage_team=lambda: False,
        display_name='Officer Test',
    )
    with app.test_request_context('/forms/1/fill'):
        html = app.jinja_env.get_template('forms_fill.html').render(
            user=fake_user,
            form=SimpleNamespace(id=1, title='Unconfigured Form', category='Admin'),
            schema={'sections': [], 'show_role_entry': False, 'show_notes': False, 'pdf_source_warning': 'No PDF-backed visible fields are configured for this form.'},
            payload={'values': {}, 'role_entries': [], 'notes': ''},
            saved_record=None,
            can_edit=True,
            policy=SimpleNamespace(is_no_retention=False, allow_completed_save=True, allow_download=True, allow_email=True, allow_blank_print=True),
            fill_state=SimpleNamespace(is_ready=False, fallback_message='This form is not yet available for online completion. You can still print or download the blank form.'),
            scan_supported=False,
            scan_result=None,
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'Online Completion Not Available Yet' in html
    assert 'This form is not yet available for online completion.' in html
    assert 'PDF Mapping Required' not in html
    assert 'PDF Template Editor' not in html
    assert 'Blank Preview' in html
    assert 'Blank Download' in html


def test_saved_forms_hides_retention_events_for_normal_users():
    app = Flask(__name__, template_folder=r'C:\Users\rober\Desktop\mcpd-portal\app\templates')
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    fake_user = SimpleNamespace(can_manage_site=lambda: False, can_manage_team=lambda: False, display_name='Officer Test')
    with app.test_request_context('/forms/saved'):
        html = app.jinja_env.get_template('saved_forms.html').render(
            user=fake_user,
            saved_forms=[],
            status='',
            form_type='',
            search_term='',
            no_retention_events=[],
            show_admin_retention_events=False,
            display_dt=lambda value: '',
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'No-Retention Form Events' not in html


def test_reports_center_template_unifies_standard_and_mock_report_sections():
    app = Flask(__name__, template_folder=r'C:\Users\rober\Desktop\mcpd-portal\app\templates')
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    fake_user = SimpleNamespace(can_manage_site=lambda: False, can_manage_team=lambda: False, display_name='Officer Test')
    with app.test_request_context('/reports'):
        html = app.jinja_env.get_template('reports_list.html').render(
            user=fake_user,
            reports=[],
            cleo_reports=[],
            cleo_review_reports=[],
            report_count=0,
            cleo_count=0,
            cleo_review_count=0,
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'Reports Center' in html
    assert 'Standard Reports' in html
    assert 'Mock Reports' in html
    assert 'Paperwork Navigator' in html


def test_visible_input_keys_for_pdf_falls_back_to_fillable_pdf_fields():
    original_load = forms_pdf_renderer._load_template
    original_inspect = forms_pdf_renderer.inspect_pdf_fields
    original_exists = forms_pdf_renderer.os.path.exists
    try:
        forms_pdf_renderer._load_template = lambda *_args, **_kwargs: {}
        forms_pdf_renderer.inspect_pdf_fields = lambda *_args, **_kwargs: {
            'fields': [
                {'name': 'IncidentDate', 'type': '/Tx'},
                {'name': 'PrintButton', 'type': '/Btn'},
                {'name': 'OfficerSignature', 'type': '/Tx'},
                {'name': 'Location', 'type': '/Tx'},
            ]
        }
        forms_pdf_renderer.os.path.exists = lambda *_args, **_kwargs: True
        keys = forms_pdf_renderer.visible_input_keys_for_pdf('generic_form_v1', 'dummy.pdf')
    finally:
        forms_pdf_renderer._load_template = original_load
        forms_pdf_renderer.inspect_pdf_fields = original_inspect
        forms_pdf_renderer.os.path.exists = original_exists
    assert 'IncidentDate' in keys
    assert 'Location' in keys
    assert 'PrintButton' not in keys
    assert 'OfficerSignature' not in keys


def test_visible_input_keys_for_pdf_uses_template_keys_when_pdf_targets_do_not_match():
    original_load = forms_pdf_renderer._load_template
    original_inspect = forms_pdf_renderer.inspect_pdf_fields
    original_exists = forms_pdf_renderer.os.path.exists
    try:
        forms_pdf_renderer._load_template = lambda *_args, **_kwargs: {
            'field_map': {'report_date': 'report_date', 'watch_commander': 'watch_commander'},
            'ui_fields': [{'name': 'report_date'}, {'name': 'watch_commander'}],
        }
        forms_pdf_renderer.inspect_pdf_fields = lambda *_args, **_kwargs: {
            'fields': [{'name': 'DateTime', 'type': '/Tx'}, {'name': 'Officer Reporting', 'type': '/Tx'}]
        }
        forms_pdf_renderer.os.path.exists = lambda *_args, **_kwargs: True
        keys = forms_pdf_renderer.visible_input_keys_for_pdf('mcpd_stat_sheet_v1', 'dummy.pdf')
    finally:
        forms_pdf_renderer._load_template = original_load
        forms_pdf_renderer.inspect_pdf_fields = original_inspect
        forms_pdf_renderer.os.path.exists = original_exists
    assert keys == {'report_date', 'watch_commander'}


def test_field_name_map_uses_template_mapping_and_direct_pdf_match():
    mapped = forms_pdf_renderer._field_name_map(
        ['report_date', 'watchCommander', 'notes'],
        {'field_map': {'watch_commander': 'watchCommander'}},
        {
            'report_date': '2026-03-10',
            'watch_commander': 'Sgt Smith',
            'general_notes': 'Completed online',
            'label::General Notes': 'Completed online',
        },
    )
    assert mapped['report_date'] == '2026-03-10'
    assert mapped['watchCommander'] == 'Sgt Smith'


def test_render_form_pdf_falls_back_to_overlay_when_template_has_zero_pdf_matches():
    original_exists = forms_pdf_renderer.os.path.exists
    original_reader_for_pdf = forms_pdf_renderer._reader_for_pdf
    original_load = forms_pdf_renderer._load_template
    original_fillable = forms_pdf_renderer._write_fillable_pdf
    original_overlay = forms_pdf_renderer._write_overlay_pdf
    try:
        forms_pdf_renderer.os.path.exists = lambda *_args, **_kwargs: True
        forms_pdf_renderer._reader_for_pdf = lambda *_args, **_kwargs: SimpleNamespace(
            pages=[],
            get_fields=lambda: {'SomeField': {}},
        )
        forms_pdf_renderer._load_template = lambda *_args, **_kwargs: {'template_id': 'mcpd_stat_sheet_v1', 'field_map': {'report_date': 'report_date'}}
        forms_pdf_renderer._write_fillable_pdf = lambda *_args, **_kwargs: {'mode': 'fillable', 'mapped_count': 0, 'mapped_fields': [], 'truncations': [], 'template_id': 'mcpd_stat_sheet_v1'}
        forms_pdf_renderer._write_overlay_pdf = lambda *_args, **_kwargs: {'mode': 'overlay', 'mapped_count': 5, 'mapped_fields': ['report_date'], 'template_id': ''}
        out_path, meta = forms_pdf_renderer.render_form_pdf('dummy.pdf', {'id': 'mcpd_stat_sheet_v1'}, {'values': {'report_date': '2026-03-10'}}, blank_mode=False)
    finally:
        forms_pdf_renderer.os.path.exists = original_exists
        forms_pdf_renderer._reader_for_pdf = original_reader_for_pdf
        forms_pdf_renderer._load_template = original_load
        forms_pdf_renderer._write_fillable_pdf = original_fillable
        forms_pdf_renderer._write_overlay_pdf = original_overlay
        if 'out_path' in locals():
            try:
                Path(out_path).unlink()
            except Exception:
                pass
    assert meta['mode'] == 'overlay_template_fallback'
    assert meta['mapped_count'] == 5


def test_render_form_pdf_uses_browser_compatible_overlay_for_xfa_shell():
    original_exists = forms_pdf_renderer.os.path.exists
    original_pdf = forms_pdf_renderer.inspect_pdf_fields
    original_xfa = forms_pdf_renderer.inspect_xfa_fields
    original_overlay = forms_pdf_renderer._write_overlay_pdf
    original_xfa_overlay = forms_pdf_renderer._write_xfa_overlay_pdf
    original_xfa_layout = forms_pdf_renderer._write_xfa_layout_pdf
    try:
        forms_pdf_renderer.os.path.exists = lambda *_args, **_kwargs: True
        forms_pdf_renderer.inspect_pdf_fields = lambda *_args, **_kwargs: {'field_count': 0, 'fields': []}
        forms_pdf_renderer.inspect_xfa_fields = lambda *_args, **_kwargs: {'field_count': 1, 'fields': [{'name': 'form1.TextField1'}]}
        forms_pdf_renderer._write_overlay_pdf = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('generic overlay should not be used for XFA layout'))
        forms_pdf_renderer._write_xfa_overlay_pdf = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('raw XFA shell should not be used'))
        forms_pdf_renderer._write_xfa_layout_pdf = lambda *_args, **_kwargs: {'mode': 'xfa_layout', 'mapped_count': 1, 'mapped_fields': ['form1.TextField1'], 'template_id': ''}
        out_path, meta = forms_pdf_renderer.render_form_pdf(
            'xfa-shell.pdf',
            {'id': 'generic_form_v1', 'sections': [{'title': 'Fields', 'fields': [{'name': 'form1.TextField1', 'label': 'Field'}]}]},
            {'values': {'form1.TextField1': 'test'}},
            blank_mode=True,
        )
    finally:
        forms_pdf_renderer.os.path.exists = original_exists
        forms_pdf_renderer.inspect_pdf_fields = original_pdf
        forms_pdf_renderer.inspect_xfa_fields = original_xfa
        forms_pdf_renderer._write_overlay_pdf = original_overlay
        forms_pdf_renderer._write_xfa_overlay_pdf = original_xfa_overlay
        forms_pdf_renderer._write_xfa_layout_pdf = original_xfa_layout
        if 'out_path' in locals():
            try:
                Path(out_path).unlink()
            except Exception:
                pass
    assert meta['mode'] == 'xfa_layout'


def test_render_form_pdf_forces_overlay_when_source_has_adobe_wait_shell():
    original_exists = forms_pdf_renderer.os.path.exists
    original_shell = forms_pdf_renderer.source_pdf_has_adobe_wait_shell
    original_pdf = forms_pdf_renderer.inspect_pdf_fields
    original_overlay = forms_pdf_renderer._write_overlay_pdf
    original_fillable = forms_pdf_renderer._write_fillable_pdf
    original_xfa_sectioned = forms_pdf_renderer._write_xfa_sectioned_pdf
    try:
        forms_pdf_renderer.os.path.exists = lambda *_args, **_kwargs: True
        forms_pdf_renderer.source_pdf_has_adobe_wait_shell = lambda *_args, **_kwargs: True
        forms_pdf_renderer.inspect_pdf_fields = lambda *_args, **_kwargs: {'field_count': 12, 'fields': [{'name': 'real'}]}
        forms_pdf_renderer._write_overlay_pdf = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('Adobe wait shell must not use generic overlay path'))
        forms_pdf_renderer._write_fillable_pdf = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('Adobe wait shell must not use raw fillable path'))
        forms_pdf_renderer._write_xfa_sectioned_pdf = lambda *_args, **_kwargs: {'mode': 'xfa_sectioned', 'mapped_count': 1, 'mapped_fields': ['real'], 'template_id': ''}
        out_path, meta = forms_pdf_renderer.render_form_pdf(
            'xfa-shell-with-fields.pdf',
            {'id': 'generic_form_v1', 'sections': [{'title': 'Fields', 'fields': [{'name': 'real', 'label': 'Real Field'}]}]},
            {'values': {'real': 'test'}},
            blank_mode=False,
        )
    finally:
        forms_pdf_renderer.os.path.exists = original_exists
        forms_pdf_renderer.source_pdf_has_adobe_wait_shell = original_shell
        forms_pdf_renderer.inspect_pdf_fields = original_pdf
        forms_pdf_renderer._write_overlay_pdf = original_overlay
        forms_pdf_renderer._write_fillable_pdf = original_fillable
        forms_pdf_renderer._write_xfa_sectioned_pdf = original_xfa_sectioned
        if 'out_path' in locals():
            try:
                Path(out_path).unlink()
            except Exception:
                pass
    assert meta['mode'] == 'xfa_sectioned_compatible'


def test_send_ephemeral_file_removes_temp_pdf_after_response():
    app = Flask(__name__)
    target = Path(r'C:\Users\rober\Desktop\mcpd-portal\app\generated-test-ephemeral.pdf')
    if target.exists():
        target.unlink()
    target.write_bytes(b'%PDF-1.4\n%test\n')
    original_exists = forms.os.path.exists
    original_remove = forms.os.remove
    removals = []
    forms.os.path.exists = lambda path: str(path) == str(target) or original_exists(path)
    forms.os.remove = lambda path: removals.append(str(path))
    with app.test_request_context('/download'):
        response = None
        try:
            response = forms._send_ephemeral_file(str(target), 'generated.pdf')
            app.process_response(response)
        finally:
            if response is not None:
                response.close()
            forms.os.path.exists = original_exists
            forms.os.remove = original_remove
            if target.exists():
                try:
                    target.unlink()
                except PermissionError:
                    pass
    assert str(target) in removals
