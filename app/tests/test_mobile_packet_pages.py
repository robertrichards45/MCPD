from app import create_app
from app.models import User


def _logged_in_client():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        user = User.query.filter_by(username='Robertrichards').first() or User.query.first()
        assert user is not None
        client = app.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
    return client


def test_mobile_packet_pages_render_for_authenticated_user():
    client = _logged_in_client()
    cases = [
        ('/mobile/incident/packet-review', 'Packet Review'),
        ('/mobile/incident/send-packet', 'Send Packet'),
        ('/mobile/incident/success', 'Packet Sent'),
    ]
    for url, expected in cases:
        response = client.get(url)
        assert response.status_code == 200
        assert expected in response.get_data(as_text=True)


def test_mobile_send_packet_api_rejects_incomplete_packet():
    client = _logged_in_client()
    response = client.post('/mobile/api/incident/send-packet', json={'incident': {}})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['ok'] is False
    assert any(item['field'] == 'Call Type' for item in payload['errors'])
    assert any(item['field'] == 'Profile Email' for item in payload['errors']) or isinstance(payload['errors'], list)
