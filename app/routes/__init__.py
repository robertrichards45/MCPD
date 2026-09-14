import re

from flask import redirect, request
from flask_login import current_user

from . import auth, dashboard, forms, training, stats, annual_ai, admin, cleo_api, reports, reconstruction, officers, ops_modules, legal, orders, reference, announcements, mobile
from . import credit_simulator, sentinel

# Nest add-on tools under blueprints already registered by the app factory so
# the large central factory does not need to be modified.
admin.bp.register_blueprint(credit_simulator.bp)
reports.bp.register_blueprint(sentinel.bp)


@admin.bp.before_app_request
def _retire_requested_portal_modules():
    """Retire old user-facing modules while preserving stored records/data."""
    if not getattr(current_user, 'is_authenticated', False):
        return None

    path = request.path.rstrip('/') or '/'
    if path == '/reports/new':
        return redirect('/tools/narrative')
    if path == '/cleo/reports':
        return redirect('/reports')
    if path == '/watch-commander/dashboard':
        return redirect('/dashboard')
    if path.startswith('/assistant-operations'):
        return redirect('/dashboard')
    if path.startswith('/notifications'):
        return redirect('/dashboard')
    if path.startswith('/bodycam'):
        return redirect('/tools/narrative')
    return None


def _remove_anchor_by_text(html, label):
    pattern = re.compile(r'<a\b[^>]*>.*?' + re.escape(label) + r'.*?</a>', re.I | re.S)
    return pattern.sub('', html)


def _remove_details_group(html, label):
    pattern = re.compile(
        r'<details\b[^>]*>\s*<summary\b[^>]*>.*?' + re.escape(label) + r'.*?</summary>.*?</details>',
        re.I | re.S,
    )
    return pattern.sub('', html)


@admin.bp.after_app_request
def _portal_navigation_and_retirement_layer(response):
    """Keep the portal simple and expose the integrated Sentinel tools."""
    if not getattr(current_user, 'is_authenticated', False):
        return response
    if response.direct_passthrough or response.status_code != 200 or response.mimetype != 'text/html':
        return response

    try:
        html = response.get_data(as_text=True)
    except (RuntimeError, UnicodeDecodeError):
        return response

    html = _remove_details_group(html, 'Bodycam')
    html = _remove_details_group(html, 'Watch Commander')
    for label in (
        'Start New Report',
        'Start Report',
        'CLEOC Reports',
        'Messages',
        'Assistant Ops',
        'Watch Dashboard',
        'WC Dashboard',
        'Body Cam Mode',
        'Bodycam Footage',
        'Command Due-Out Tracker',
    ):
        html = _remove_anchor_by_text(html, label)

    if '</head>' in html and 'sentinel-retired-ui' not in html:
        html = html.replace(
            '</head>',
            '<style id="sentinel-retired-ui">'
            '.mcpd-map-card,.mcpd-map-fullscreen-overlay,.mcpd-mobile-map-panel{display:none!important}'
            '</style></head>',
            1,
        )
    html = html.replace('MCLB Albany — Installation Map', '')
    html = html.replace('MCLB Albany &mdash; Installation Map', '')
    html = html.replace('Watch Commander dashboard, BOLO board, shift management,', 'Incident command, BOLO board, shift management,')

    if 'mcpd-command-sidebar' in html and '/sentinel/report-inspector' not in html:
        narrative_link = '<a href="/tools/narrative"'
        idx = html.find(narrative_link)
        if idx >= 0:
            end = html.find('</a>', idx)
            if end >= 0:
                end += 4
                html = html[:end] + '<a href="/sentinel/report-inspector">Sentinel Report Inspector</a>' + html[end:]
        training_text = '>Training</a>'
        idx = html.find(training_text)
        if idx >= 0:
            end = idx + len(training_text)
            html = html[:end] + '<a href="/sentinel/fto-instructor">AI FTO Instructor</a>' + html[end:]

    if request.path.rstrip('/') == '/forms' and 'sentinel-forms-guide' not in html:
        marker = '<h2 class="mb-1">Forms Library</h2>'
        if marker in html:
            guide = (
                '<div id="sentinel-forms-guide" class="alert alert-info mt-3">'
                '<strong>Simple paperwork workflow:</strong> choose the incident/call type, complete required forms first, '
                'review conditional forms, preview the packet, then save or submit. Use the Paperwork Navigator when you are unsure.'
                '</div>'
            )
            html = html.replace(marker, marker + guide, 1)

    if 'href="/private/credit-simulator/"' not in html and 'mcpd-command-sidebar' in html:
        marker = '<nav aria-label="Main navigation">'
        if marker in html:
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
