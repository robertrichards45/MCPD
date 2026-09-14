import json
import os
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.fto_models import FTODailyObservation, FTOProgramAssignment, FTORemediation
from app.models import (
    ROLE_FIELD_TRAINING,
    ROLE_PATROL_OFFICER,
    ROLE_WEBSITE_CONTROLLER,
    User,
)


def _build_app_and_users():
    fd, db_path = tempfile.mkstemp(prefix='mcpd-fto-program-', suffix='.db')
    os.close(fd)
    os.environ['MCPD_DATABASE_URL'] = f"sqlite:///{Path(db_path).as_posix()}"
    os.environ['REQUIRE_PERSISTENT_DATABASE'] = '0'
    app = create_app()
    app.config['TESTING'] = True
    app.config['_TEST_DB_PATH'] = db_path

    with app.app_context():
        db.create_all()
        supervisor = User(
            username='fto-supervisor-test',
            name='FTO Supervisor Test',
            role=ROLE_WEBSITE_CONTROLLER,
            active=True,
            pending_approval=False,
        )
        fto = User(
            username='fto-evaluator-test',
            name='FTO Evaluator Test',
            role=ROLE_FIELD_TRAINING,
            active=True,
            pending_approval=False,
        )
        trainee = User(
            username='fto-trainee-test',
            name='FTO Trainee Test',
            role=ROLE_PATROL_OFFICER,
            active=True,
            pending_approval=False,
        )
        outsider = User(
            username='fto-outsider-test',
            name='FTO Outsider Test',
            role=ROLE_PATROL_OFFICER,
            active=True,
            pending_approval=False,
        )
        for user in (supervisor, fto, trainee, outsider):
            user.set_password('test-only-password')
            db.session.add(user)
        db.session.commit()
        ids = {
            'supervisor': supervisor.id,
            'fto': fto.id,
            'trainee': trainee.id,
            'outsider': outsider.id,
        }
    return app, db_path, ids


def _login(client, user_id):
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
        session['_csrf_token'] = 'test-token'


def _dispose(app, db_path):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    try:
        os.remove(db_path)
    except OSError:
        pass


def _create_program(client, ids, program_type='standard'):
    _login(client, ids['supervisor'])
    return client.post(
        '/sentinel/fto-center/programs',
        data={
            '_csrf_token': 'test-token',
            'trainee_id': str(ids['trainee']),
            'assigned_fto_id': str(ids['fto']),
            'supervisor_id': str(ids['supervisor']),
            'program_type': program_type,
            'start_date': '2026-09-14',
        },
        follow_redirects=False,
    )


def test_supervisor_can_create_standard_program_and_role_scoping_holds():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        response = _create_program(client, ids)
        assert response.status_code == 302
        assert '/sentinel/fto-center/programs/' in response.headers['Location']

        with app.app_context():
            assignment = FTOProgramAssignment.query.one()
            assert assignment.program_type == 'standard'
            assert assignment.current_week == 1
            assert assignment.status == 'ACTIVE'
            assert assignment.progress_percent == 0
            assert assignment.expected_completion_date.isoformat() == '2026-11-09'

        _login(client, ids['outsider'])
        response = client.get('/sentinel/fto-center/programs/1')
        assert response.status_code == 403

        _login(client, ids['trainee'])
        response = client.get('/sentinel/fto-center/programs/1')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Human-Entered DOR Ratings' in html
        assert 'Official evaluation is human-controlled' in html
    finally:
        _dispose(app, db_path)


def test_assigned_fto_finalizes_dor_and_supervisor_advances_week():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        _create_program(client, ids)

        _login(client, ids['fto'])
        response = client.post(
            '/sentinel/fto-center/programs/1/dor',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-14',
                'scenario_id': 'S003',
                'rating_0': '4',
                'rating_1': '3',
                'rating_2': '4',
                'rating_3': '3',
                'rating_4': '4',
                'rating_5': '3',
                'rating_6': '4',
                'rating_7': '3',
                'strengths': 'Maintained officer safety and clear radio traffic.',
                'development_areas': 'Continue improving legal articulation.',
                'comments': 'Observed during field training; coaching provided.',
                'action': 'finalize',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        with app.app_context():
            dor = FTODailyObservation.query.one()
            assert dor.status == 'FINALIZED'
            assert dor.week_number == 1
            assert dor.evaluator_id == ids['fto']
            assert dor.overall_rating == 3.5
            ratings = json.loads(dor.ratings_json)
            assert ratings['Officer Safety'] == 3

        _login(client, ids['supervisor'])
        response = client.post(
            '/sentinel/fto-center/programs/1/advance',
            data={'_csrf_token': 'test-token', 'action': 'advance'},
            follow_redirects=False,
        )
        assert response.status_code == 302
        with app.app_context():
            assignment = db.session.get(FTOProgramAssignment, 1)
            assert assignment.current_week == 2
            assert assignment.progress_percent == 12
    finally:
        _dispose(app, db_path)


def test_unassigned_patrol_officer_cannot_create_dor():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        _create_program(client, ids)
        _login(client, ids['outsider'])
        response = client.post(
            '/sentinel/fto-center/programs/1/dor',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-14',
                'rating_0': '5',
                'action': 'finalize',
            },
        )
        assert response.status_code == 403
        with app.app_context():
            assert FTODailyObservation.query.count() == 0
    finally:
        _dispose(app, db_path)


def test_supervisor_review_and_trainee_acknowledgment_are_separate_actions():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        _create_program(client, ids)
        _login(client, ids['fto'])
        response = client.post(
            '/sentinel/fto-center/programs/1/dor',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-14',
                'rating_0': '3',
                'rating_1': '4',
                'action': 'finalize',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        _login(client, ids['supervisor'])
        response = client.post(
            '/sentinel/fto-center/dor/1/supervisor-review',
            data={'_csrf_token': 'test-token', 'supervisor_note': 'Reviewed with FTO.'},
            follow_redirects=False,
        )
        assert response.status_code == 302

        _login(client, ids['trainee'])
        response = client.post(
            '/sentinel/fto-center/dor/1/acknowledge',
            data={'_csrf_token': 'test-token', 'acknowledgment_note': 'Received.'},
            follow_redirects=False,
        )
        assert response.status_code == 302

        with app.app_context():
            dor = db.session.get(FTODailyObservation, 1)
            assert dor.supervisor_reviewed_by == ids['supervisor']
            assert dor.supervisor_reviewed_at is not None
            assert dor.trainee_acknowledged_at is not None
            assert dor.trainee_acknowledgment_note == 'Received.'
    finally:
        _dispose(app, db_path)


def test_open_remediation_blocks_completion_until_human_verification():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        _create_program(client, ids, program_type='accelerated')
        with app.app_context():
            assignment = db.session.get(FTOProgramAssignment, 1)
            assignment.current_week = 4
            assignment.progress_percent = 75
            db.session.commit()

        _login(client, ids['fto'])
        response = client.post(
            '/sentinel/fto-center/programs/1/dor',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-10-05',
                'rating_0': '3',
                'rating_1': '3',
                'action': 'finalize',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        response = client.post(
            '/sentinel/fto-center/programs/1/remediation',
            data={
                '_csrf_token': 'test-token',
                'area': 'Documentation',
                'plan': 'Complete two observed report-writing repetitions to standard.',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        _login(client, ids['supervisor'])
        response = client.post(
            '/sentinel/fto-center/programs/1/advance',
            data={'_csrf_token': 'test-token', 'action': 'complete', 'completion_note': 'Final review.'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert 'Open remediation items must be resolved before program completion.' in response.get_data(as_text=True)
        with app.app_context():
            assert db.session.get(FTOProgramAssignment, 1).status != 'COMPLETED'
            assert db.session.get(FTORemediation, 1).status == 'OPEN'

        response = client.post(
            '/sentinel/fto-center/remediation/1/close',
            data={'_csrf_token': 'test-token', 'verification_note': 'Observed satisfactory report-writing repetitions.'},
            follow_redirects=False,
        )
        assert response.status_code == 302
        response = client.post(
            '/sentinel/fto-center/programs/1/advance',
            data={'_csrf_token': 'test-token', 'action': 'complete', 'completion_note': 'All requirements reviewed.'},
            follow_redirects=False,
        )
        assert response.status_code == 302
        with app.app_context():
            assignment = db.session.get(FTOProgramAssignment, 1)
            assert assignment.status == 'COMPLETED'
            assert assignment.progress_percent == 100
            assert assignment.completion_recommendation == 'SUPERVISOR_COMPLETED'
            assert db.session.get(FTORemediation, 1).status == 'CLOSED'
    finally:
        _dispose(app, db_path)


def test_dor_draft_can_be_edited_and_finalized_but_finalized_record_is_locked():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        _create_program(client, ids)
        _login(client, ids['fto'])

        response = client.post(
            '/sentinel/fto-center/programs/1/dor',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-14',
                'scenario_id': 'Initial field observation',
                'rating_0': '2',
                'strengths': 'Initial strength.',
                'comments': 'Draft comments.',
                'action': 'draft',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        record = client.get('/sentinel/fto-center/programs/1')
        assert record.status_code == 200
        assert 'Edit Draft' in record.get_data(as_text=True)

        edit_page = client.get('/sentinel/fto-center/dor/1/edit')
        assert edit_page.status_code == 200
        html = edit_page.get_data(as_text=True)
        assert 'Edit Daily Observation Report' in html
        assert 'Draft comments.' in html

        _login(client, ids['outsider'])
        assert client.get('/sentinel/fto-center/dor/1/edit').status_code == 403

        _login(client, ids['fto'])
        response = client.post(
            '/sentinel/fto-center/dor/1/edit',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-15',
                'scenario_id': 'Updated observation',
                'rating_0': '4',
                'rating_1': '3',
                'strengths': 'Updated observed strength.',
                'development_areas': 'Continue report articulation.',
                'comments': 'Finalized after FTO review of the draft.',
                'action': 'finalize',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        with app.app_context():
            dor = db.session.get(FTODailyObservation, 1)
            assert dor.status == 'FINALIZED'
            assert dor.training_date.isoformat() == '2026-09-15'
            assert dor.scenario_id == 'Updated observation'
            assert dor.overall_rating == 3.5
            assert dor.finalized_at is not None
            assert 'Finalized after FTO review' in dor.comments

        assert client.get('/sentinel/fto-center/dor/1/edit').status_code == 403
    finally:
        _dispose(app, db_path)


def test_fto_attention_items_are_role_scoped_on_dashboard():
    app, db_path, ids = _build_app_and_users()
    try:
        client = app.test_client()
        _create_program(client, ids)

        _login(client, ids['fto'])
        response = client.post(
            '/sentinel/fto-center/programs/1/dor',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-14',
                'rating_0': '3',
                'action': 'draft',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        dashboard = client.get('/dashboard')
        assert dashboard.status_code == 200
        assert 'FTO DOR Drafts' in dashboard.get_data(as_text=True)

        response = client.post(
            '/sentinel/fto-center/dor/1/edit',
            data={
                '_csrf_token': 'test-token',
                'training_date': '2026-09-14',
                'rating_0': '3',
                'rating_1': '4',
                'action': 'finalize',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        _login(client, ids['supervisor'])
        dashboard = client.get('/dashboard')
        assert dashboard.status_code == 200
        assert 'FTO DORs Awaiting Review' in dashboard.get_data(as_text=True)

        _login(client, ids['trainee'])
        dashboard = client.get('/dashboard')
        assert dashboard.status_code == 200
        assert 'FTO DOR Acknowledgment' in dashboard.get_data(as_text=True)

        _login(client, ids['outsider'])
        dashboard = client.get('/dashboard')
        assert dashboard.status_code == 200
        outsider_html = dashboard.get_data(as_text=True)
        assert 'FTO DOR Drafts' not in outsider_html
        assert 'FTO DOR Acknowledgment' not in outsider_html
    finally:
        _dispose(app, db_path)
