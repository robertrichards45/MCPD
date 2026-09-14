from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-visual-ci').first()
        if user is None:
            user = User(
                username='scenario-visual-ci',
                name='Scenario Visual CI Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
        session['_csrf_token'] = 'test-token'
    return client


def test_hidden_visual_evidence_does_not_leak_and_discovered_visual_is_rendered():
    client = _client()
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S003')
    assert response.status_code == 200

    with client.session_transaction() as session:
        state = session['sentinel_scenario_lab_v2']
        run_id = state['run_context']['run_id']
        assert state['world']['evidence']['property_damage']['status'] == 'hidden'

    hidden = client.get(
        f'/sentinel/fto-center/scenario-lab/evidence/{run_id}/property_damage.svg'
    )
    assert hidden.status_code == 404

    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S003',
            'action': 'officer_action',
            'command_text': (
                'I inspect the damaged government property and photograph the damage '
                'before anything is moved.'
            ),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Synthetic training visual generated from facts already developed in this run.' in html
    assert f'/scenario-lab/evidence/{run_id}/property_damage.svg' in html

    visible = client.get(
        f'/sentinel/fto-center/scenario-lab/evidence/{run_id}/property_damage.svg'
    )
    assert visible.status_code == 200
    assert visible.mimetype == 'image/svg+xml'
    svg = visible.get_data(as_text=True)
    assert 'TRAINING / SYNTHETIC' in svg
    assert 'NOT REAL EVIDENCE' in svg


def test_medical_scene_visual_stays_hidden_until_scene_observation():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S006')

    with client.session_transaction() as session:
        state = session['sentinel_scenario_lab_v2']
        run_id = state['run_context']['run_id']
        assert state['world']['evidence']['scene_layout']['status'] == 'hidden'

    hidden = client.get(
        f'/sentinel/fto-center/scenario-lab/evidence/{run_id}/scene_layout.svg'
    )
    assert hidden.status_code == 404

    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S006',
            'action': 'officer_action',
            'command_text': 'I look around the patient area for scene hazards, crowding, and EMS access.',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    visible = client.get(
        f'/sentinel/fto-center/scenario-lab/evidence/{run_id}/scene_layout.svg'
    )
    assert visible.status_code == 200
    assert 'Medical-assist scene layout' in visible.get_data(as_text=True)
