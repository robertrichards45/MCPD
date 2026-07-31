from flask import request
from flask_login import current_user

from . import auth, dashboard, forms, training, stats, annual_ai, admin, cleo_api, reports, reconstruction, officers, ops_modules, legal, orders, reference, announcements, mobile
from . import credit_simulator

# Nest the private simulator under a blueprint already registered by the app
# factory, avoiding any change to the large central application factory.
admin.bp.register_blueprint(credit_simulator.bp)


@admin.bp.after_app_request
def _inject_private_credit_center_navigation(response):
    """Add a visible Credit Center link to the normal authenticated sidebar."""
    if not getattr(current_user, 'is_authenticated', False):
        return response
    if response.direct_passthrough or response.status_code != 200:
        return response
    if response.mimetype != 'text/html':
        return response

    try:
        html = response.get_data(as_text=True)
    except (RuntimeError, UnicodeDecodeError):
        return response

    if 'href="/private/credit-simulator/"' in html or 'mcpd-command-sidebar' not in html:
        return response

    marker = '<nav aria-label="Main navigation">'
    if marker not in html:
        marker = '<nav aria-label="Main navigation"'
        marker_index = html.find(marker)
        if marker_index < 0:
            return response
        marker_end = html.find('>', marker_index)
        if marker_end < 0:
            return response
        insert_at = marker_end + 1
    else:
        insert_at = html.find(marker) + len(marker)

    active = ' is-active' if request.path.startswith('/private/credit-simulator') else ''
    link = (
        '<a class="credit-center-nav' + active + '" href="/private/credit-simulator/" '
        'title="Private credit report and score simulator">'
        '<svg class="nav-icon" viewBox="0 0 16 16" width="16" height="16" fill="none" '
        'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
        '<rect x="1.5" y="3" width="13" height="10" rx="2"/>'
        '<path d="M1.5 6h13M4 10h3"/></svg>Credit Center</a>'
    )
    html = html[:insert_at] + link + html[insert_at:]
    response.set_data(html)
    response.headers['Content-Length'] = str(len(response.get_data()))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response
