import json

from app import create_app
from app.extensions import db
from app.fto_models import FTOScenarioRun
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.instructor_control import inject_event


def _state():
    return {
        'scenario_id': 'S004',
        'run_context': {'run_id': 'S004-444444444', 'seed': 444444444},
        'complete': False,
        'terminated': False,
        'world': {
            'world_version': 1,
            'scenario_id': 'S004',
            'run_id': 'S004-444444444',
            'clock': 3,
            'status': 'active',
            'officer': {'location': 'scene', 'available': False},
            'environment': {'weather': 'clear', 'lighting': 'normal', 'noise': 'normal', 'visibility': 'normal', 'crowd': 'none'},
            'people': {},
            'resources': {
                'backup': {'status': 'enroute', 'requested_at': 1, 'eta': 4},
                'ems': {'status': 'not_requested', 'requested_at': None, 'eta': None},
                'fire': {'status': 'not_requested', 'requested_at': None, 'eta': None},
                'supervisor': {'status': 'available_by_radio'},
                'investigations': {'status': 'available_by_request'},
            },
            'evidence': {
                'retail_video': {'id': 'retail_video', 'label': 'Retail video', 'status': 'hidden', 'discovered_at': None},
            },
            'records': {},
            'known_information': [],
            'outstanding_tasks': [],
            'radio_log': [],
            'timeline': [],
            'irreversible_events': [],
            'last_actions': [],
            'pending_radio': [],
            'scheduled_events': [],
            'coaching_mode': False,
            'fto_message': '',
            'paused': False,
            'truth': {
                'scenario_id': 'S004',
                'people': {'lp': {'private_facts': []}, 'subject': {'private_facts': []}},
                'evidence': {'retail_video': {'exists': True, 'label': 'Retail video'}},
            },
        },
    }


def test_instructor_cannot_create_unconfigured_evidence():
    state = _state()
    result = inject_event(state, 'evidence_available', target_id='invented_weapon')
    assert result['ok'] is False
    assert 'invented_weapon' not in state['world']['evidence']
    assert state['world']['evidence']['retail_video']['status'] == 'hidden'


def test_instructor_can_surface_existing_evidence_and_delay_enroute_backup():
    state = _state()
    result = inject_event(state, 'evidence_available', target_id='retail_video')
    assert result['ok'] is True
    assert state['world']['evidence']['retail_video']['status'] == 'available'

    result = inject_event(state, 'backup_delay', delay=3)
    assert result['ok'] is True
    assert state['world']['resources']['backup']['eta'] == 7
    assert any(row.get('speaker') == 'Dispatch' for row in state['world']['radio_log'])


def test_instructor_updates_enter_timeline_as_human_overrides():
    state = _state()
    result = inject_event(state, 'caller_update', text='a second involved person has walked toward the parking area')
    assert result['ok'] is True
    event = state['world']['timeline'][-1]
    assert event['event_type'] == 'instructor_caller_update'
    assert event['details']['instructor_injected'] is True
    assert event['visible_to_trainee'] is True

    result = inject_event(state, 'environment_change', environment={'weather': 'light rain', 'visibility': 'reduced'})
    assert result['ok'] is True
    assert state['world']['environment']['weather'] == 'light rain'
    assert state['world']['environment']['visibility'] == 'reduced'


def test_authorized_controller_can_open_instructor_control_page():
    app = create_app()
    app.config['TESTING'] = True
    state = _state()
    with app.app_context():
        controller = User.query.filter_by(username='scenario-instructor-controller').first()
        if controller is None:
            controller = User(
                username='scenario-instructor-controller',
                name='Scenario Instructor Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            controller.set_password('ci-only-password')
            db.session.add(controller)
        trainee = User.query.filter_by(username='scenario-instructor-trainee').first()
        if trainee is None:
            trainee = User(
                username='scenario-instructor-trainee',
                name='Scenario Instructor Trainee',
                role='OFFICER',
                active=True,
                pending_approval=False,
            )
            trainee.set_password('ci-only-password')
            db.session.add(trainee)
        db.session.commit()
        run = FTOScenarioRun.query.filter_by(run_id='S004-444444444').first()
        if run is None:
            run = FTOScenarioRun(
                run_id='S004-444444444', scenario_id='S004', seed=444444444,
                trainee_id=trainee.id, mode='EVALUATION', status='ACTIVE',
                state_json=json.dumps(state),
            )
            db.session.add(run)
            db.session.commit()
        controller_id = controller.id

    client = app.test_client()
    with client.session_transaction() as s:
        s['_user_id'] = str(controller_id)
        s['_fresh'] = True
        s['_csrf_token'] = 'test-token'

    response = client.get('/sentinel/fto-center/scenario-lab/instructor/S004-444444444')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Instructor Event Control' in html
    assert 'Structured overrides only' in html
    assert 'Surface an Existing Opportunity' in html
