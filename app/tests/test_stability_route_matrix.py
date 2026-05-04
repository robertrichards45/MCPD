from html.parser import HTMLParser

from app import create_app
from app.extensions import db
from app.models import Report, User


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])


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


def _dispose_app(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def _internal_links(html):
    parser = _LinkParser()
    parser.feed(html)
    links = []
    for href in parser.links:
        if href.startswith(('#', 'mailto:', 'tel:', 'http://', 'https://', 'javascript:')):
            continue
        links.append(href)
    return links


def test_primary_pages_render_without_blank_or_dead_links():
    client = _logged_in_client()
    try:
        pages = [
            '/dashboard',
            '/mobile/home',
            '/mobile/incident/start',
            '/mobile/incident/basics',
            '/mobile/incident/recommended-forms',
            '/mobile/incident/persons',
            '/mobile/incident/facts',
            '/mobile/incident/narrative-review',
            '/mobile/incident/packet-review',
            '/mobile/incident/send-packet',
            '/reports',
            '/reports/accident-reconstruction',
            '/reports/new',
            '/forms',
            '/forms/saved',
            '/incident-paperwork-guide',
            '/incident-paperwork-guide/manage',
            '/legal/search?q=pooping+in+the+street&source=ALL&state=GA',
            '/orders/reference',
            '/training/menu',
            '/officers',
            '/reconstruction',
        ]
        for path in pages:
            response = client.get(
                path,
                headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile'},
                follow_redirects=True,
            )
            assert response.status_code == 200, path
            html = response.get_data(as_text=True)
            assert html.strip(), path
            assert 'Traceback' not in html
            assert 'href="#"' not in html

        for source in ['/dashboard', '/reports', '/forms', '/mobile/home']:
            html = client.get(source).get_data(as_text=True)
            for href in _internal_links(html):
                if any(token in href for token in ('/download', '/preview', '/pdf', '/export', '/static/')):
                    continue
                target = client.get(href)
                assert target.status_code not in {404, 500}, f'{source} -> {href} returned {target.status_code}'
    finally:
        _dispose_app(client.application)
