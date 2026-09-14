from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='sentinel-ci').first()
        if user is None:
            user = User(
                username='sentinel-ci',
                name='Sentinel CI Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
                builder_mode_access=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        else:
            user.role = ROLE_WEBSITE_CONTROLLER
            user.active = True
            user.pending_approval = False
            db.session.commit()

        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
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
    assert 'do not add facts merely to satisfy this check' in html.lower()


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
    assert 'Why was this flagged?' in html


def test_fto_center_exposes_roadmaps_and_interactive_scenario_lab_entry():
    client = _client()
    response = client.get('/sentinel/fto-center')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Standard FTO Program — 8 Weeks' in html
    assert 'Accelerated FTO Program — 4 Weeks' in html
    assert 'DOR &amp; Remediation Workflow' in html or 'DOR & Remediation Workflow' in html
    assert 'Sentinel supports training and coaching only' in html
    assert 'assigned FTO/instructor owns the final rating' in html
    assert 'Open Interactive Lab' in html
    assert '/sentinel/fto-center/scenario-lab/' in html


def test_interactive_scenario_lab_reveals_staged_facts_without_persisting_raw_actions():
    client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Scenario Lab' in html
    assert 'Damage to Government Property' in html
    assert 'Decision 1 of 4' in html
    assert 'A small government-owned light pole is visibly damaged.' not in html

    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S003',
            'action': 'act',
            'response_text': 'I will advise dispatch, approach safely, identify witnesses, and photograph the damaged government property.',
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'A small government-owned light pole is visibly damaged.' in html
    assert 'Decision 2 of 4' in html
    assert 'identify or interview' in html

    with client.session_transaction() as session:
        state = session.get('sentinel_scenario_lab_v2')
        assert state is not None
        assert state['turn'] == 1
        assert 'I will advise dispatch' not in str(state)
        assert 'area_counts' in state

    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S003',
            'action': 'act',
            'response_text': 'I will interview the reporting person and determine who actually witnessed the collision.',
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'She did not witness the collision herself.' in html
    assert 'Decision 3 of 4' in html


def test_interactive_scenario_lab_completes_four_stage_flow_and_uses_seg_aligned_coaching():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')

    actions = [
        'I advise dispatch I am on scene, request backup if needed, maintain distance, and contact the reporting staff member.',
        'I approach professionally, watch the subject hands and positioning, explain why I am there, and ask the subject what occurred.',
        'I interview and separate witnesses, verify who directed the subject to leave, review available video, and assess legal authority before enforcement.',
        'I determine the appropriate disposition from the established facts, notify dispatch, document statements and evidence, and complete the report.',
    ]
    for action_text in actions:
        response = client.post(
            '/sentinel/fto-center/scenario-lab/',
            data={
                '_csrf_token': 'test-token',
                'scenario_id': 'S001',
                'action': 'act',
                'response_text': action_text,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'Ready for Coaching Review' in html
    assert '100%' in html

    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S001',
            'action': 'finish',
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'SEG-Aligned Practice Cues' in html
    assert 'text-based practice cues only, not SEG/DOR ratings' in html
    assert 'Investigative Skills' in html
    assert 'Officer Safety: General' in html
    assert 'Problem Solving / Decision Making' in html
    assert 'Report Writing / Documentation' in html
    assert 'Practice score' not in html
    assert '1/7' not in html

    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S005')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Traffic Stop - Escalating Driver' in html
    assert 'Decision 1 of 4' in html
    assert 'Ready for Coaching Review' not in html


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


def test_reports_center_contains_call_type_driven_incident_workspace():
    client = _client()
    response = client.get('/reports')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Incident Workspace' in html
    assert 'Paperwork Packet Builder' in html
    assert 'Required / Normal' in html
    assert 'Review If Applicable' in html
    assert 'Not Normally Required' in html
    assert 'Narrative Creator + Sentinel' in html
    assert 'Traffic Accident' in html


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
    assert 'Needs attention' in html
    assert 'Reports Awaiting Review' in html
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
