from app import create_app
from app.models import User
from app.services.legal_lookup import get_entries, search_entries


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


def _corpus_queries(limit=650):
    queries = []
    for entry in get_entries('ALL'):
        if entry.code:
            queries.append((entry.code, entry.code, 'code'))
        if entry.title:
            queries.append((entry.code, entry.title, 'title'))
        if entry.summary:
            queries.append((entry.code, ' '.join(entry.summary.split()[:8]), 'summary'))
        for keyword in list(entry.keywords)[:2]:
            if keyword:
                queries.append((entry.code, keyword, 'keyword'))
        if entry.title and entry.keywords:
            queries.append((entry.code, f'{entry.title} {entry.keywords[0]}', 'title+keyword'))
    seen = set()
    unique_queries = []
    for row in queries:
        marker = row[1].strip().lower()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        unique_queries.append(row)
        if len(unique_queries) >= limit:
            break
    return unique_queries


def test_legal_lookup_engine_stress_matrix_500_plus():
    queries = _corpus_queries()
    assert len(queries) >= 500
    for expected_code, query, kind in queries:
        results = search_entries(query, 'ALL')
        codes = [item.entry.code for item in results[:8]]
        assert results, (kind, expected_code, query, 'NO_RESULTS')
        assert expected_code in codes, (kind, expected_code, query, codes)


def test_legal_lookup_route_stress_matrix_500_plus():
    client = _logged_in_client()
    queries = _corpus_queries(limit=520)
    assert len(queries) >= 500
    for expected_code, query, _kind in queries:
        response = client.get('/legal/search', query_string={'q': query, 'source': 'ALL'})
        assert response.status_code == 200, (expected_code, query, response.status_code)
        html = response.get_data(as_text=True)
        assert 'Traceback' not in html, query
        assert 'Law Lookup' in html or 'Georgia Code Lookup' in html or 'UCMJ Lookup' in html, query
        assert query.split()[0] in html or expected_code in html, query
