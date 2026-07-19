from app import create_app
from app.routes.credit_center import bp as credit_center_bp

app = create_app()
app.register_blueprint(credit_center_bp)


@app.after_request
def add_credit_center_navigation(response):
    """Add the Credit Center to the shared sidebar without altering legacy templates."""
    if response.direct_passthrough or response.status_code != 200:
        return response
    if not response.content_type or 'text/html' not in response.content_type:
        return response

    html = response.get_data(as_text=True)
    dashboard_link_end = '</a>'
    dashboard_marker = "href=\"/dashboard\""
    marker_index = html.find(dashboard_marker)
    if marker_index < 0:
        dashboard_marker = "href=\"/\""
        marker_index = html.find(dashboard_marker)
    if marker_index < 0 or '/credit-center/' in html:
        return response

    link_end = html.find(dashboard_link_end, marker_index)
    if link_end < 0:
        return response
    link_end += len(dashboard_link_end)
    active_class = 'is-active' if getattr(__import__('flask').request, 'path', '') .startswith('/credit-center') else ''
    credit_link = (
        f'<a class="{active_class}" href="/credit-center/">'
        '<svg class="nav-icon" viewBox="0 0 16 16" width="16" height="16" fill="none" '
        'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
        '<rect x="2" y="2" width="12" height="12" rx="2"/>'
        '<path d="M5 6h6M5 9h4M11 10.5v2M10 11.5h2"/>'
        '</svg>Credit Center</a>'
    )
    html = html[:link_end] + credit_link + html[link_end:]
    response.set_data(html)
    response.headers['Content-Length'] = len(response.get_data())
    return response
