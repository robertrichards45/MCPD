"""Isolated loopback-only fixture server for responsive browser regressions.

Never imported by the production app. No test authentication routes are added.
All data and signed sessions belong to a temporary, synthetic database.
"""
import json
import os
from pathlib import Path
import sys
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
folder = Path(sys.argv[1]).resolve()
folder.mkdir(parents=True, exist_ok=True)
os.environ.update(
    APP_ENV='dev', REQUIRE_PERSISTENT_DATABASE='0',
    MCPD_DATABASE_URL='sqlite:///' + (folder / 'responsive.db').as_posix(),
    DATABASE_URL='sqlite:///' + (folder / 'responsive.db').as_posix(),
    SECRET_KEY='synthetic-responsive-tests-only', ADMIN_USERNAME='responsive-audit',
    SITE_OWNER_USERNAME='responsive-audit', ADMIN_PASSWORD='synthetic-tests-only',
    UPLOAD_ROOT=str(folder / 'uploads'), LEGAL_AI_EXPANSION_ENABLED='0',
    ORDERS_AI_ASSIST_ENABLED='0', LEGAL_QUERY_LOG_ENABLED='0',
    OPENAI_API_KEY='', MCPD_OPENAI_API_KEY='', OPENAI_KEY='',
)
from app import create_app
from app.extensions import db
from app.models import User, Form, ROLE_PATROL_OFFICER
from app.fto_models import FTOProgramAssignment, FTODailyObservation
from werkzeug.serving import make_server

app = create_app()
app.config['TESTING'] = True
with app.app_context():
    owner = User.query.filter_by(username='responsive-audit').one()
    officer = User(username='responsive-officer', name='Synthetic Officer With A Long Display Name',
                   role=ROLE_PATROL_OFFICER, active=True, pending_approval=False)
    officer.set_password('synthetic-tests-only')
    db.session.add(officer)
    db.session.flush()
    assignment = FTOProgramAssignment(trainee_id=officer.id, assigned_fto_id=owner.id,
        supervisor_id=owner.id, created_by=owner.id, start_date=date(2026, 9, 14))
    db.session.add(assignment)
    db.session.flush()
    dor = FTODailyObservation(assignment_id=assignment.id, evaluator_id=owner.id,
        training_date=date(2026, 9, 14), comments='Synthetic mobile layout test. ' * 20)
    db.session.add(dor)
    db.session.commit()
    owner_id, officer_id = owner.id, officer.id
    detail_paths = [f'/admin/users/{officer.id}/edit',
        f'/sentinel/fto-center/programs/{assignment.id}',
        f'/sentinel/fto-center/dor/{dor.id}/edit']
    # The app seeds its approved form catalog into this fresh database.
    for form in Form.query.limit(3).all():
        detail_paths.append(f'/forms/{form.id}/fill')

def session_client(user_id):
    client = app.test_client()
    with client.session_transaction() as s:
        s['_user_id'] = str(user_id)
        s['_fresh'] = True
        s['_csrf_token'] = 'responsive-token'
    return client

live = session_client(owner_id)
live.get('/sentinel/fto-center/scenario-lab/?scenario_id=S007')
with live.session_transaction() as s:
    run_id = s['sentinel_scenario_lab_v2']['run_context']['run_id']
detail_paths += [f'/sentinel/fto-center/scenario-lab/evaluator/{run_id}',
    f'/sentinel/fto-center/scenario-lab/review/{run_id}',
    f'/sentinel/fto-center/scenario-lab/instructor/{run_id}',
    f'/sentinel/fto-center/scenario-lab/analytics/{owner_id}']
for path in ['/reports/accidents/officer-diagram/new', '/reports/accidents/reconstruction/new']:
    response = live.get(path)
    assert response.status_code in (302, 303)
    detail_paths.append(response.headers['Location'])

complete = session_client(owner_id)
complete.get('/sentinel/fto-center/scenario-lab/?scenario_id=S004')
with complete.session_transaction() as s:
    state = s['sentinel_scenario_lab_v2']
    state['complete'] = True
    s['sentinel_scenario_lab_v2'] = state
complete.post('/sentinel/fto-center/scenario-paperwork/', data={
    '_csrf_token':'responsive-token', 'action':'submit',
    'selected_documents':['OPNAV 5580 2 Voluntary Statement'], 'cid_decision':'screen',
    'notification_notes':'Synthetic training review.',
    'narrative':'Synthetic training narrative for responsive testing. ' * 10,
})

server = make_server('127.0.0.1', 0, app, threaded=True)
base = f'http://127.0.0.1:{server.server_port}'
def cookie(client):
    value = client.get_cookie(app.config['SESSION_COOKIE_NAME'])
    return {'name': value.key, 'value': value.value, 'url': base}

(folder / 'manifest.json').write_text(json.dumps({'base':base, 'details':detail_paths,
    'live':cookie(live), 'complete':cookie(complete),
    'officer':cookie(session_client(officer_id))}), encoding='utf-8')
server.serve_forever()
