from app import create_app
from app.models import User


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter(User.username.ilike('robertrichards')).first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def test_rfi_and_truck_gate_are_not_globally_hidden():
    client = _logged_in_client()

    rfi_response = client.get('/rfi')
    truck_gate_response = client.get('/truck-gate')

    assert rfi_response.status_code in {200, 302, 303, 403}
    assert truck_gate_response.status_code in {200, 302, 303, 403}
    assert rfi_response.status_code != 404
    assert truck_gate_response.status_code != 404
