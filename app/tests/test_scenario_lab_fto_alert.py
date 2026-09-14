from app import create_app
from app.extensions import db
from app.fto_models import FTOProgramAssignment, FTOScenarioAlert
from app.models import ROLE_FIELD_TRAINING, ROLE_PATROL_OFFICER, User
from app.routes.fto_refinements import dashboard_attention_items


def test_terminal_scenario_outcome_creates_advisory_fto_center_alert():
    app = create_app()
    app.config['TESTING'] = True

    with app.app_context():
        trainee = User.query.filter_by(username='scenario-alert-trainee').first()
        if trainee is None:
            trainee = User(
                username='scenario-alert-trainee',
                name='Scenario Alert Trainee',
                role=ROLE_PATROL_OFFICER,
                active=True,
                pending_approval=False,
            )
            trainee.set_password('ci-only-password')
            db.session.add(trainee)

        fto = User.query.filter_by(username='scenario-alert-fto').first()
        if fto is None:
            fto = User(
                username='scenario-alert-fto',
                name='Scenario Alert FTO',
                role=ROLE_FIELD_TRAINING,
                active=True,
                pending_approval=False,
            )
            fto.set_password('ci-only-password')
            db.session.add(fto)
        db.session.commit()

        assignment = FTOProgramAssignment.query.filter_by(trainee_id=trainee.id, status='ACTIVE').first()
        if assignment is None:
            assignment = FTOProgramAssignment(
                trainee_id=trainee.id,
                assigned_fto_id=fto.id,
                program_type='standard',
                status='ACTIVE',
                current_week=1,
            )
            db.session.add(assignment)
            db.session.commit()

        FTOScenarioAlert.query.filter_by(trainee_id=trainee.id).delete()
        db.session.commit()
        trainee_id = trainee.id
        fto_id = fto.id

    client = app.test_client()
    with client.session_transaction() as s:
        s['_user_id'] = str(trainee_id)
        s['_fresh'] = True
        s['_csrf_token'] = 'test-token'

    client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S001')
    response = client.post(
        '/sentinel/fto-center/scenario-lab/',
        data={
            '_csrf_token': 'test-token',
            'scenario_id': 'S001',
            'action': 'act',
            'response_text': 'I shoot the person immediately even though no deadly threat has been presented.',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        alert = FTOScenarioAlert.query.filter_by(trainee_id=trainee_id).order_by(FTOScenarioAlert.id.desc()).first()
        assert alert is not None
        assert alert.assigned_fto_id == fto_id
        assert alert.scenario_id == 'S001'
        assert alert.severity == 'CRITICAL'
        assert alert.acknowledged_at is None

        fto = db.session.get(User, fto_id)
        attention = dashboard_attention_items(fto)
        critical = [item for item in attention if item['label'] == 'Critical Scenario Lab Alerts']
        assert critical
        assert int(critical[0]['value']) >= 1
        assert 'not automatic DOR findings' in critical[0]['detail']
