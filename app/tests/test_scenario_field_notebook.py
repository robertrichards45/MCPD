from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.field_notebook import add_field_note, field_notes, revise_field_note


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-notebook-ci').first()
        if user is None:
            user = User(
                username='scenario-notebook-ci',
                name='Scenario Notebook CI Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
        client = app.test_client()
        with client.session_transaction() as s:
            s['_user_id'] = str(user_id)
            s['_fresh'] = True
            s['_csrf_token'] = 'test-token'
    return client


def test_notebook_service_preserves_original_when_revised():
    state = {
        'scenario_id': 'S001',
        'run_context': {'run_id': 'TEST-NOTEBOOK', 'choices': {}},
    }
    first = add_field_note(state, 'Witness says the vehicle arrived around 1300.', category='statement')
    assert first['id'] == 'N001'
    assert first['status'] == 'active'

    revised = revise_field_note(
        state,
        first['id'],
        'Witness clarified the vehicle arrived around 1310.',
        category='statement',
    )
    assert revised['id'] == 'N002'
    assert revised['revision_of'] == 'N001'

    all_notes = field_notes(state, include_superseded=True)
    assert len(all_notes) == 2
    assert all_notes[0]['status'] == 'superseded'
    assert all_notes[1]['status'] == 'active'
    assert field_notes(state) == [all_notes[1]]

    timeline = state['world']['timeline']
    assert [row['event_type'] for row in timeline] == ['field_note_added', 'field_note_revised']
    assert all(row['visible_to_trainee'] is False for row in timeline)


def test_live_scenario_exposes_field_notebook_link_and_saves_note():
    client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Field Notebook' in html

    response = client.get('/sentinel/fto-center/scenario-notebook/')
    assert response.status_code == 200
    assert 'Training Field Notes' in response.get_data(as_text=True)

    response = client.post('/sentinel/fto-center/scenario-notebook/', data={
        '_csrf_token': 'test-token',
        'action': 'add',
        'category': 'evidence',
        'note_text': 'Photographs obtained during the synthetic call.',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Photographs obtained during the synthetic call.' in response.get_data(as_text=True)

    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        notes = state['world']['field_notes']
        assert len(notes) == 1
        assert notes[0]['category'] == 'evidence'
        assert notes[0]['status'] == 'active'


def test_closed_run_notebook_is_read_only():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    client.post('/sentinel/fto-center/scenario-notebook/', data={
        '_csrf_token': 'test-token',
        'action': 'add',
        'category': 'general',
        'note_text': 'Original note.',
    }, follow_redirects=True)

    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        state['complete'] = True
        s['sentinel_scenario_lab_v2'] = state

    response = client.post('/sentinel/fto-center/scenario-notebook/', data={
        '_csrf_token': 'test-token',
        'action': 'add',
        'category': 'general',
        'note_text': 'Late note that should not be added.',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'can no longer be changed' in response.get_data(as_text=True)

    with client.session_transaction() as s:
        notes = s['sentinel_scenario_lab_v2']['world']['field_notes']
        assert len(notes) == 1
        assert notes[0]['text'] == 'Original note.'


def test_virtual_patrol_has_specific_scenario_picker_and_random_call_button():
    client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Choose the Call You Want to Work' in html
    assert 'Medical Assist with Conflicting Information' in html
    assert 'Traffic Stop - Escalating Driver' in html
    assert 'Random Call' in html
    assert 'Start Selected' in html


def test_end_call_moves_to_paperwork_even_when_core_stages_are_unfinished():
    client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')
    assert response.status_code == 200

    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['turn'] == 0
        assert state['complete'] is False

    response = client.post('/sentinel/fto-center/scenario-notebook/complete-call', data={
        '_csrf_token': 'test-token',
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Training Package' in html
    assert 'Call closed' in html

    with client.session_transaction() as s:
        state = s['sentinel_scenario_lab_v2']
        assert state['complete'] is True
        assert state['post_call_handoff']['cleared_before_all_core_stages'] is True
        assert state['post_call_handoff']['turn_at_clear'] == 0
