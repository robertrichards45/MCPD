from app import create_app
from app.extensions import db
from app.models import ROLE_DESK_SGT, ROLE_PATROL_OFFICER, ROLE_WATCH_COMMANDER, User


def _logged_in_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike("robertrichards")).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)
            session["_fresh"] = True
    return client


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _delete_user(username):
    user = User.query.filter(User.username == username).first()
    if user:
        db.session.delete(user)
        db.session.commit()


def test_personnel_name_click_edit_updates_installation_shift_and_role():
    client = _logged_in_client()
    username = "pytest_assignment_officer"
    try:
        with client.application.app_context():
            _delete_user(username)
            officer = User(
                username=username,
                first_name="Assignment",
                last_name="Officer",
                role=ROLE_PATROL_OFFICER,
                active=True,
                installation="MCLB_ALBANY",
            )
            officer.set_password("TempPass123!")
            db.session.add(officer)
            db.session.commit()
            officer_id = officer.id

        list_response = client.get("/admin/users")
        list_html = list_response.get_data(as_text=True)
        assert list_response.status_code == 200
        assert f"/admin/users/{officer_id}/edit" in list_html

        edit_response = client.get(f"/admin/users/{officer_id}/edit")
        edit_html = edit_response.get_data(as_text=True)
        assert edit_response.status_code == 200
        assert "Edit Officer" in edit_html
        assert "Shift / Section" in edit_html
        assert "Installation" in edit_html

        save_response = client.post(
            f"/admin/users/{officer_id}/edit",
            data={
                "first_name": "Assignment",
                "last_name": "Officer",
                "display_name": "Sgt. Assignment Officer",
                "email": "assignment.officer@example.test",
                "phone_number": "555-0101",
                "address": "100 Command Way",
                "officer_number": "AO123",
                "edipi": "1234567890",
                "badge_employee_id": "B-123",
                "section_unit": "Bravo Shift",
                "installation": "MCB_CAMP_LEJEUNE",
                "supervisor_id": "",
                "role": ROLE_DESK_SGT,
                "active": "1",
                "can_grade_cleoc_reports": "1",
            },
            follow_redirects=False,
        )
        assert save_response.status_code in {302, 303}

        with client.application.app_context():
            officer = db.session.get(User, officer_id)
            assert officer.display_name_override == "Sgt. Assignment Officer"
            assert officer.section_unit == "Bravo Shift"
            assert officer.installation == "MCB_CAMP_LEJEUNE"
            assert officer.role == ROLE_DESK_SGT
            assert officer.can_grade_cleoc_reports is True
            assert officer.badge_employee_id == "B-123"
    finally:
        with client.application.app_context():
            _delete_user(username)
        _dispose_app(client.application)


def test_pending_account_gets_clear_login_message_until_approved():
    client = _logged_in_client()
    username = "pytest_pending_login"
    try:
        with client.application.app_context():
            _delete_user(username)
            officer = User(
                username=username,
                first_name="Pending",
                last_name="Officer",
                role=ROLE_PATROL_OFFICER,
                active=False,
                pending_approval=True,
                installation="MCLB_ALBANY",
            )
            officer.set_password("TempPass123!")
            db.session.add(officer)
            db.session.commit()

        response = client.post(
            "/login",
            data={"username": username, "password": "TempPass123!"},
            follow_redirects=True,
        )
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "waiting for Watch Commander approval" in html
    finally:
        with client.application.app_context():
            _delete_user(username)
        _dispose_app(client.application)


def test_watch_commander_can_claim_unassigned_installation_officer():
    app = create_app()
    app.config["TESTING"] = True
    wc_username = "pytest_wc_assignment"
    officer_username = "pytest_unassigned_officer"
    try:
        with app.app_context():
            _delete_user(officer_username)
            _delete_user(wc_username)
            commander = User(
                username=wc_username,
                first_name="Watch",
                last_name="Commander",
                role=ROLE_WATCH_COMMANDER,
                active=True,
                installation="MCLB_ALBANY",
                section_unit="Alpha Shift",
            )
            commander.set_password("TempPass123!")
            officer = User(
                username=officer_username,
                first_name="Unassigned",
                last_name="Officer",
                role=ROLE_PATROL_OFFICER,
                active=True,
                installation="MCLB_ALBANY",
            )
            officer.set_password("TempPass123!")
            db.session.add_all([commander, officer])
            db.session.commit()
            commander_id = commander.id
            officer_id = officer.id

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(commander_id)
            session["_fresh"] = True

        list_response = client.get("/admin/users")
        assert list_response.status_code == 200
        assert f"/admin/users/{officer_id}/edit" in list_response.get_data(as_text=True)

        save_response = client.post(
            f"/admin/users/{officer_id}/edit",
            data={
                "first_name": "Unassigned",
                "last_name": "Officer",
                "phone_number": "555-0133",
                "address": "200 Command Way",
                "section_unit": "Alpha Shift",
                "installation": "MCLB_ALBANY",
                "supervisor_id": str(commander_id),
                "role": ROLE_PATROL_OFFICER,
                "active": "1",
            },
            follow_redirects=False,
        )
        assert save_response.status_code in {302, 303}

        with app.app_context():
            officer = db.session.get(User, officer_id)
            assert officer.supervisor_id == commander_id
            assert officer.section_unit == "Alpha Shift"
    finally:
        with app.app_context():
            _delete_user(officer_username)
            _delete_user(wc_username)
        _dispose_app(app)


def test_watch_commander_role_defaults_to_assignable_watch_shift():
    client = _logged_in_client()
    username = "pytest_new_watch_commander"
    try:
        with client.application.app_context():
            _delete_user(username)

        response = client.post(
            "/admin/users",
            data={
                "action": "create",
                "first_name": "New",
                "last_name": "Commander",
                "phone_number": "555-0144",
                "address": "300 Command Way",
                "installation": "MCLB_ALBANY",
                "username": username,
                "password": "TempPass123!",
                "role": ROLE_WATCH_COMMANDER,
                "supervisor_id": "",
            },
            follow_redirects=False,
        )
        assert response.status_code in {302, 303}

        with client.application.app_context():
            commander = User.query.filter_by(username=username).first()
            assert commander is not None
            assert commander.section_unit == "New Commander Watch"
    finally:
        with client.application.app_context():
            _delete_user(username)
        _dispose_app(client.application)
