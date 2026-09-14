import json

from app import create_app
from app.extensions import db
from app.fto_models import FTOScenarioEvent
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.run_store import persist_run
from app.simulator.world_state import add_known_information, add_timeline, apply_interpreted_actions, ensure_world_state


def _user_id(app):
    with app.app_context():
        user = User.query.filter_by(username='replay-snapshot-ci').first()
        if user is None:
            user = User(
                username='replay-snapshot-ci',
                name='Replay Snapshot CI',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        return user.id


def test_persisted_replay_snapshot_does_not_gain_later_information():
    app = create_app()
    app.config['TESTING'] = True
    user_id = _user_id(app)

    state = {
        'scenario_id': 'S001',
        'run_context': {'run_id': 'S001-555555551', 'seed': 555555551},
        'complete': False,
        'terminated': False,
    }
    world = ensure_world_state(state, 'S001')
    add_known_information(state, 'Initial caller says there is an argument.', source='dispatch')
    add_timeline(state, 'decision_point', 'Officer decides how to approach.', actor='Trainee', channel='scene')

    add_known_information(state, 'Later witness says they saw the entire exchange.', source='witness')
    world['clock'] = 3
    add_timeline(state, 'witness_update', 'Later witness account developed.', actor='Witness', channel='face_to_face')

    with app.app_context():
        run = persist_run(state, user_id)
        events = FTOScenarioEvent.query.filter_by(scenario_run_id=run.id).order_by(FTOScenarioEvent.sequence.asc()).all()
        assert len(events) == 2
        first_snapshot = json.loads(events[0].world_snapshot_json)
        second_snapshot = json.loads(events[1].world_snapshot_json)
        first_info = [row['text'] for row in first_snapshot['known_information']]
        second_info = [row['text'] for row in second_snapshot['known_information']]
        assert 'Initial caller says there is an argument.' in first_info
        assert 'Later witness says they saw the entire exchange.' not in first_info
        assert 'Later witness says they saw the entire exchange.' in second_info
        assert first_snapshot['clock'] == 0
        assert second_snapshot['clock'] == 3


def test_trainee_action_snapshot_is_pre_action_world_state():
    state = {
        'scenario_id': 'S003',
        'run_context': {'run_id': 'S003-555555552', 'seed': 555555552},
    }
    world = ensure_world_state(state, 'S003')
    assert world['officer']['location'] == 'enroute'

    apply_interpreted_actions(
        state,
        [{'action_type': 'radio_status', 'target': 'dispatch', 'reason': 'on_scene'}],
        raw_text='214, show me on scene.',
        channel='radio',
    )
    action_event = state['world']['timeline'][0]
    assert action_event['event_type'] == 'trainee_action'
    assert action_event['world_snapshot']['officer']['location'] == 'enroute'
    assert state['world']['officer']['location'] == 'scene'
