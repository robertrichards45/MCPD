from flask import session

from app import create_app
from app.extensions import db
from app.models import Form, ROLE_PATROL_OFFICER, User


def _make_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REQUIRE_PERSISTENT_DATABASE", "0")
    app = create_app()
    app.config["TESTING"] = True
    return app


def test_demo_rows_are_hidden_from_normal_requests(monkeypatch):
    app = _make_app(monkeypatch)
    with app.app_context():
        real_user = User(
            username="real.officer",
            role=ROLE_PATROL_OFFICER,
            active=True,
            pending_approval=False,
        )
        real_user.set_password("TestPass123!")
        demo_user = User(
            username="demo.officer",
            role=ROLE_PATROL_OFFICER,
            active=True,
            pending_approval=False,
            is_demo=True,
        )
        demo_user.set_password("TestPass123!")
        real_form = Form(title="Official Real Form", file_path="forms/real.pdf", is_active=True)
        demo_form = Form(
            title="DEMO Sample Form",
            file_path="demo/forms/sample.pdf",
            is_active=True,
            is_demo=True,
        )
        db.session.add_all([real_user, demo_user, real_form, demo_form])
        db.session.commit()

    with app.test_request_context("/forms"):
        form_titles = [
            row.title
            for row in Form.query.filter(Form.title.in_(["Official Real Form", "DEMO Sample Form"]))
            .order_by(Form.title.asc())
            .all()
        ]
        usernames = [
            row.username
            for row in User.query.filter(User.username.in_(["real.officer", "demo.officer"]))
            .order_by(User.username.asc())
            .all()
        ]

    assert form_titles == ["Official Real Form"]
    assert usernames == ["real.officer"]


def test_demo_rows_are_visible_when_demo_mode_is_active(monkeypatch):
    app = _make_app(monkeypatch)
    with app.app_context():
        db.session.add_all(
            [
                Form(title="Official Real Form", file_path="forms/real.pdf", is_active=True),
                Form(
                    title="DEMO Sample Form",
                    file_path="demo/forms/sample.pdf",
                    is_active=True,
                    is_demo=True,
                ),
            ]
        )
        db.session.commit()

    with app.test_request_context("/forms"):
        session["demo_mode"] = True
        form_titles = [
            row.title
            for row in Form.query.filter(Form.title.in_(["Official Real Form", "DEMO Sample Form"]))
            .order_by(Form.title.asc())
            .all()
        ]

    assert form_titles == ["DEMO Sample Form", "Official Real Form"]
