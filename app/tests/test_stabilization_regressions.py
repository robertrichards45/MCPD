from app import create_app
from app.extensions import db
from app.models import Report, ReportAttachment, ReportCoAuthor, ReportGrade, ReportPerson, User


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def test_stress_reports_are_hidden_from_dashboard_and_reports_list():
    client = _logged_in_client()
    titles = [
        'Stress Report 999',
        'Test Report 999',
        'Mock Stress Report 999',
        'Real Patrol Report',
    ]
    try:
        with client.application.app_context():
            user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
            Report.query.filter(Report.title.in_(titles)).delete(synchronize_session=False)
            for title in titles:
                db.session.add(Report(title=title, owner_id=user.id, status='DRAFT'))
            db.session.commit()

        dashboard = client.get('/dashboard').get_data(as_text=True)
        reports = client.get('/reports').get_data(as_text=True)

        assert 'Real Patrol Report' in reports
        assert 'Stress Report 999' not in dashboard
        assert 'Stress Report 999' not in reports
        assert 'Test Report 999' not in dashboard
        assert 'Test Report 999' not in reports
        assert 'Mock Stress Report 999' not in dashboard
        assert 'Mock Stress Report 999' not in reports
    finally:
        with client.application.app_context():
            ids = [row.id for row in Report.query.filter(Report.title.in_(titles)).all()]
            if ids:
                ReportAttachment.query.filter(ReportAttachment.report_id.in_(ids)).delete(synchronize_session=False)
                ReportPerson.query.filter(ReportPerson.report_id.in_(ids)).delete(synchronize_session=False)
                ReportCoAuthor.query.filter(ReportCoAuthor.report_id.in_(ids)).delete(synchronize_session=False)
                ReportGrade.query.filter(ReportGrade.report_id.in_(ids)).delete(synchronize_session=False)
                Report.query.filter(Report.id.in_(ids)).delete(synchronize_session=False)
                db.session.commit()
        _dispose_app(client.application)


def test_mobile_scanner_library_is_lazy_loaded_and_has_clean_fallbacks():
    client = _logged_in_client()
    try:
        person_page = client.get('/mobile/incident/persons/edit').get_data(as_text=True)
        runtime = client.get('/static/mobile/incident-core.js?v=2026-05-01-stable-1').get_data(as_text=True)

        assert 'MCPD_ZXING_SRC' in person_page
        assert 'zxing-browser.min.js?v=2026-05-01-stable-1' in person_page
        assert '<script src="/static/vendor/zxing-browser.min.js' not in person_page
        assert 'function loadZxingLibrary()' in runtime
        assert 'Live scan not supported on this device. Use photo upload.' in runtime
        assert 'Permission denied. Use upload instead.' in runtime
        assert 'No readable barcode found. Try again or use manual entry.' in runtime
    finally:
        _dispose_app(client.application)


def test_law_lookup_public_defecation_does_not_surface_shoplifting():
    from app.services.legal_lookup import search_entries

    results = search_entries('pooping in the street', 'ALL')
    top_codes = [item.entry.code for item in results[:5]]
    top_titles = ' '.join(item.entry.title for item in results[:5]).lower()

    assert {'OCGA 16-6-8', 'OCGA 16-11-39'} & set(top_codes)
    assert 'shoplifting' not in top_titles
