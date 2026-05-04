from app import create_app
from app.extensions import db
from app.models import ROLE_DESK_SGT, ROLE_PATROL_OFFICER, User


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
