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


def test_fto_instructor_returns_category_scoring_and_followup():
    client = _client()
    response = client.post(
        '/sentinel/fto-instructor',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S001',
            'response_text': (
                '214 copy, en route. I will advise dispatch on scene, maintain distance and position, '
                'watch the subject hands, request backup, separate and interview the witness, ask the subject '
                'what occurred, determine whether reasonable suspicion or probable cause exists before detention '
                'or arrest, and document statements and evidence in the report.'
            ),
        },
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'AI FTO Instructor' in html
    assert 'Radio communication' in html
    assert 'Officer safety' in html
    assert 'Legal authority' in html
    assert 'Training aid only' in html


def test_forms_and_accident_tools_show_simplified_guidance():
    client = _client()

    forms = client.get('/forms').get_data(as_text=True)
    assert 'Simple paperwork workflow' in forms

    accidents = client.get('/reports/accidents').get_data(as_text=True)
    assert 'Which workflow do I need?' in accidents
    assert 'Crash packet review' in accidents
