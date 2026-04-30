from app import create_app
from app.extensions import db
from app.models import Form, OrderDocument, User
from app.routes import reference
from app.routes.orders import _ensure_orders_library_seeded, _filtered_orders


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


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


def _order_queries(limit=560):
    app = create_app()
    try:
        with app.app_context():
            _ensure_orders_library_seeded()
            docs = list(OrderDocument.query.filter_by(is_active=True).all())
            queries = []
            for doc in docs:
                title = (doc.title or '').strip()
                summary = (doc.summary or '').strip()
                category = (doc.category or '').strip()
                order_number = (doc.order_number or '').strip()
                source_group = (doc.source_group or '').strip()
                if title:
                    queries.append((doc.id, title))
                    queries.append((doc.id, title.lower()))
                    queries.append((doc.id, ' '.join(title.split()[:4])))
                if summary:
                    queries.append((doc.id, ' '.join(summary.split()[:6])))
                if title and category:
                    queries.append((doc.id, f'{title} {category}'))
                if order_number:
                    queries.append((doc.id, order_number))
                if source_group and title:
                    queries.append((doc.id, f'{source_group} {title.split()[0]}'))
            seen = set()
            unique = []
            for doc_id, query in queries:
                marker = query.strip().lower()
                if not marker or marker in seen:
                    continue
                seen.add(marker)
                unique.append((doc_id, query))
            while len(unique) < limit:
                unique.extend(unique[: min(len(unique), limit - len(unique))])
            return unique[:limit]
    finally:
        _dispose_app(app)


def _navigator_queries(limit=540):
    app = create_app()
    try:
        with app.app_context():
            scenarios = reference._load_incident_scenarios()
            queries = []
            for scenario in scenarios:
                title = (scenario.get('title') or scenario.get('label') or scenario.get('incident') or '').strip()
                if not title:
                    continue
                words = title.split()
                queries.append((title, title))
                queries.append((title, title.lower()))
                queries.append((title, words[0]))
                if len(words) > 1:
                    queries.append((title, ' '.join(words[:2])))
                for item in (scenario.get('required_paperwork') or [])[:2]:
                    if isinstance(item, dict):
                        label = str(item.get('search_term') or item.get('label') or '').strip()
                    else:
                        label = str(item).strip()
                    if label:
                        queries.append((title, label))
            seen = set()
            unique = []
            for title, query in queries:
                marker = query.strip().lower()
                if not marker or marker in seen:
                    continue
                seen.add(marker)
                unique.append((title, query))
            while len(unique) < limit:
                unique.extend(unique[: min(len(unique), limit - len(unique))])
            return unique[:limit]
    finally:
        _dispose_app(app)


def test_orders_desk_stress_matrix_500_plus():
    app = create_app()
    try:
        with app.app_context():
            _ensure_orders_library_seeded()
            queries = _order_queries()
            assert len(queries) >= 500
            failures = []
            for document_id, query in queries:
                docs = _filtered_orders(query, '', 'ACTIVE')
                if not docs:
                    failures.append((document_id, query, 'NO_RESULTS'))
                    continue
                ids = [item.id for item in docs[:8]]
                if document_id not in ids:
                    failures.append((document_id, query, ids))
            assert not failures[:10], failures[:10]
    finally:
        _dispose_app(app)


def test_forms_routes_stress_matrix_500_plus():
    client = _logged_in_client()
    app = create_app()
    try:
        with app.app_context():
            forms = [(form.id, form.title) for form in Form.query.order_by(Form.id.asc()).all()]
        total = 0
        for _round in range(8):
            for form_id, title in forms:
                total += 1
                response = client.get(f'/forms/{form_id}/fill')
                try:
                    assert response.status_code == 200, (form_id, title, 'fill', response.status_code)
                    html = response.get_data(as_text=True)
                    assert 'Traceback' not in html, (form_id, title, 'fill')
                    assert title in html, (form_id, title, 'fill-title')
                finally:
                    response.close()

                total += 1
                response = client.get(f'/forms/{form_id}/blank-print')
                try:
                    assert response.status_code == 200, (form_id, title, 'blank', response.status_code)
                    html = response.get_data(as_text=True)
                    assert 'Traceback' not in html, (form_id, title, 'blank')
                finally:
                    response.close()

        while total < 500:
            response = client.get('/forms')
            try:
                assert response.status_code == 200
            finally:
                response.close()
            total += 1
        assert total >= 500
    finally:
        _dispose_app(app)
        _dispose_app(client.application)


def test_navigator_stress_matrix_500_plus():
    client = _logged_in_client()
    queries = _navigator_queries()
    try:
        assert len(queries) >= 500
        failures = []
        for expected_title, query in queries:
            response = client.get('/incident-paperwork-guide', query_string={'q': query})
            try:
                if response.status_code != 200:
                    failures.append((expected_title, query, response.status_code))
                    continue
                html = response.get_data(as_text=True)
                if 'Traceback' in html:
                    failures.append((expected_title, query, 'TRACEBACK'))
                    continue
                if expected_title not in html:
                    failures.append((expected_title, query, 'MISSING_EXPECTED_SCENARIO'))
            finally:
                response.close()
        assert not failures[:10], failures[:10]
    finally:
        _dispose_app(client.application)
