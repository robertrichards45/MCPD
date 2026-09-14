from app import create_app
from app.models import User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
            session['_csrf_token'] = 'test-token'
    return client


def test_report_inspector_detects_missing_disposition_and_offense_cues():
    client = _client()
    narrative = (
        'At 1302, 20 Aug 2026, Marine Corps Police were dispatched to Building 7130 '
        'for damage to government property. The complainant stated a truck struck a light pole. '
        'The reporting officer arrived, made contact, observed the damaged government property, '
        'and photographed the damage.'
    )
    response = client.post(
        '/sentinel/report-inspector',
        data={'_csrf_token': 'test-token', 'narrative': narrative},
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Report Quality Inspector' in html
    assert 'Damage to Government Property' in html
    assert 'Disposition may be missing' in html
    assert 'Do not add facts merely to satisfy this check' in html


def test_fto_center_returns_expanded_category_scoring_and_followup():
    client = _client()
    response = client.post(
        '/sentinel/fto-center',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S001',
            'response_text': (
                '214 copy, en route. I will advise dispatch on scene, maintain distance and position, '
                'watch the subject hands, request backup, separate and interview the witness, ask the subject '
                'what occurred, assess risk, use de-escalation, determine whether reasonable suspicion or probable '
                'cause exists before detention or arrest, remain professional, follow policy, and document statements '
                'and evidence in the report.'
            ),
        },
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'FTO Center' in html
    assert 'Radio Communication' in html
    assert 'Officer Safety' in html
    assert 'Legal Authority' in html
    assert 'Judgment / Decision Making' in html
    assert 'Professionalism' in html
    assert 'Policy / Procedure Awareness' in html
    assert 'assigned FTO/instructor owns the final rating' in html


def test_old_fto_instructor_get_redirects_to_fto_center():
    client = _client()
    response = client.get('/sentinel/fto-instructor', follow_redirects=False)
    assert response.status_code in {301, 302, 303, 307, 308}
    assert '/sentinel/fto-center' in response.headers['Location']


def test_universal_portal_search_renders_safe_workflow_shortcuts():
    client = _client()
    response = client.get('/sentinel/search?q=training')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Search' in html
    assert 'Law &amp; Legal Search' in html or 'Law & Legal Search' in html
    assert 'Orders &amp; Memos' in html or 'Orders & Memos' in html
    assert 'Narrative Creator' in html
    assert 'FTO Center' in html
    assert 'Report search uses report titles/status only' in html


def test_retired_incident_command_and_shift_checkin_redirect():
    client = _client()
    for path in ('/incident-command', '/incident-command/', '/watch-commander/sign-on'):
        response = client.get(path, follow_redirects=False)
        assert response.status_code in {301, 302, 303, 307, 308}, path
        assert '/dashboard' in response.headers['Location'], path


def test_dashboard_hides_retired_tools_and_exposes_new_workflows():
    client = _client()
    response = client.get('/dashboard')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Needs My Attention' in html
    assert 'FTO Center' in html
    assert 'Incident Command' not in html
    assert 'Shift Check-In' not in html
    assert 'Check In' not in html


def test_forms_and_accident_tools_show_simplified_guidance():
    client = _client()

    forms = client.get('/forms').get_data(as_text=True)
    assert 'Simple paperwork workflow' in forms

    accidents = client.get('/reports/accidents').get_data(as_text=True)
    assert 'Guided Crash Intake' in accidents
    assert 'Build My Crash Checklist' in accidents
    assert 'Crash packet review' in accidents
    assert 'Sentinel Review' in accidents
