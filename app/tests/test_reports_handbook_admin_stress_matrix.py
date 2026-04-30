import json
import shutil
from io import BytesIO
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Report, User
from app.routes import reference


def _isolated_app(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[2]
    source_db = root / 'data' / 'app.db'
    temp_db = tmp_path / 'stress-app.db'
    shutil.copy2(source_db, temp_db)
    upload_root = tmp_path / 'uploads'
    upload_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{temp_db.as_posix()}")
    monkeypatch.setenv('UPLOAD_ROOT', str(upload_root))
    app = create_app()
    app.config['TESTING'] = True
    return app


def _logged_in_client(app):
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _handbook_queries(app, limit=540):
    with app.app_context():
        payload = reference._load_handbook()
        scenarios = reference._load_incident_scenarios()

    queries = []
    for section in payload.get('sections', []):
        title = str(section.get('title') or section.get('id') or '').strip()
        summary = str(section.get('summary') or '').strip()
        if title:
            queries.append(('/officer-handbook', title, title))
            queries.append(('/officer-handbook', title.lower(), title))
            queries.append(('/officer-handbook', ' '.join(title.split()[:2]), title))
        if summary:
            queries.append(('/officer-handbook', ' '.join(summary.split()[:4]), title or 'Officer Handbook'))
        for topic in section.get('topics') or []:
            topic_title = str(topic.get('title') or '').strip()
            if topic_title:
                queries.append(('/officer-handbook', topic_title, topic_title))
                queries.append(('/officer-handbook', topic_title.lower(), topic_title))
        for guide in section.get('form_guides') or []:
            form_name = str(guide.get('form_name') or '').strip()
            if form_name:
                queries.append(('/officer-handbook', form_name, form_name))

    for scenario in scenarios:
        title = str(scenario.get('title') or scenario.get('label') or scenario.get('incident') or '').strip()
        if not title:
            continue
        queries.append(('/incident-paperwork-guide', title, title))
        queries.append(('/incident-paperwork-guide', title.lower(), title))
        words = title.split()
        queries.append(('/incident-paperwork-guide', words[0], title))
        if len(words) > 1:
            queries.append(('/incident-paperwork-guide', ' '.join(words[:2]), title))
        for item in (scenario.get('required_paperwork') or [])[:2]:
            if isinstance(item, dict):
                label = str(item.get('search_term') or item.get('label') or '').strip()
            else:
                label = str(item).strip()
            if label:
                queries.append(('/incident-paperwork-guide', label, title))

    unique = []
    seen = set()
    for route, query, expected in queries:
        key = (route, query.strip().lower(), expected.strip().lower())
        if not query.strip() or key in seen:
            continue
        seen.add(key)
        unique.append((route, query, expected))
    while len(unique) < limit:
        unique.extend(unique[: min(len(unique), limit - len(unique))])
    return unique[:limit]


def test_reports_stress_matrix_500_plus(monkeypatch, tmp_path):
    app = _isolated_app(monkeypatch, tmp_path)
    try:
        client = _logged_in_client(app)
        total = 0

        for idx in range(70):
            response = client.post('/reports/new', data={'title': f'Stress Report {idx:03d}'}, follow_redirects=False)
            assert response.status_code in {302, 303}
            report_id = int(response.headers['Location'].rstrip('/').split('/')[-1])
            total += 1

            response = client.get(f'/reports/{report_id}')
            assert response.status_code == 200
            assert f'Stress Report {idx:03d}' in response.get_data(as_text=True)
            total += 1

            response = client.post(
                f'/reports/{report_id}/add-person',
                data={'name': f'Victim {idx:03d}', 'role': 'Victim'},
                follow_redirects=False,
            )
            assert response.status_code in {302, 303}
            total += 1

            response = client.post(
                f'/reports/{report_id}/add-coauthor',
                data={'username': 'ROBERTRICHARDS'},
                follow_redirects=False,
            )
            assert response.status_code in {302, 303}
            total += 1

            upload = BytesIO(b'%PDF-1.4 stress report attachment')
            response = client.post(
                f'/reports/{report_id}/upload',
                data={'page_key': f'page-{idx}', 'file': (upload, f'attachment-{idx}.pdf')},
                content_type='multipart/form-data',
                follow_redirects=False,
            )
            assert response.status_code in {302, 303}
            total += 1

            response = client.post(f'/reports/{report_id}/submit', follow_redirects=False)
            assert response.status_code in {302, 303}
            total += 1

            invalid_grade = client.post(
                f'/reports/{report_id}/grade',
                data={'score': 'not-a-number', 'comments': 'bad input', 'required_fixes': ''},
                follow_redirects=False,
            )
            assert invalid_grade.status_code in {302, 303}
            total += 1

            valid_grade = client.post(
                f'/reports/{report_id}/grade',
                data={'score': str((idx % 101)), 'comments': 'graded', 'required_fixes': ''},
                follow_redirects=False,
            )
            assert valid_grade.status_code in {302, 303}
            total += 1

        with app.app_context():
            graded = Report.query.filter_by(status='GRADED').count()
            assert graded >= 60

        assert total >= 500
    finally:
        _dispose_app(app)


def test_handbook_and_navigator_stress_matrix_500_plus(monkeypatch, tmp_path):
    app = _isolated_app(monkeypatch, tmp_path)
    try:
        client = _logged_in_client(app)
        queries = _handbook_queries(app)
        assert len(queries) >= 500

        failures = []
        for route, query, expected in queries:
            response = client.get(route, query_string={'q': query})
            if response.status_code != 200:
                failures.append((route, query, response.status_code))
                continue
            html = response.get_data(as_text=True)
            if 'Traceback' in html:
                failures.append((route, query, 'TRACEBACK'))
                continue
            if expected not in html:
                failures.append((route, query, f'MISSING:{expected}'))
        assert not failures[:10], failures[:10]
    finally:
        _dispose_app(app)


def test_handbook_admin_validation_and_admin_stress_matrix_500_plus(monkeypatch, tmp_path):
    app = _isolated_app(monkeypatch, tmp_path)
    try:
        client = _logged_in_client(app)
        target_username = 'robertrichards'

        temp_additions = tmp_path / 'officer_handbook_additions.json'
        temp_additions.write_text(json.dumps(reference._default_additions_payload()), encoding='utf-8')
        monkeypatch.setattr(reference, '_handbook_additions_file', lambda: str(temp_additions))

        invalid_admin = client.post(
            '/officer-handbook/admin',
            data={'handbook_json': '{"title":"Bad","sections":"not-a-list"}'},
            follow_redirects=False,
        )
        assert invalid_admin.status_code in {302, 303}

        valid_admin = client.post(
            '/officer-handbook/admin',
            data={'handbook_json': json.dumps({'title': 'Patched', 'version': '2', 'sections': []})},
            follow_redirects=False,
        )
        assert valid_admin.status_code in {302, 303}

        total = 2

        for idx in range(65):
            response = client.post('/role/switch/WEBSITE_CONTROLLER', data={'next': '/dashboard'}, follow_redirects=False)
            assert response.status_code in {302, 303}
            total += 1

            response = client.get('/admin/users')
            assert response.status_code == 200
            total += 1

            response = client.post(
                '/admin/users',
                data={
                    'action': 'create',
                    'first_name': 'Bad',
                    'last_name': 'Supervisor',
                    'username': f'bad.supervisor.{idx}',
                    'password': 'TempPass123!',
                    'phone_number': '555-000-0000',
                    'address': '2 Test Way',
                    'role': 'PATROL_OFFICER',
                    'supervisor_id': 'not-a-number',
                },
            )
            assert response.status_code == 200
            assert 'Supervisor selection is invalid.' in response.get_data(as_text=True)
            total += 1

            response = client.post(
                '/admin/users',
                data={'action': 'issue_code', 'username': target_username, 'hours': 'bad-hours'},
            )
            assert response.status_code == 200
            assert 'Enrollment hours must be a whole number.' in response.get_data(as_text=True)
            total += 1

            response = client.post(
                '/admin/users',
                data={'action': 'update', 'username': target_username, 'role': 'PATROL_OFFICER', 'supervisor_id': 'oops'},
            )
            assert response.status_code == 200
            assert 'Supervisor selection is invalid.' in response.get_data(as_text=True)
            total += 1

            response = client.post('/role/scope', data={'watch_commander_id': 'oops'}, follow_redirects=False)
            assert response.status_code == 400
            total += 1

            response = client.post('/role/switch/WEBSITE_CONTROLLER', data={'next': '/dashboard'}, follow_redirects=False)
            assert response.status_code in {302, 303}
            total += 1

            response = client.post('/role/switch/WATCH_COMMANDER', data={'next': '/dashboard'}, follow_redirects=False)
            assert response.status_code in {302, 303}
            total += 1

            response = client.post('/admin/users', data={'action': 'reset', 'username': target_username, 'password': 'ResetPass123!'}, follow_redirects=False)
            assert response.status_code in {302, 303}
            total += 1

        assert total >= 500
    finally:
        _dispose_app(app)
