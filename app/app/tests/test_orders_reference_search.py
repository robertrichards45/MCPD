from types import SimpleNamespace

import pytest

from app import create_app
from app.extensions import db
from app.models import OrderDocument
from app.routes import orders
from app.routes.orders import _display_order_match_reasons, _document_download_path, _document_source_metadata, _ensure_orders_library_seeded, _filtered_orders, _reader_context, search_orders_with_ai_assist


def test_orders_library_auto_seeds_when_empty():
    app = create_app()
    with app.app_context():
        inserted, skipped = _ensure_orders_library_seeded()
        assert inserted >= 0
        assert skipped >= 0
        assert OrderDocument.query.count() > 0


def test_plain_language_search_haircut_returns_grooming_standard():
    app = create_app()
    with app.app_context():
        _ensure_orders_library_seeded()
        docs = _filtered_orders('haircut', '', 'ACTIVE')
        assert docs
        assert docs[0].title == 'Marine Corps Grooming and Haircut Standards'
        assert 'grooming' in (docs[0].match_snippet or '').lower() or 'hair' in (docs[0].match_snippet or '').lower()


def test_plain_language_search_watch_commander_duties_returns_command_result():
    app = create_app()
    with app.app_context():
        _ensure_orders_library_seeded()
        docs = _filtered_orders('watch commander duties', '', 'ACTIVE')
        assert docs
        assert 'watch commander' in docs[0].title.lower()
        assert docs[0].match_reference or docs[0].match_snippet


def test_plain_language_search_vehicle_inspection_returns_gate_or_vehicle_policy():
    app = create_app()
    with app.app_context():
        _ensure_orders_library_seeded()
        docs = _filtered_orders('vehicle inspection', '', 'ACTIVE')
        assert docs
        top_title = docs[0].title.lower()
        assert 'vehicle' in top_title or 'inspection' in (docs[0].match_snippet or '').lower()


def test_orders_search_excludes_unapproved_domain_pollution():
    app = create_app()
    with app.app_context():
        bad = OrderDocument(
            title='Indeed Leave Policy Mirror',
            category='Personnel',
            source_type='MEMORANDUM',
            source_group='https://www.indeed.com/viewjob?jk=123',
            memo_number='BAD-1',
            summary='Leave policy and grooming references.',
            extracted_text='leave policy grooming vehicle inspection',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\bad-indeed.txt',
            is_active=True,
        )
        good = OrderDocument(
            title='Leave and Liberty Administrative Guidance',
            category='Personnel',
            source_type='MEMORANDUM',
            source_group='USMC',
            memo_number='GOOD-1',
            summary='Leave policy guidance for command approval.',
            extracted_text='leave policy absence vacation command approval',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\seed-good-leave.txt',
            is_active=True,
        )
        db.session.add_all([bad, good])
        db.session.commit()
        try:
            docs = _filtered_orders('leave policy', '', 'ACTIVE')
            titles = [doc.title for doc in docs]
            assert 'Leave and Liberty Administrative Guidance' in titles
            assert 'Indeed Leave Policy Mirror' not in titles
        finally:
            db.session.delete(bad)
            db.session.delete(good)
            db.session.commit()


def test_orders_search_ignores_unrelated_policy_only_results():
    app = create_app()
    with app.app_context():
        relevant = OrderDocument(
            title='Leave and Liberty Administrative Guidance',
            category='Personnel',
            source_type='MEMORANDUM',
            source_group='USMC',
            memo_number='LEAVE-1',
            summary='Leave policy guidance for command approval and liberty management.',
            extracted_text='leave policy liberty absence command approval travel leave',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\leave-guidance.txt',
            is_active=True,
        )
        unrelated = OrderDocument(
            title='Tattoo Policy Guidance',
            category='Personnel',
            source_type='MEMORANDUM',
            source_group='USMC',
            memo_number='TAT-1',
            summary='Tattoo policy and appearance standards.',
            extracted_text='tattoo policy grooming appearance standards body art',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\tattoo-guidance.txt',
            is_active=True,
        )
        db.session.add_all([relevant, unrelated])
        db.session.commit()
        try:
            docs = _filtered_orders('leave policy', '', 'ACTIVE')
            titles = [doc.title for doc in docs]
            assert 'Leave and Liberty Administrative Guidance' in titles
            assert 'Tattoo Policy Guidance' not in titles
        finally:
            db.session.delete(unrelated)
            db.session.delete(relevant)
            db.session.commit()


def test_orders_search_requires_search_context_not_just_authorization():
    app = create_app()
    with app.app_context():
        relevant = OrderDocument(
            title='Search Authorization and Consent Inspections',
            category='Operations',
            source_type='MEMORANDUM',
            source_group='USMC',
            memo_number='SEARCH-1',
            summary='Search authorization guidance for consent inspections and command approvals.',
            extracted_text='search authorization consent inspections probable cause command approval search procedures',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\search-auth.txt',
            is_active=True,
        )
        unrelated = OrderDocument(
            title='Authorization Routing Sheet',
            category='Administration',
            source_type='MEMORANDUM',
            source_group='USMC',
            memo_number='AUTH-1',
            summary='Authorization and approval routing for administrative requests.',
            extracted_text='authorization approval routing signature chain administrative request',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\auth-routing.txt',
            is_active=True,
        )
        db.session.add_all([relevant, unrelated])
        db.session.commit()
        try:
            docs = _filtered_orders('search authorization', '', 'ACTIVE')
            titles = [doc.title for doc in docs]
            assert 'Search Authorization and Consent Inspections' in titles
            assert 'Authorization Routing Sheet' not in titles
        finally:
            db.session.delete(unrelated)
            db.session.delete(relevant)
            db.session.commit()


def test_unapproved_document_source_metadata_flags_blocked_domains():
    app = create_app()
    with app.app_context():
        document = OrderDocument(
            title='Bad Source',
            category='General',
            source_type='MEMORANDUM',
            source_group='USMC Official | https://www.indeed.com/viewjob?jk=123',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\bad-source.txt',
            is_active=True,
        )
        metadata = _document_source_metadata(document)
        assert not metadata['approved']
        assert 'blocked' in (metadata['blocked_reason'] or '').lower() or 'allowlist' in (metadata['blocked_reason'] or '').lower()


def test_source_metadata_does_not_block_approved_order_just_because_title_contains_shoplifting():
    app = create_app()
    with app.app_context():
        document = OrderDocument(
            title='Shoplifting and Exchange/PX Theft Response Procedure',
            category='Theft Enforcement',
            source_type='MEMORANDUM',
            source_group='MCLB Albany',
            summary='Guidance for retail theft incidents on installation.',
            extracted_text='Aliases: shoplifting from px, retail theft base',
            file_path=r'C:\Users\rober\Desktop\mcpd-portal\app\data\uploads\orders\seed-shoplifting.txt',
            source_version='seed-v1',
            is_active=True,
        )
        metadata = _document_source_metadata(document)
        assert metadata['approved'] is True
        assert metadata['origin_label'] == 'Seed Library'


def test_display_order_match_reasons_returns_clean_officer_language():
    reasons = _display_order_match_reasons(['body:haircut', 'exact phrase in summary', 'body:haircut'])
    assert reasons == [
        'matched "haircut" in the source text',
        'matched the exact phrase in the summary',
    ]


def test_reader_context_keeps_match_first_with_surrounding_text():
    text = "\n".join(
        [
            "Section General Standards",
            "All personnel will maintain a professional appearance.",
            "Haircut standards require a neat military appearance.",
            "Unauthorized beard growth is prohibited.",
            "Commanders may inspect grooming compliance.",
        ]
    )
    context = _reader_context(text, 'haircut', before=1, after=1, extra_before=2, extra_after=2)
    assert context['focus_blocks']
    assert 'haircut' in context['focus_blocks'][0]['text'].lower()
    assert context['leading_blocks']
    assert context['trailing_blocks']
    assert context['reference']


def test_orders_search_does_not_fallback_to_random_results_when_no_match():
    app = create_app()
    with app.app_context():
        _ensure_orders_library_seeded()
        docs = _filtered_orders('zzqvnonexistentpolicyterm', '', 'ACTIVE')
        assert docs == []


def test_orders_ai_assist_can_recover_from_poor_plain_language_query(monkeypatch):
    app = create_app()
    with app.app_context():
        _ensure_orders_library_seeded()
        monkeypatch.setitem(app.config, 'ORDERS_AI_ASSIST_ENABLED', True)
        monkeypatch.setattr(
            orders,
            '_ai_order_search_strategy',
            lambda *_args, **_kwargs: {
                'priority_terms': ['haircut'],
                'query_variants': ['haircut grooming standards'],
                'topic_hints': ['grooming'],
                'audience_hints': [],
                'officer_brief': 'Open the grooming standard first.',
            },
        )
        docs, strategy = search_orders_with_ai_assist('zzqvnonexistentpolicyterm')
        assert docs
        assert docs[0].title == 'Marine Corps Grooming and Haircut Standards'
        assert strategy['officer_brief'] == 'Open the grooming standard first.'


def test_download_route_only_serves_local_order_files(monkeypatch):
    app = create_app()
    document = SimpleNamespace(file_path=r'C:\Windows\System32\drivers\etc\hosts')
    with app.app_context():
        assert _document_download_path(document) == ''
        monkeypatch.setattr(orders.OrderDocument, 'query', SimpleNamespace(get_or_404=lambda _id: document))
        with app.test_request_context('/orders/999/download'):
            with pytest.raises(Exception) as excinfo:
                orders.download_order.__wrapped__(999)
        assert getattr(excinfo.value, 'code', None) == 404


def test_reference_results_hide_download_for_invalid_target_and_keep_open_text():
    app = create_app()
    with app.app_context():
        document = SimpleNamespace(
            id=77,
            title='Broken Download Link',
            source_type='MEMORANDUM',
            audience_label='',
            is_active=True,
            category='General',
            order_number=None,
            memo_number=None,
            source_group='USMC Official',
            summary='Result should still open in-site text.',
            match_snippet='Haircut guidance remains readable in site view.',
            match_reference='Section Grooming Standards',
            download_available=False,
            version_label='v1',
            source_version='v1',
            issue_date=None,
            revision_date=None,
            search_confidence=91,
            match_reasons=['body:haircut'],
        )
        with app.test_request_context('/orders/reference?q=haircut'):
            user = SimpleNamespace(can_manage_team=lambda: False)
            html = app.jinja_env.get_template('orders_reference.html').render(
                user=user,
                documents=[document],
                categories=[],
                search_term='haircut',
                category_filter='',
                status_filter='ACTIVE',
                source_type_filter='',
                year_filter='',
                topic_filter='',
                source_filter='',
                can_manage_orders=False,
                source_type_options=[],
                source_groups=[],
                years=[],
                topic_values=[],
                display_dt=lambda value: value,
                ai_guidance='',
            )
    assert '/orders/77/view?q=haircut' in html
    assert '/orders/77/download' not in html
    assert 'Download not available' in html


def test_reference_results_show_clean_no_result_message():
    app = create_app()
    with app.app_context():
        with app.test_request_context('/orders/reference?q=zzqvnonexistentpolicyterm'):
            user = SimpleNamespace(can_manage_team=lambda: False)
            html = app.jinja_env.get_template('orders_reference.html').render(
                user=user,
                documents=[],
                categories=[],
                search_term='zzqvnonexistentpolicyterm',
                category_filter='',
                status_filter='ACTIVE',
                source_type_filter='',
                year_filter='',
                topic_filter='',
                source_filter='',
                can_manage_orders=False,
                source_type_options=[],
                source_groups=[],
                years=[],
                topic_values=[],
                display_dt=lambda value: value,
                ai_guidance='',
            )
    assert 'No approved order/reference source found for this search.' in html
