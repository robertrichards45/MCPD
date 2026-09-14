import re

from flask import redirect, request
from flask_login import current_user

from . import auth, dashboard, forms, training, stats, annual_ai, admin, cleo_api, reports, reconstruction, officers, ops_modules, legal, orders, reference, announcements, mobile
from . import credit_simulator, sentinel

# Nest add-on tools under blueprints already registered by the app factory so
# the large central factory does not need to be modified.
admin.bp.register_blueprint(credit_simulator.bp)
reports.bp.register_blueprint(sentinel.bp)

# Retired user-facing tools stay out of the dashboard/navigation while their
# underlying records remain intact for compatibility and historical access.
_RETIRED_CARD_IDS = {
    'start_report',
    'bodycam_mode',
    'bodycam_footage',
    'assistant_operations_tracker',
    'watch_commander_hub',
    'incident_command',
}
_RETIRED_ENDPOINTS = {
    'reports.new_report',
    'bodycam.new_recording',
    'bodycam.library',
    'assistant_operations.dashboard',
    'watch_commander.dashboard',
    'watch_commander.sign_on',
    'incident_command.dashboard',
    'cleo_api.cleo_reports_page',
    'notifications.inbox',
}

_original_dashboard_card_catalog = dashboard._dashboard_card_catalog
_original_dashboard_panel_catalog = dashboard._dashboard_panel_catalog
_original_dashboard_readiness_items = dashboard._dashboard_readiness_items
_original_dashboard_queue_items = dashboard._dashboard_queue_items
_original_dashboard_live_ops = dashboard._dashboard_live_ops


def _sentinel_dashboard_card_catalog():
    """Return a smaller role-aware card set with Sentinel embedded in workflow."""
    cards = [card for card in _original_dashboard_card_catalog() if card.get('id') not in _RETIRED_CARD_IDS]
    by_id = {card.get('id'): card for card in cards}

    by_id['sentinel_report_inspector'] = {
        'id': 'sentinel_report_inspector',
        'label': 'Report Quality Review',
        'description': 'Sentinel review for completeness, chronology, articulation, and missing facts',
        'icon': 'report',
        'endpoint': 'reports.sentinel.report_inspector',
    }
    by_id['fto_center'] = {
        'id': 'fto_center',
        'label': 'FTO Center',
        'description': 'Field training scenarios, evaluation coaching, and trainee development',
        'icon': 'training',
        'endpoint': 'reports.sentinel.fto_center',
    }

    officer_order = [
        'narrative_creator',
        'sentinel_report_inspector',
        'forms_library',
        'accident_tools',
        'law_lookup',
        'training',
        'fto_center',
        'orders_memos',
        'saved_work',
        'five_w_builder',
        'mobile_field_view',
    ]
    supervisor_order = officer_order + [
        'approve_assign_officers',
        'stats_approvals',
        'readiness_tracker',
    ]
    order = supervisor_order if current_user.can_manage_team() else officer_order

    # The original catalog already includes Site Builder when the user has
    # builder access; preserve it without duplicating permission logic here.
    if 'site_builder' in by_id:
        order.append('site_builder')

    return [by_id[item_id] for item_id in order if item_id in by_id]


def _sentinel_dashboard_panel_catalog(snapshot):
    """Replace legacy command panels with role-specific work queues."""
    panels = _original_dashboard_panel_catalog(snapshot)
    cleaned = []
    for panel in panels:
        if panel.get('id') == 'command_activity':
            continue
        item = dict(panel)
        item['items'] = [
            row for row in panel.get('items', [])
            if row.get('endpoint') not in _RETIRED_ENDPOINTS
            and row.get('label') not in {'Start New Report', 'Body Cam Mode', 'Bodycam Footage', 'Incident Command'}
        ]
        if item.get('id') == 'recent_reports':
            item['title'] = 'Reporting Workspace'
            item['items'] = [
                {'label': 'Reports Center', 'detail': 'Open your reports, returned corrections, and submitted packets', 'endpoint': 'reports.list_reports'},
                {'label': 'Narrative Creator', 'detail': 'Build the narrative and review missing facts as you write', 'endpoint': 'bodycam.narrative_tool'},
                {'label': 'Report Quality Review', 'detail': 'Run Sentinel without inventing or assuming missing facts', 'endpoint': 'reports.sentinel.report_inspector'},
                {'label': 'Accident Tools', 'detail': 'Guided crash documentation and diagram workflow', 'endpoint': 'reports.accidents'},
            ]
        elif item.get('id') == 'training_rosters':
            item['title'] = 'Training & Development'
            item['items'] = [
                {'label': 'Training Center', 'detail': 'Assigned training, rosters, and acknowledgements', 'endpoint': 'training.training_menu'},
                {'label': 'FTO Center', 'detail': 'Scenario Lab, evaluation coaching, and trainee development', 'endpoint': 'reports.sentinel.fto_center'},
                {'label': 'Qualifications', 'detail': 'Qualification and readiness tracking', 'endpoint': 'qual_tracker.tracker_personal'},
            ]
            if current_user.can_manage_team():
                item['items'].append({'label': 'Team Readiness', 'detail': 'Review qualification status across the team', 'endpoint': 'qual_tracker.tracker_readiness'})
        if item.get('items'):
            if item.get('view_all_endpoint') in _RETIRED_ENDPOINTS:
                item['view_all_endpoint'] = 'dashboard.dashboard'
            cleaned.append(item)

    action_items = []
    for row in snapshot.get('queue_items', []):
        if row.get('endpoint') in _RETIRED_ENDPOINTS:
            continue
        action_items.append({
            'label': row.get('label', 'Action item'),
            'detail': row.get('detail', 'Open item'),
            'endpoint': row.get('endpoint', 'dashboard.dashboard'),
        })
    if current_user.can_manage_team():
        action_items.extend([
            {'label': 'Reports Awaiting Review', 'detail': 'Review submitted reports and correction status', 'endpoint': 'reports.list_reports'},
            {'label': 'Readiness Issues', 'detail': 'Review qualifications, expirations, and training attention items', 'endpoint': 'qual_tracker.tracker_readiness'},
            {'label': 'Personnel', 'detail': 'Accounts, assignments, and role management', 'endpoint': 'auth.manage_users'},
        ])
    else:
        action_items.extend([
            {'label': 'Returned Reports', 'detail': 'Check reports returned for correction', 'endpoint': 'reports.list_reports'},
            {'label': 'FTO / Training', 'detail': 'Open assigned development and scenario work', 'endpoint': 'reports.sentinel.fto_center'},
        ])
    cleaned.insert(0, {
        'id': 'needs_attention',
        'title': 'Needs My Attention',
        'view_all_endpoint': 'dashboard.dashboard',
        'items': action_items[:7],
    })
    return cleaned


def _sentinel_dashboard_readiness_items(*args, **kwargs):
    items = _original_dashboard_readiness_items(*args, **kwargs)
    return [
        item for item in items
        if item.get('endpoint') not in _RETIRED_ENDPOINTS
        and item.get('label') not in {'Watch Command', 'Command Tasking'}
    ]


def _sentinel_dashboard_queue_items(*args, **kwargs):
    items = _original_dashboard_queue_items(*args, **kwargs)
    cleaned = [item for item in items if item.get('endpoint') not in _RETIRED_ENDPOINTS and item.get('label') != 'Task Tracker']
    if current_user.can_manage_team():
        cleaned.extend([
            {
                'label': 'Reports Awaiting Review',
                'value': 'Review',
                'detail': 'Submitted reports and correction workflow',
                'endpoint': 'reports.list_reports',
            },
            {
                'label': 'Readiness',
                'value': 'Team',
                'detail': 'Training and qualification attention items',
                'endpoint': 'qual_tracker.tracker_readiness',
            },
        ])
    return cleaned


def _sentinel_dashboard_live_ops(*args, **kwargs):
    payload = _original_dashboard_live_ops(*args, **kwargs)
    payload['preplan_layers'] = [
        item for item in payload.get('preplan_layers', [])
        if item.get('label') not in {'Installation Map', 'Incident / BOLO Layer'}
        and item.get('endpoint') not in _RETIRED_ENDPOINTS
    ]
    for item in payload.get('feed', []):
        if item.get('endpoint') in _RETIRED_ENDPOINTS:
            item['endpoint'] = 'reports.list_reports'
    return payload


dashboard._dashboard_card_catalog = _sentinel_dashboard_card_catalog
dashboard._dashboard_panel_catalog = _sentinel_dashboard_panel_catalog
dashboard._dashboard_readiness_items = _sentinel_dashboard_readiness_items
dashboard._dashboard_queue_items = _sentinel_dashboard_queue_items
dashboard._dashboard_live_ops = _sentinel_dashboard_live_ops


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
    if path in {'/watch-commander/sign-on', '/watch-commander/sign_on'}:
        return redirect('/dashboard')
    if path.startswith('/incident-command'):
        return redirect('/dashboard')
    if path.startswith('/assistant-operations'):
        return redirect('/dashboard')
    if path in {'/notifications', '/notifications/inbox'}:
        return redirect('/dashboard')
    if path.startswith(('/bodycam', '/mobile/bodycam')):
        return redirect('/tools/narrative')
    return None


def _remove_anchor_by_text(html, label):
    # Do not allow the match to cross an </a>; this keeps adjacent navigation
    # items safe when the requested label is absent from the first anchor.
    pattern = re.compile(
        r'<a\b[^>]*>(?:(?!</a>).)*?' + re.escape(label) + r'(?:(?!</a>).)*?</a>',
        re.I | re.S,
    )
    return pattern.sub('', html)


def _remove_anchor_by_class(html, class_name):
    pattern = re.compile(
        r'<a\b(?=[^>]*\bclass=["\'][^"\']*\b' + re.escape(class_name) + r'\b[^"\']*["\'])[^>]*>.*?</a>',
        re.I | re.S,
    )
    return pattern.sub('', html)


def _remove_details_group(html, label):
    pattern = re.compile(
        r'<details\b[^>]*>\s*<summary\b[^>]*>(?:(?!</summary>).)*?' + re.escape(label) + r'(?:(?!</summary>).)*?</summary>.*?</details>',
        re.I | re.S,
    )
    return pattern.sub('', html)


@admin.bp.after_app_request
def _portal_navigation_and_retirement_layer(response):
    """Keep the portal simple and expose integrated Sentinel workflows."""
    if response.direct_passthrough or response.status_code != 200 or response.mimetype != 'text/html':
        return response

    try:
        html = response.get_data(as_text=True)
    except (RuntimeError, UnicodeDecodeError):
        return response

    # Public-facing copy should not advertise retired internal tools.
    html = html.replace(
        'Watch Commander dashboard, BOLO board, shift management,',
        'BOLO board, training, reporting,',
    )
    html = html.replace(
        'Incident command, BOLO board, shift management,',
        'BOLO board, training, reporting,',
    )

    if not getattr(current_user, 'is_authenticated', False):
        response.set_data(html)
        response.headers['Content-Length'] = str(len(response.get_data()))
        return response

    html = _remove_details_group(html, 'Bodycam')
    html = _remove_details_group(html, 'Watch Commander')
    html = _remove_anchor_by_class(html, 'nav-shift-pill')
    for label in (
        'Start New Report',
        'Start Report',
        'CLEOC Reports',
        'Messages',
        'Assistant Ops',
        'Watch Dashboard',
        'WC Dashboard',
        'Watch Commander Hub',
        'Watch Command',
        'Command Dashboard',
        'Body Cam Mode',
        'Bodycam Footage',
        'Command Due-Out Tracker',
        'Installation Map',
        'Incident Command',
        'Shift Check-In',
        'Check In',
        'End Shift',
    ):
        html = _remove_anchor_by_text(html, label)

    if '</head>' in html and 'sentinel-retired-ui' not in html:
        html = html.replace(
            '</head>',
            '<style id="sentinel-retired-ui">'
            '.mcpd-map-card,.mcpd-map-fullscreen-overlay,.mcpd-mobile-map-panel,.nav-shift-pill{display:none!important}'
            '</style></head>',
            1,
        )
    html = html.replace('MCLB Albany — Installation Map', '')
    html = html.replace('MCLB Albany &mdash; Installation Map', '')

    if 'mcpd-command-sidebar' in html and '/sentinel/report-inspector' not in html:
        narrative_link = '<a href="/tools/narrative"'
        idx = html.find(narrative_link)
        if idx >= 0:
            end = html.find('</a>', idx)
            if end >= 0:
                end += 4
                html = html[:end] + '<a href="/sentinel/report-inspector">Report Quality Review</a>' + html[end:]
        training_text = '>Training</a>'
        idx = html.find(training_text)
        if idx >= 0:
            end = idx + len(training_text)
            html = html[:end] + '<a href="/sentinel/fto-center">FTO Center</a>' + html[end:]

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