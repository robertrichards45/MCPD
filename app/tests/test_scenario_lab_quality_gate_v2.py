from app import create_app


def test_current_virtual_patrol_sections_are_visible_and_internal_evaluator_sections_are_hidden():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    with app.app_context():
        from app.extensions import db
        from app.models import ROLE_WEBSITE_CONTROLLER, User
        user = User.query.filter_by(username='scenario-visibility-ci').first()
        if user is None:
            user = User(username='scenario-visibility-ci', name='Scenario Visibility CI', role=ROLE_WEBSITE_CONTROLLER, active=True, pending_approval=False)
            user.set_password('ci-only-password')
            db.session.add(user)
            db.session.commit()
        user_id = user.id
    with client.session_transaction() as s:
        s['_user_id'] = str(user_id)
        s['_fresh'] = True
        s['_csrf_token'] = 'test-token'
    response = client.get('/sentinel/fto-center/scenario-lab/?scenario_id=S005')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'People / Resources' in html
    assert 'Information / Evidence' in html
    for hidden_label in ('Scene Risk', 'Core Phases Cleared', 'Branch Events', 'Immediate FTO Feedback', 'Training Objective'):
        assert hidden_label not in html
