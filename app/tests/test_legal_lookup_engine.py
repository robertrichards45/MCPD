from pathlib import Path
from types import SimpleNamespace

from flask import Flask

from app import create_app
from app.services.legal_lookup import LegalEntry, reference_download_info, search_entries
from app.routes.legal import _order_reference_matches


def test_federal_installation_queries_rank_18_usc_1382_first():
    for query in (
        'trespassing on a federal installation',
        'barred from military base and returned',
        'unlawful entry onto military installation',
        'entered federal military property after warning',
    ):
        results = search_entries(query, 'ALL')
        assert results
        assert results[0].entry.code == '18 USC 1382'


def test_reference_download_info_falls_back_to_generated_text():
    entry = LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1382',
        title='Entering Military, Naval, or Coast Guard Property',
        summary='Federal installation entry offense.',
        elements=('Element one',),
        official_text='Full federal text.',
    )
    download = reference_download_info(entry)
    assert download['available'] is True
    assert download['mode'] == 'generated_text'
    assert download['file_name'].endswith('.txt')


def test_broad_scenario_queries_return_expected_reference_paths():
    cases = {
        'barred from base and came back': '18 USC 1382',
        'gave false name to police': 'OCGA 16-10-25',
        'threatened by text': '18 USC 2261A',
        'stole government property': '18 USC 641',
        'subject refused lawful order': 'Article 92',
    }
    for query, expected_code in cases.items():
        results = search_entries(query, 'ALL')
        assert results, query
        assert results[0].entry.code == expected_code, query


def test_lookup_scores_against_full_entry_body_before_keyword_hits():
    results = search_entries('barred from base and came back', 'ALL')
    assert results
    assert results[0].entry.code == '18 USC 1382'
    assert any('full statute/order text' in reason for reason in results[0].reasons)


def test_federal_installation_search_keeps_federal_reference_ahead_of_base_orders():
    results = search_entries('suspicious person in restricted area', 'ALL')
    assert results
    assert results[0].entry.code == '18 USC 1382'
    if len(results) > 1:
        assert results[0].entry.source == 'FEDERAL_USC'


def test_public_defecation_query_does_not_surface_unrelated_shoplifting_order():
    app = create_app()
    with app.app_context():
        matches = _order_reference_matches('pooping in the street')
    titles = [item['title'] for item in matches]
    assert not any('shoplifting' in title.lower() for title in titles)


def test_dui_refusal_scenario_keeps_core_charge_path_results():
    results = search_entries('driver was weaving and refused breath test', 'ALL')
    codes = [item.entry.code for item in results[:6]]
    assert 'OCGA 40-6-391' in codes
    assert 'OCGA 40-5-67.1' in codes
    assert 'OCGA 40-6-392' in codes


def test_prescription_pill_possession_filters_out_form_and_forgery_only_statutes():
    results = search_entries('possession of prescription pills', 'ALL')
    codes = [item.entry.code for item in results[:8]]
    assert 'OCGA 16-13-30' in codes
    assert 'OCGA 16-13-58' in codes
    assert 'OCGA 16-13-37' not in codes
    assert 'OCGA 16-13-33' not in codes


def test_legal_lookup_template_is_officer_clean_and_shows_download_action():
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    fake_user = SimpleNamespace(can_manage_site=lambda: False, can_manage_team=lambda: False, display_name='Officer Test')
    fake_entry = LegalEntry(
        source='FEDERAL_USC',
        code='18 USC 1382',
        title='Entering Military, Naval, or Coast Guard Property',
        summary='Federal installation trespass.',
        plain_language_summary='Use for barred-from-base returns.',
        elements=('Entered military property after warning.',),
        required_elements=('Entered military property after warning.',),
    )
    fake_match = SimpleNamespace(entry=fake_entry, confidence=99, certainty_bucket='strong', reasons=['matched concept: federal installation'])

    with app.test_request_context('/legal/search'):
        html = app.jinja_env.get_template('legal_lookup.html').render(
            user=fake_user,
            page_title='Legal Lookup',
            page_subtitle='Search all legal sources.',
            query='trespassing on a federal installation',
            source='ALL',
            state='GA',
            state_label='Georgia',
            state_options=(('GA', 'Georgia'), ('TX', 'Texas')),
            state_corpus_available=True,
            source_options=('ALL', 'STATE', 'UCMJ', 'BASE_ORDER', 'FEDERAL_USC'),
            example_terms=(('trespassing on a federal installation', 'ALL'),),
            ai_candidates=[],
            order_reference_matches=[],
            results=[fake_match],
            grouped_results=[{'label': 'All Sources', 'source': 'ALL', 'strongest': [fake_match], 'probable': [], 'possible': []}],
            overlap_note='',
            search_tip='Search by plain language.',
            corpus_status={},
            ai_brief='',
            ai_terms=(),
            ai_query_variants=(),
            ai_related_policy_terms=(),
            reference_download_info=lambda _entry: {'available': True},
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'Search Debug' not in html
    assert 'AI Supplemental Leads' not in html
    assert 'fallback sample set' not in html
    assert 'Open Full Text' in html
    assert 'Download Reference' in html


def test_legal_lookup_template_renders_ai_search_brief_when_present():
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    fake_user = SimpleNamespace(can_manage_site=lambda: False, can_manage_team=lambda: False, display_name='Officer Test')
    with app.test_request_context('/legal/search'):
        html = app.jinja_env.get_template('legal_lookup.html').render(
            user=fake_user,
            page_title='Legal Lookup',
            page_subtitle='Search all legal sources.',
            query='barred from base and returned',
            source='ALL',
            state='GA',
            state_label='Georgia',
            state_options=(('GA', 'Georgia'), ('TX', 'Texas')),
            state_corpus_available=True,
            source_options=('ALL', 'STATE', 'UCMJ', 'BASE_ORDER', 'FEDERAL_USC'),
            example_terms=(),
            ai_candidates=[],
            order_reference_matches=[],
            results=[],
            grouped_results=[],
            overlap_note='',
            search_tip='Search by plain language.',
            corpus_status={},
            ai_brief='Review the federal installation entry path first.',
            ai_terms=('barred from base', 'federal installation'),
            ai_query_variants=('returned after warning',),
            ai_related_policy_terms=('barment',),
            reference_download_info=lambda _entry: {'available': True},
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'AI Search Brief' in html
    assert 'Review the federal installation entry path first.' in html
    assert 'barred from base' in html


def test_legal_lookup_template_renders_state_selector_and_ai_candidate_notice():
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'))
    app.secret_key = 'test'
    app.handle_url_build_error = lambda error, endpoint, values: f'/{endpoint}'
    fake_user = SimpleNamespace(can_manage_site=lambda: False, can_manage_team=lambda: False, display_name='Officer Test')
    with app.test_request_context('/legal/search?state=TX&source=ALL&q=assault'):
        html = app.jinja_env.get_template('legal_lookup.html').render(
            user=fake_user,
            page_title='Law Lookup',
            page_subtitle='Search Texas, federal, and UCMJ.',
            query='assault',
            source='ALL',
            state='TX',
            state_label='Texas',
            state_options=(('GA', 'Georgia'), ('TX', 'Texas')),
            state_corpus_available=False,
            source_options=('ALL', 'STATE', 'UCMJ', 'BASE_ORDER', 'FEDERAL_USC'),
            example_terms=(('assault', 'STATE'),),
            ai_candidates=[
                {
                    'label': 'Texas State Law',
                    'code': 'TX Example 1',
                    'title': 'Example Candidate',
                    'why_relevant': 'Matches assault facts.',
                    'elements': ['Act', 'Intent'],
                    'verification_note': 'Verify against official Texas law.',
                }
            ],
            order_reference_matches=[],
            results=[],
            grouped_results=[],
            overlap_note='',
            search_tip='Search by plain language.',
            corpus_status={},
            ai_brief='',
            ai_terms=(),
            ai_query_variants=(),
            ai_related_policy_terms=(),
            reference_download_info=lambda _entry: {'available': True},
            portal_effective_role='PATROL_OFFICER',
            portal_effective_role_label='Patrol Officer',
            portal_show_origin_banner=False,
            portal_origin_label='',
            portal_is_site_controller=False,
            portal_watch_commanders=[],
            portal_watch_commander_scope_id=None,
        )
    assert 'Texas' in html
    assert 'Candidate laws to verify' in html
    assert 'Verify against official Texas law.' in html


def test_exact_title_and_keyword_queries_hold_the_expected_lead_result():
    cases = {
        'Aggravated Sexual Battery': 'OCGA 16-6-22',
        'aggravated sexual battery': 'OCGA 16-6-22',
        'Stalking': 'OCGA 16-5-90',
        'stalking': 'OCGA 16-5-90',
        'vandalism': 'OCGA 16-7-1',
        'speeding': 'OCGA 40-6-181',
    }
    for query, expected_code in cases.items():
        results = search_entries(query, 'ALL')
        assert results, query
        assert results[0].entry.code == expected_code, (query, [item.entry.code for item in results[:5]])


def test_title_led_queries_keep_the_source_statute_first():
    cases = {
        'Aggravated Sexual Battery aggravated sexual battery': 'OCGA 16-6-22',
        'Duty Upon Striking a Vehicle (Hit and Run) hit and run': 'OCGA 40-6-270',
        'Controlled Substances - Possession / Distribution / Manufacture drug possession': 'OCGA 16-13-30',
        'Possession of Firearms and Dangerous Weapons in Federal Facilities firearm in federal facility': '18 USC 930',
    }
    for query, expected_code in cases.items():
        results = search_entries(query, 'ALL')
        assert results, query
        assert results[0].entry.code == expected_code, (query, [item.entry.code for item in results[:5]])
