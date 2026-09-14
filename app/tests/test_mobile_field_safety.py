from app import create_app
from app.extensions import db
from app.models import IncidentDraft, ROLE_PATROL_OFFICER, User


CSRF_TOKEN = 'mobile-field-safety-token'


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='mobile-field-safety-ci').first()
        if user is None:
            user = User(
                username='mobile-field-safety-ci',
                name='Mobile Field Safety CI Officer',
                role=ROLE_PATROL_OFFICER,
                active=True,
                pending_approval=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        IncidentDraft.query.filter_by(officer_user_id=user_id, status='ACTIVE').delete(synchronize_session=False)
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True
            session['_csrf_token'] = CSRF_TOKEN
    return client, user_id


def _headers():
    return {'X-CSRFToken': CSRF_TOKEN}


def _draft_state():
    return {
        'callType': 'general-incident',
        'incidentBasics': {
            'occurredDate': '2026-09-14',
            'occurredTime': '13:15',
            'location': 'Training Location',
            'summary': 'Test incident draft used only for CI verification.',
        },
        'facts': [
            {'id': 'what_happened', 'label': 'Brief Facts', 'value': 'Known test facts.'},
            {'id': 'officer_actions', 'label': 'Officer Actions', 'value': 'Documented test action.'},
        ],
        'persons': [{'id': 'person-1', 'name': 'Test Person', 'role': 'Witness'}],
        'statements': [{'id': 'statement-1', 'speaker': 'Test Person', 'plainLanguage': 'Test statement.'}],
        'selectedForms': ['MCPD Stat Sheet'],
        'formDrafts': {'testForm': {'fieldOne': 'preserve-me'}},
        'narrative': 'Existing narrative text that must survive draft persistence.',
        'narrativeApproved': False,
        'packetStatus': 'draft',
    }


def test_mobile_draft_api_round_trips_full_incident_state():
    client, user_id = _client()
    state = _draft_state()

    response = client.post('/mobile/api/incident/draft', json={'incident': state}, headers=_headers())
    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    restored = client.get('/mobile/api/incident/draft')
    assert restored.status_code == 200
    payload = restored.get_json()
    assert payload['ok'] is True
    assert payload['draft'] is not None
    saved = payload['draft']['state']
    assert saved['callType'] == state['callType']
    assert saved['incidentBasics']['location'] == state['incidentBasics']['location']
    assert saved['statements'] == state['statements']
    assert saved['formDrafts'] == state['formDrafts']
    assert saved['narrative'] == state['narrative']

    with client.application.app_context():
        draft = IncidentDraft.query.filter_by(officer_user_id=user_id, status='ACTIVE').first()
        assert draft is not None
        assert draft.call_type == 'general-incident'
        assert draft.location == 'Training Location'


def test_mobile_draft_write_requires_csrf_but_read_does_not():
    client, _ = _client()
    state = _draft_state()

    blocked = client.post('/mobile/api/incident/draft', json={'incident': state})
    assert blocked.status_code == 403
    assert blocked.get_json()['ok'] is False

    readable = client.get('/mobile/api/incident/draft')
    assert readable.status_code == 200
    assert readable.get_json()['ok'] is True


def test_mobile_draft_clear_requires_csrf_and_clears_active_copy():
    client, user_id = _client()
    response = client.post('/mobile/api/incident/draft', json={'incident': _draft_state()}, headers=_headers())
    assert response.status_code == 200

    blocked = client.delete('/mobile/api/incident/draft')
    assert blocked.status_code == 403

    cleared = client.delete('/mobile/api/incident/draft', headers=_headers())
    assert cleared.status_code == 200
    assert cleared.get_json()['ok'] is True

    restored = client.get('/mobile/api/incident/draft').get_json()
    assert restored['draft'] is None

    with client.application.app_context():
        assert IncidentDraft.query.filter_by(officer_user_id=user_id, status='ACTIVE').first() is None


def test_mobile_send_packet_rejects_incomplete_packet_with_valid_csrf():
    client, _ = _client()
    response = client.post(
        '/mobile/api/incident/send-packet',
        json={'incident': {}},
        headers=_headers(),
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['ok'] is False
    fields = {item.get('field') for item in payload.get('errors', [])}
    assert 'Call Type' in fields


def test_fast_capture_and_incident_pages_render_for_field_user():
    client, _ = _client()
    for path in (
        '/mobile/fast-capture',
        '/mobile/incident/start',
        '/mobile/incident/basics',
        '/mobile/incident/facts',
        '/mobile/incident/packet-review',
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        html = response.get_data(as_text=True)
        assert 'mobile-foundation' in html
        assert 'mobile-audit.css' in html
        assert 'mobile-audit.js' in html
