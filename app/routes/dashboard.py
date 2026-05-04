from flask import Blueprint, render_template, redirect, url_for, make_response, request
from flask_login import login_required, current_user

from ..models import (
    Announcement,
    CleoReport,
    OrderDocument,
    Report,
    ROLE_WATCH_COMMANDER,
    SavedForm,
    TrainingRoster,
)

bp = Blueprint('dashboard', __name__)


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


def _dashboard_snapshot():
    visible_announcements = _visible_announcements_query()
    saved_forms_count = SavedForm.query.filter_by(officer_user_id=current_user.id).count()
    report_count = _production_report_query().filter_by(owner_id=current_user.id).count()
    cleo_report_count = CleoReport.query.filter_by(user_id=current_user.id).count()
    orders_count = OrderDocument.query.filter(OrderDocument.is_active.is_(True)).count()
    training_count = TrainingRoster.query.filter_by(status='ACTIVE').count()
    notice_count = visible_announcements.count()

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
        'announcements': (
            visible_announcements
            .order_by(Announcement.created_at.desc(), Announcement.id.desc())
            .limit(3)
            .all()
        ),
    }

@bp.route('/dashboard')
@login_required
def dashboard():
    if _request_prefers_mobile_home():
        return redirect(url_for('mobile.home'))
    snapshot = _dashboard_snapshot()
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
        )
    )

@bp.route('/cleo')
@login_required
def cleo():
    return redirect(url_for('reports.list_reports'))


@bp.route('/diagrams')
@login_required
def diagrams():
    # Backwards-compatible alias: "Diagramming" was replaced by Reconstruction.
    return redirect(url_for('reconstruction.case_list'))
