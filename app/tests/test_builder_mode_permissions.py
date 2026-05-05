from app import create_app
from app.extensions import db
from app.models import AuditLog, ROLE_PATROL_OFFICER, ROLE_WEBSITE_CONTROLLER, User
from app.permissions import can_access_builder_mode, is_site_owner


def _login(client, user):
    with client.session_transaction() as session:
        session.clear()
        session['_user_id'] = str(user.id)
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

        non_owner_client = app.test_client()
        _login(non_owner_client, non_owner_admin)
        assert non_owner_client.get('/admin/site-builder').status_code == 403
        assert 'Site Builder' not in non_owner_client.get('/dashboard').get_data(as_text=True)

        owner_client = app.test_client()
        _login(owner_client, owner)
        assert owner_client.get('/admin/site-builder').status_code == 200

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
