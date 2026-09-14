from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User


def _client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='scenario-radio-ci').first()
        if user is None:
            user = User(
                username='scenario-radio-ci',
                name='Scenario Radio CI Controller',
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


def test_one_radio_transmission_creates_one_trainee_timeline_card():
    client = _client()
    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    transmission = 'dispatch 310 im onscene'
    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S001',
            'action': 'radio',
            'radio_text': transmission,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with client.session_transaction() as session:
        state = session['sentinel_scenario_lab_v2']
        timeline_matches = [
            row for row in state['world']['timeline']
            if row.get('visible_to_trainee')
            and row.get('actor') == 'Trainee'
            and row.get('channel') == 'radio'
            and row.get('summary') == transmission
        ]
        radio_log_matches = [
            row for row in state['world']['radio_log']
            if row.get('speaker') == 'Trainee' and row.get('text') == transmission
        ]

    assert len(timeline_matches) == 1
    assert len(radio_log_matches) == 1
