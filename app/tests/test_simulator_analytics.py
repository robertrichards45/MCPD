import json

from app import create_app
from app.extensions import db
from app.fto_models import FTOScenarioRun
from app.models import ROLE_WEBSITE_CONTROLLER, User
from app.simulator.analytics import aggregate_patterns, compare_runs, summarize_run


def _state(run_id='S003-123456789', interviews=1, preserve=True, interventions=0, hidden_evidence=False):
    actions = [
        {'action_type': 'radio_status'},
        {'action_type': 'observe'},
        {'action_type': 'legal_assessment'},
    ]
    actions.extend({'action_type': 'interview'} for _ in range(interviews))
    if preserve:
        actions.append({'action_type': 'preserve_evidence'})
    timeline = [
        {'event_type': 'trainee_action', 'details': {'actions': actions}},
        {'event_type': 'npc_response', 'actor': 'Witness One', 'details': {'actor_id': 'witness1'}},
    ]
    if interviews >= 2:
        timeline.append({'event_type': 'npc_response', 'actor': 'Witness Two', 'details': {'actor_id': 'witness2'}})
    evidence = {
        'damage': {
            'status': 'preserved' if preserve else 'lost',
        },
    }
    if hidden_evidence:
        evidence['camera'] = {'status': 'hidden'}
    return {
        'scenario_id': 'S003',
        'run_context': {'run_id': run_id},
        'complete': True,
        'terminated': False,
        'intervention_count': interventions,
        'revision_count': interventions,
        'actor_interactions': interviews,
        'world': {
            'clock': 8,
            'timeline': timeline,
            'people': {
                'witness1': {'discovered': True, 'status': 'present'},
                'witness2': {'discovered': True, 'status': 'present'},
            },
            'evidence': evidence,
        },
    }


def test_run_summary_and_comparison_use_observed_actions_not_a_score():
    first = _state('S003-111111111', interviews=1, preserve=False, interventions=2, hidden_evidence=True)
    second = _state('S003-222222222', interviews=2, preserve=True, interventions=0)
    first_summary = summarize_run(first)
    second_summary = summarize_run(second)
    assert first_summary['people_contacted'] == 1
    assert first_summary['uncontacted_people'] == 1
    assert first_summary['uncontacted_people_ids'] == ['witness2']
    assert first_summary['evidence_lost'] == 1
    assert first_summary['evidence_undiscovered'] == 1
    assert set(first_summary['missed_evidence_ids']) == {'damage', 'camera'}
    assert first_summary['missed_opportunity_count'] == 3
    assert second_summary['people_contacted'] == 2
    assert second_summary['uncontacted_people'] == 0
    assert second_summary['evidence_preserved'] == 1

    comparison = compare_runs(first, second)
    rows = {row['key']: row for row in comparison['rows']}
    assert rows['people_contacted']['delta'] == 1
    assert rows['uncontacted_people']['delta'] == -1
    assert rows['evidence_preserved']['delta'] == 1
    assert rows['evidence_undiscovered']['delta'] == -1
    assert rows['interventions']['delta'] == -2
    assert 'score' not in comparison


def test_cross_call_patterns_remain_advisory_and_count_missed_opportunities():
    analytics = aggregate_patterns([
        _state('S003-1', interviews=1, preserve=False, interventions=1, hidden_evidence=True),
        _state('S003-2', interviews=2, preserve=True, interventions=0),
        _state('S003-3', interviews=2, preserve=True, interventions=0),
    ])
    assert analytics['run_count'] == 3
    assert analytics['patterns']
    assert analytics['total_interventions'] == 1
    assert analytics['total_uncontacted_people'] == 1
    assert analytics['total_evidence_undiscovered'] == 1
    assert analytics['total_missed_opportunities'] == 3
    assert 'not DOR ratings' in analytics['advisory']


def test_authorized_fto_analytics_page_compares_completed_runs():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        controller = User.query.filter_by(username='scenario-analytics-controller').first()
        if controller is None:
            controller = User(
                username='scenario-analytics-controller',
                name='Scenario Analytics Controller',
                role=ROLE_WEBSITE_CONTROLLER,
                active=True,
                pending_approval=False,
            )
            controller.set_password('ci-only-password')
            db.session.add(controller)
        trainee = User.query.filter_by(username='scenario-analytics-trainee').first()
        if trainee is None:
            trainee = User(
                username='scenario-analytics-trainee',
                name='Scenario Analytics Trainee',
                role='OFFICER',
                active=True,
                pending_approval=False,
            )
            trainee.set_password('ci-only-password')
            db.session.add(trainee)
        db.session.commit()

        existing = FTOScenarioRun.query.filter_by(trainee_id=trainee.id, scenario_id='S003').all()
        if len(existing) < 2:
            for index, state in enumerate((
                _state('S003-333333331', interviews=1, preserve=False, interventions=1, hidden_evidence=True),
                _state('S003-333333332', interviews=2, preserve=True, interventions=0),
            ), start=1):
                if FTOScenarioRun.query.filter_by(run_id=state['run_context']['run_id']).first() is None:
                    db.session.add(FTOScenarioRun(
                        run_id=state['run_context']['run_id'],
                        scenario_id='S003',
                        seed=333333330 + index,
                        trainee_id=trainee.id,
                        mode='EVALUATION',
                        status='COMPLETED',
                        state_json=json.dumps(state),
                    ))
            db.session.commit()
        runs = FTOScenarioRun.query.filter_by(trainee_id=trainee.id, scenario_id='S003').order_by(FTOScenarioRun.id.asc()).limit(2).all()
        trainee_id = trainee.id
        controller_id = controller.id
        first_id, second_id = runs[0].id, runs[1].id

    client = app.test_client()
    with client.session_transaction() as s:
        s['_user_id'] = str(controller_id)
        s['_fresh'] = True
        s['_csrf_token'] = 'test-token'

    response = client.get(f'/sentinel/fto-center/scenario-lab/analytics/{trainee_id}?first={first_id}&second={second_id}')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Performance Patterns' in html
    assert 'Compare Two Runs' in html
    assert 'Available people not contacted' in html
    assert 'Evidence opportunities not developed' in html
    assert 'Advisory only' in html
    assert 'automatic training decision' in html
    assert 'Evaluator Replay' in html