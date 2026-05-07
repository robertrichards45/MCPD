import json
import logging

from flask import Blueprint, flash, render_template, redirect, url_for, make_response, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (
    Announcement,
    CleoReport,
    OrderDocument,
    Report,
    ROLE_WATCH_COMMANDER,
    SavedForm,
    TrainingRoster,
)
from ..permissions import can_access_builder_mode

bp = Blueprint('dashboard', __name__)
_log = logging.getLogger(__name__)

DEFAULT_DASHBOARD_CARD_IDS = [
    'law_lookup',
    'start_report',
    'forms_library',
    'orders_memos',
    'training',
    'saved_work',
]

DEFAULT_DASHBOARD_PANEL_IDS = ['recent_reports', 'training_rosters', 'saved_work']


def _is_test_report_title(title: str) -> bool:
    return str(title or '').strip().lower().startswith(('stress report', 'test report ', 'mock stress report'))


def _production_report_query():
    return Report.query.filter(
        ~Report.title.ilike('Stress Report%'),
        ~Report.title.ilike('Test Report %'),
        ~Report.title.ilike('Mock Stress Report%'),
    )


def _request_prefers_mobile_home() -> bool:
    user_agent = str(getattr(request, 'user_agent', '') or '')
    blob = ' '.join(
        [
            user_agent,
            str(request.headers.get('User-Agent', '') or ''),
            str(request.headers.get('Sec-CH-UA-Mobile', '') or ''),
        ]
    ).lower()
    return any(token in blob for token in ('iphone', 'android', 'mobile', 'ipad'))


def _no_store_response(rendered):
    response = make_response(rendered)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _visible_announcements_query():
    scopes = {'ALL', current_user.normalized_role}
    if current_user.has_role(ROLE_WATCH_COMMANDER):
        scopes.add(ROLE_WATCH_COMMANDER)
    return Announcement.query.filter(
        Announcement.is_active.is_(True),
        Announcement.scope.in_(sorted(scopes)),
    )


def _safe_count(label, query):
    try:
        return query.count()
    except Exception as exc:
        db.session.rollback()
        _log.warning('Dashboard count failed for %s: %s', label, exc.__class__.__name__)
        return 0


def _safe_recent_announcements(query):
    try:
        return query.order_by(Announcement.created_at.desc(), Announcement.id.desc()).limit(3).all()
    except Exception as exc:
        db.session.rollback()
        _log.warning('Dashboard announcements failed: %s', exc.__class__.__name__)
        return []


def _dashboard_snapshot():
    visible_announcements = _visible_announcements_query()
    saved_forms_count = _safe_count('saved_forms', SavedForm.query.filter_by(officer_user_id=current_user.id))
    report_count = _safe_count('reports', _production_report_query().filter_by(owner_id=current_user.id))
    cleo_report_count = _safe_count('cleo_reports', CleoReport.query.filter_by(user_id=current_user.id))
    orders_count = _safe_count('orders', OrderDocument.query.filter(OrderDocument.is_active.is_(True)))
    training_count = _safe_count('training', TrainingRoster.query.filter_by(status='ACTIVE'))
    notice_count = _safe_count('announcements', visible_announcements)

    metrics = [
        {
            'label': 'Saved Forms',
            'value': saved_forms_count,
            'detail': 'Resume form drafts without digging through menus.',
        },
        {
            'label': 'Reports',
            'value': report_count,
            'detail': 'Case writeups and report shells tied to your account.',
        },
        {
            'label': 'Mock Report Drafts',
            'value': cleo_report_count,
            'detail': 'Mock report packets and review work still in motion.',
        },
        {
            'label': 'Live Notices',
            'value': notice_count,
            'detail': 'Command updates visible to your current scope.',
        },
    ]

    return {
        'metrics': metrics,
        'saved_forms_count': saved_forms_count,
        'report_count': report_count,
        'cleo_report_count': cleo_report_count,
        'orders_count': orders_count,
        'training_count': training_count,
        'notice_count': notice_count,
        'announcements': _safe_recent_announcements(visible_announcements),
    }


def _dashboard_card_catalog():
    cards = [
        {
            'id': 'law_lookup',
            'label': 'Law Lookup',
            'description': 'Search laws, UCMJ, and base orders',
            'icon': 'law',
            'endpoint': 'legal.legal_home',
        },
        {
            'id': 'start_report',
            'label': 'Start New Report',
            'description': 'Create an incident report or blotter',
            'icon': 'report',
            'endpoint': 'reports.new_report',
        },
        {
            'id': 'forms_library',
            'label': 'Forms Library',
            'description': 'Fill out, save, and manage forms',
            'icon': 'forms',
            'endpoint': 'forms.list_forms',
        },
        {
            'id': 'orders_memos',
            'label': 'Orders & Memos',
            'description': 'Search orders, memos, and references',
            'icon': 'orders',
            'endpoint': 'orders.reference_search',
        },
        {
            'id': 'training',
            'label': 'Training',
            'description': 'Rosters, sign-in, and qualifications',
            'icon': 'training',
            'endpoint': 'training.training_menu',
        },
        {
            'id': 'saved_work',
            'label': 'Saved Work',
            'description': 'Saved forms, drafts, and packets',
            'icon': 'saved',
            'endpoint': 'forms.saved_forms',
        },
        {
            'id': 'accident_tools',
            'label': 'Accident Tools',
            'description': 'Officer diagrams and investigator reconstruction',
            'icon': 'report',
            'endpoint': 'reports.accidents',
        },
        {
            'id': 'bodycam_mode',
            'label': 'Body Cam Mode',
            'description': 'Record video with transcript support',
            'icon': 'report',
            'endpoint': 'bodycam.new_recording',
        },
        {
            'id': 'bodycam_footage',
            'label': 'Bodycam Footage',
            'description': 'Review saved recordings and transcripts',
            'icon': 'saved',
            'endpoint': 'bodycam.library',
        },
        {
            'id': 'narrative_creator',
            'label': 'Narrative Creator',
            'description': 'Turn report facts into a draft narrative',
            'icon': 'forms',
            'endpoint': 'bodycam.narrative_tool',
        },
        {
            'id': 'five_w_builder',
            'label': '5W Builder',
            'description': 'Paste one notes block and extract the 5Ws',
            'icon': 'forms',
            'endpoint': 'bodycam.five_w_tool',
        },
        {
            'id': 'mobile_field_view',
            'label': 'Mobile Field View',
            'description': 'Open the phone/tablet field dashboard',
            'icon': 'training',
            'endpoint': 'mobile.home',
        },
    ]
    if can_access_builder_mode(current_user):
        cards.append({
            'id': 'site_builder',
            'label': 'Site Builder',
            'description': 'Owner-approved change request console',
            'icon': 'orders',
            'endpoint': 'admin.site_builder',
        })
    if current_user.can_manage_team():
        cards.extend([
            {
                'id': 'watch_commander_hub',
                'label': 'Watch Commander Hub',
                'description': 'Shift, reports, approvals, officers, and briefing',
                'icon': 'orders',
                'endpoint': 'watch_commander.dashboard',
            },
            {
                'id': 'approve_assign_officers',
                'label': 'Approve / Assign Officers',
                'description': 'Activate accounts, edit roles, and assign watch',
                'icon': 'training',
                'endpoint': 'auth.manage_users',
            },
            {
                'id': 'stats_approvals',
                'label': 'Stats Approvals',
                'description': 'Approve officer stats and performance entries',
                'icon': 'report',
                'endpoint': 'performance.pending',
            },
            {
                'id': 'readiness_tracker',
                'label': 'Readiness Tracker',
                'description': 'Monitor team qualifications and expirations',
                'icon': 'training',
                'endpoint': 'qual_tracker.tracker_readiness',
            },
        ])
    return cards


def _dashboard_panel_catalog(snapshot):
    return [
        {
            'id': 'recent_reports',
            'title': 'Recent Reports',
            'view_all_endpoint': 'reports.list_reports',
            'items': [
                {'label': 'Reports Center', 'detail': snapshot['metrics'][0]['detail'] if snapshot['metrics'] else 'Open reports and packets', 'endpoint': 'reports.list_reports'},
                {'label': 'Bodycam Footage', 'detail': 'Recordings and transcripts', 'endpoint': 'bodycam.library'},
                {'label': 'Narrative Creator', 'detail': 'Standalone report writing tool', 'endpoint': 'bodycam.narrative_tool'},
                {'label': '5W Builder', 'detail': 'Who, what, when, where, and why summary', 'endpoint': 'bodycam.five_w_tool'},
                {'label': 'Accident Reconstruction', 'detail': 'Scene diagrams and crash reports', 'endpoint': 'reports.accident_reconstruction_list'},
            ],
        },
        {
            'id': 'training_rosters',
            'title': 'Training Rosters',
            'view_all_endpoint': 'training.training_menu',
            'items': [
                {'label': 'Training Center', 'detail': 'Assigned rosters and sign-offs', 'endpoint': 'training.training_menu'},
                {'label': 'Qualifications', 'detail': 'Personal qualification tracker', 'endpoint': 'qual_tracker.tracker_personal'},
                {'label': 'Officer Stats', 'detail': 'Performance and elements', 'endpoint': 'performance.my_stats'},
            ],
        },
        {
            'id': 'saved_work',
            'title': 'Saved Work',
            'view_all_endpoint': 'forms.saved_forms',
            'items': [
                {'label': 'Saved Forms', 'detail': f"{snapshot['saved_forms_count']} item{'' if snapshot['saved_forms_count'] == 1 else 's'}", 'endpoint': 'forms.saved_forms'},
                {'label': 'My Profile', 'detail': 'Contact info and emergency contacts', 'endpoint': 'officers.profile'},
                {'label': 'Command Notices', 'detail': 'Assigned notices and updates', 'endpoint': 'announcements.board'},
            ],
        },
        {
            'id': 'command_activity',
            'title': 'Command Activity',
            'view_all_endpoint': 'watch_commander.dashboard',
            'supervisor_only': True,
            'items': [
                {'label': 'Watch Commander Hub', 'detail': 'Shift supervision dashboard', 'endpoint': 'watch_commander.dashboard'},
                {'label': 'Approvals Center', 'detail': 'Review pending supervisor actions', 'endpoint': 'watch_commander.approvals'},
                {'label': 'Shift Management', 'detail': 'Create shifts and assign officers', 'endpoint': 'watch_commander.shift'},
            ],
        },
    ]


def _load_dashboard_preferences():
    raw = getattr(current_user, 'dashboard_preferences_json', None)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _ordered_visible_items(catalog, selected_ids, default_ids):
    allowed = {item['id']: item for item in catalog}
    ordered_ids = [item_id for item_id in selected_ids if item_id in allowed] if selected_ids else []
    if not ordered_ids:
        ordered_ids = [item_id for item_id in default_ids if item_id in allowed]
    return [allowed[item_id] for item_id in ordered_ids if item_id in allowed]


def _dashboard_preferences_context(snapshot=None):
    snapshot = snapshot or _dashboard_snapshot()
    prefs = _load_dashboard_preferences()
    card_catalog = _dashboard_card_catalog()
    panel_catalog = [
        panel for panel in _dashboard_panel_catalog(snapshot)
        if not panel.get('supervisor_only') or current_user.can_manage_team()
    ]
    selected_cards = prefs.get('cards') if isinstance(prefs.get('cards'), list) else []
    selected_panels = prefs.get('panels') if isinstance(prefs.get('panels'), list) else []
    return {
        'dashboard_card_catalog': card_catalog,
        'dashboard_panel_catalog': panel_catalog,
        'dashboard_cards': _ordered_visible_items(card_catalog, selected_cards, DEFAULT_DASHBOARD_CARD_IDS),
        'dashboard_panels': _ordered_visible_items(panel_catalog, selected_panels, DEFAULT_DASHBOARD_PANEL_IDS),
        'dashboard_selected_card_ids': selected_cards or [card['id'] for card in _ordered_visible_items(card_catalog, [], DEFAULT_DASHBOARD_CARD_IDS)],
        'dashboard_selected_panel_ids': selected_panels or [panel['id'] for panel in _ordered_visible_items(panel_catalog, [], DEFAULT_DASHBOARD_PANEL_IDS)],
    }


@bp.route('/dashboard')
@login_required
def dashboard():
    if _request_prefers_mobile_home():
        return redirect(url_for('mobile.home'))
    snapshot = _dashboard_snapshot()
    preferences_context = _dashboard_preferences_context(snapshot)
    return _no_store_response(
        render_template(
            'dashboard.html',
            user=current_user,
            dashboard_metrics=snapshot['metrics'],
            dashboard_saved_forms_count=snapshot['saved_forms_count'],
            dashboard_report_count=snapshot['report_count'],
            dashboard_cleo_report_count=snapshot['cleo_report_count'],
            dashboard_orders_count=snapshot['orders_count'],
            dashboard_training_count=snapshot['training_count'],
            dashboard_notice_count=snapshot['notice_count'],
            dashboard_announcements=snapshot['announcements'],
            **preferences_context,
        )
    )


@bp.route('/dashboard/customize', methods=['GET', 'POST'])
@login_required
def customize_dashboard():
    snapshot = _dashboard_snapshot()
    context = _dashboard_preferences_context(snapshot)
    if request.method == 'POST':
        action = (request.form.get('action') or 'save').strip().lower()
        if action == 'reset':
            current_user.dashboard_preferences_json = None
            db.session.commit()
            flash('Dashboard reset to the MCPD default layout.', 'success')
            return redirect(url_for('dashboard.dashboard'))

        allowed_card_ids = {card['id'] for card in context['dashboard_card_catalog']}
        allowed_panel_ids = {panel['id'] for panel in context['dashboard_panel_catalog']}
        selected_cards = [item for item in request.form.getlist('cards') if item in allowed_card_ids]
        selected_panels = [item for item in request.form.getlist('panels') if item in allowed_panel_ids]
        if not selected_cards:
            selected_cards = [item for item in DEFAULT_DASHBOARD_CARD_IDS if item in allowed_card_ids]
        if not selected_panels:
            selected_panels = [item for item in DEFAULT_DASHBOARD_PANEL_IDS if item in allowed_panel_ids]
        current_user.dashboard_preferences_json = json.dumps(
            {'cards': selected_cards, 'panels': selected_panels},
            sort_keys=True,
        )
        db.session.commit()
        flash('Dashboard layout saved.', 'success')
        return redirect(url_for('dashboard.dashboard'))

    return _no_store_response(render_template('dashboard_customize.html', user=current_user, **context))

@bp.route('/cleo')
@login_required
def cleo():
    return redirect(url_for('reports.list_reports'))


@bp.route('/diagrams')
@login_required
def diagrams():
    # Backwards-compatible alias: "Diagramming" was replaced by Reconstruction.
    return redirect(url_for('reconstruction.case_list'))
