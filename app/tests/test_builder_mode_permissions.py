from app import create_app
from app.extensions import db
from app.models import AuditLog, ROLE_PATROL_OFFICER, ROLE_WEBSITE_CONTROLLER, User
from app.permissions import can_access_builder_mode, is_site_owner


def _login(client, user_or_id):
    user_id = user_or_id if isinstance(user_or_id, int) else user_or_id.id
    with client.session_transaction() as session:
        session.clear()
        session['_user_id'] = str(user_id)
        session['_fresh'] = True


def _make_user(username, role=ROLE_PATROL_OFFICER, builder=False):
    existing = User.query.filter_by(username=username).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    user = User(
        username=username,
        first_name=username,
        last_name='Test',
        role=role,
        active=True,
        pending_approval=False,
        builder_mode_access=builder,
    )
    user.set_password('test-password')
    db.session.add(user)
    db.session.commit()
    return user


def test_site_builder_owner_only_by_default():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        owner = User.query.filter(User.username.ilike('robertrichards')).first()
        assert owner is not None
        non_owner_admin = _make_user('builder_non_owner_admin', ROLE_WEBSITE_CONTROLLER)
        assert is_site_owner(non_owner_admin) is False
        assert can_access_builder_mode(non_owner_admin) is False
        owner_id = owner.id
        non_owner_admin_id = non_owner_admin.id

    non_owner_client = app.test_client()
    _login(non_owner_client, non_owner_admin_id)
    assert non_owner_client.get('/admin/site-builder').status_code == 403
    assert 'Site Builder' not in non_owner_client.get('/dashboard').get_data(as_text=True)

    owner_client = app.test_client()
    _login(owner_client, owner_id)
    assert owner_client.get('/admin/site-builder').status_code == 200

    with app.app_context():
        non_owner_admin = db.session.get(User, non_owner_admin_id)
        db.session.delete(non_owner_admin)
        db.session.commit()


def test_builder_grant_requires_owner_confirmations_and_audits():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        owner = User.query.filter(User.username.ilike('robertrichards')).first()
        assert owner is not None
        target = _make_user('builder_target_officer')

        client = app.test_client()
        _login(client, owner)

        response = client.post(
            f'/admin/users/{target.id}/edit',
            data={
                'first_name': target.first_name,
                'last_name': target.last_name,
                'role': ROLE_PATROL_OFFICER,
                'active': '1',
                'builder_mode_access': '1',
            },
        )
        assert response.status_code == 200
        assert 'requires both confirmations' in response.get_data(as_text=True)

        db.session.refresh(target)
        assert target.builder_mode_access is False

        response = client.post(
            f'/admin/users/{target.id}/edit',
            data={
                'first_name': target.first_name,
                'last_name': target.last_name,
                'role': ROLE_PATROL_OFFICER,
                'active': '1',
                'builder_mode_access': '1',
                'builder_confirm_risk': '1',
                'builder_confirm_ai': '1',
                'builder_confirm_phrase': 'GRANT BUILDER',
                'builder_reason': 'Testing controlled grant',
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        db.session.refresh(target)
        assert target.builder_mode_access is True
        assert AuditLog.query.filter_by(action='builder_mode_grant').order_by(AuditLog.id.desc()).first() is not None

        _login(client, target)
        assert client.get('/admin/site-builder').status_code == 200

        db.session.delete(target)
        db.session.commit()


def test_site_builder_creates_and_updates_requests():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        owner = User.query.filter(User.username.ilike('robertrichards')).first()
        assert owner is not None
        owner_id = owner.id

    from pathlib import Path
    request_file = Path(app.instance_path) / 'site_builder' / 'requests.json'
    if request_file.exists():
        request_file.unlink()

    client = app.test_client()
    _login(client, owner_id)
    response = client.get('/admin/site-builder')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Create Builder Request' in html
    assert 'No builder requests yet.' in html

    response = client.post(
        '/admin/site-builder/requests',
        data={
            'title': 'Fix mobile More page route',
            'request_type': 'Bug Fix',
            'priority': 'High',
            'area': 'Mobile More',
            'description': 'The More page route should render professional cards and not fail.',
            'acceptance': 'Request appears in Site Builder and can be tracked.',
        },
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Fix mobile More page route' in html
    assert 'NEW' in html

    import json
    rows = json.loads(request_file.read_text(encoding='utf-8'))
    assert len(rows) == 1
    request_id = rows[0]['id']

    response = client.post(
        f'/admin/site-builder/requests/{request_id}/status',
        data={'status': 'APPROVED'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert 'APPROVED' in response.get_data(as_text=True)

    with app.app_context():
        assert AuditLog.query.filter_by(action='site_builder_request_create').order_by(AuditLog.id.desc()).first() is not None
        assert AuditLog.query.filter_by(action='site_builder_request_status').order_by(AuditLog.id.desc()).first() is not None

    if request_file.exists():
        request_file.unlink()
