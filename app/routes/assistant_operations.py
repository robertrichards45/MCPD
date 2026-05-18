import hmac
import json
from datetime import date, datetime, time

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    ROLE_ASSISTANT_OPERATIONS_OFFICER,
    ROLE_DESK_SGT,
    ROLE_WATCH_COMMANDER,
    ROLE_WEBSITE_CONTROLLER,
    AuditLog,
    OperationsTask,
    OperationsTaskComment,
    User,
    utcnow_naive,
)
from ..permissions import can_access_assistant_operations, can_create_assistant_operations_tasks

bp = Blueprint('assistant_operations', __name__, url_prefix='/assistant-operations')

TASK_CATEGORIES = [
    'Annual Training',
    'Monthly Training',
    'Inspection',
    'Fire Warden',
    'Range',
    'Medical',
    'Admin',
    'CLEOC',
    'DBIDS',
    'Livescan',
    'Safety',
    'Equipment',
    'Special Project',
    'Other',
]

PRIORITY_CHOICES = ['Low', 'Normal', 'High', 'Command Critical']
STATUS_CHOICES = ['Not Started', 'In Progress', 'Waiting on Personnel', 'Pending Review', 'Complete', 'Overdue', 'Cancelled']
WATCH_CHOICES = ['Day Shift', 'Night Shift', 'Alpha Watch', 'Bravo Watch', 'Charlie Watch', 'Delta Watch', 'All Watches', 'Admin']
RECURRENCE_CHOICES = ['One-Time', 'Monthly', 'Quarterly', 'Annual']
OPEN_STATUSES = {'Not Started', 'In Progress', 'Waiting on Personnel', 'Pending Review', 'Overdue'}
ASSIGNMENT_TARGET_CHOICES = [
    ('ALL_WATCH_COMMANDERS', 'All Watch Commanders'),
    ('SPECIFIC_WATCH_COMMANDERS', 'Certain Watch Commanders'),
    ('WATCH_COMMANDERS_AND_DESK_SGTS', 'Watch Commanders and Desk Sgts'),
    ('ALL_DESK_SGTS', 'All Desk Sgts'),
    ('SPECIFIC_DESK_SGTS', "Certain Desk Sgt's"),
    ('SPECIFIC_LEAD', 'One Specific Lead'),
]
COMPLETION_TARGET_CHOICES = [
    ('ALL_ACTIVE_PERSONNEL', 'Everyone Active'),
    ('ASSIGNED_WATCH', 'Everyone on Assigned Watch'),
    ('WATCH_COMMANDERS', 'Watch Commanders'),
    ('DESK_SGTS', 'Desk Sgts'),
    ('WATCH_COMMANDERS_AND_DESK_SGTS', 'Watch Commanders and Desk Sgts'),
    ('SPECIFIC_PERSONNEL', 'Certain People'),
    ('CUSTOM_COUNT', 'Custom Count Only'),
]


def _require_access():
    if not can_access_assistant_operations(current_user):
        abort(403)


def _require_task_creator():
    if not can_create_assistant_operations_tasks(current_user):
        abort(403)


def _require_csrf():
    expected = session.get('_csrf_token', '')
    supplied = request.form.get('_csrf_token') or request.headers.get('X-CSRFToken') or ''
    if not expected or not hmac.compare_digest(str(expected), str(supplied)):
        abort(400)


def _parse_date(value, fallback=None):
    raw = (value or '').strip()
    if not raw:
        return fallback
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.combine(datetime.strptime(raw, fmt).date(), time.min)
        except ValueError:
            continue
    return fallback


def _int_field(name, default=0):
    try:
        return max(0, int(request.form.get(name, default) or default))
    except (TypeError, ValueError):
        return default


def _selected_user_ids(field_name):
    selected = []
    for raw_id in request.form.getlist(field_name):
        try:
            selected.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    return selected


def _clamp_percent(value):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def _generate_task_id():
    today_key = utcnow_naive().strftime('%Y%m%d')
    existing_today = OperationsTask.query.filter(OperationsTask.task_id.like(f'OPS-{today_key}-%')).count()
    for offset in range(existing_today + 1, existing_today + 200):
        candidate = f'OPS-{today_key}-{offset:03d}'
        if not OperationsTask.query.filter_by(task_id=candidate).first():
            return candidate
    return f'OPS-{today_key}-{int(utcnow_naive().timestamp())}'


def _generate_comment_id():
    today_key = utcnow_naive().strftime('%Y%m%d')
    existing_today = OperationsTaskComment.query.filter(OperationsTaskComment.comment_id.like(f'COM-{today_key}-%')).count()
    for offset in range(existing_today + 1, existing_today + 300):
        candidate = f'COM-{today_key}-{offset:03d}'
        if not OperationsTaskComment.query.filter_by(comment_id=candidate).first():
            return candidate
    return f'COM-{today_key}-{int(utcnow_naive().timestamp())}'


def _refresh_task_calculations(task):
    today = date.today()
    total = max(0, int(task.total_personnel_required or 0))
    completed = max(0, min(total, int(task.personnel_completed or 0))) if total else max(0, int(task.personnel_completed or 0))
    task.total_personnel_required = total
    task.personnel_completed = completed
    task.personnel_pending = max(0, total - completed)

    if total:
        task.percent_complete = _clamp_percent(round((completed / total) * 100))
    else:
        task.percent_complete = _clamp_percent(task.percent_complete)

    if task.status == 'Complete':
        if total:
            task.personnel_completed = total
            task.personnel_pending = 0
        task.percent_complete = 100
        if not task.completion_date:
            task.completion_date = utcnow_naive()
    elif task.status == 'Cancelled':
        task.completion_date = None
    elif task.completion_date and task.status != 'Complete':
        task.completion_date = None

    due_day = task.due_date.date() if task.due_date else today
    task.days_until_due = (due_day - today).days
    task.is_overdue = task.days_until_due < 0 and task.status not in {'Complete', 'Cancelled'}
    if task.is_overdue and task.status not in {'Pending Review'}:
        task.status = 'Overdue'
    task.last_updated_date = utcnow_naive()


def _audit(action, details):
    db.session.add(AuditLog(actor_id=current_user.id, action=action, details=(details or '')[:2000]))


def _active_leads():
    command_roles = {
        ROLE_WEBSITE_CONTROLLER,
        ROLE_ASSISTANT_OPERATIONS_OFFICER,
        ROLE_WATCH_COMMANDER,
        ROLE_DESK_SGT,
    }
    users = (
        User.query.filter(User.active.is_(True))
        .order_by(User.last_name.asc(), User.first_name.asc(), User.username.asc())
        .all()
    )
    command_users = [user for user in users if user.has_any_role(*command_roles)]
    return command_users or users


def _active_personnel():
    return (
        User.query.filter(User.active.is_(True))
        .order_by(User.last_name.asc(), User.first_name.asc(), User.username.asc())
        .all()
    )


def _role_users(*role_keys):
    return [user for user in _active_personnel() if user.has_any_role(*role_keys)]


def _watch_users(watch_name):
    watch = (watch_name or '').strip().lower()
    if not watch or watch == 'all watches':
        return _active_personnel()
    users = []
    for user in _active_personnel():
        section = (user.section_unit or '').strip().lower()
        if section == watch or watch in section:
            users.append(user)
    return users


def _resolve_assignment_recipients(assignment_target):
    if assignment_target == 'ALL_WATCH_COMMANDERS':
        return _role_users(ROLE_WATCH_COMMANDER)
    if assignment_target == 'WATCH_COMMANDERS_AND_DESK_SGTS':
        return _role_users(ROLE_WATCH_COMMANDER, ROLE_DESK_SGT)
    if assignment_target == 'ALL_DESK_SGTS':
        return _role_users(ROLE_DESK_SGT)

    if assignment_target == 'SPECIFIC_WATCH_COMMANDERS':
        allowed = {user.id: user for user in _role_users(ROLE_WATCH_COMMANDER)}
        return [allowed[user_id] for user_id in _selected_user_ids('watch_commander_ids') if user_id in allowed]

    if assignment_target == 'SPECIFIC_DESK_SGTS':
        allowed = {user.id: user for user in _role_users(ROLE_DESK_SGT)}
        return [allowed[user_id] for user_id in _selected_user_ids('desk_sgt_ids') if user_id in allowed]

    lead_id = request.form.get('assigned_lead_id', type=int)
    lead = db.session.get(User, lead_id) if lead_id else None
    return [lead] if lead and lead.active else []


def _assignment_label(target):
    return dict(ASSIGNMENT_TARGET_CHOICES).get(target or 'SPECIFIC_LEAD', 'One Specific Lead')


def _resolve_completion_recipients(completion_target, assigned_watch):
    if completion_target == 'ALL_ACTIVE_PERSONNEL':
        return _active_personnel()
    if completion_target == 'ASSIGNED_WATCH':
        return _watch_users(assigned_watch)
    if completion_target == 'WATCH_COMMANDERS':
        return _role_users(ROLE_WATCH_COMMANDER)
    if completion_target == 'DESK_SGTS':
        return _role_users(ROLE_DESK_SGT)
    if completion_target == 'WATCH_COMMANDERS_AND_DESK_SGTS':
        return _role_users(ROLE_WATCH_COMMANDER, ROLE_DESK_SGT)
    if completion_target == 'SPECIFIC_PERSONNEL':
        allowed = {user.id: user for user in _active_personnel()}
        return [allowed[user_id] for user_id in _selected_user_ids('completion_user_ids') if user_id in allowed]
    return []


def _completion_label(target):
    return dict(COMPLETION_TARGET_CHOICES).get(target or 'CUSTOM_COUNT', 'Custom Count Only')


def _dashboard_metrics(tasks):
    total = len(tasks)
    open_count = sum(1 for task in tasks if task.status in OPEN_STATUSES)
    completed = sum(1 for task in tasks if task.status == 'Complete')
    overdue = sum(1 for task in tasks if task.is_overdue)
    due_soon = sum(1 for task in tasks if task.status in OPEN_STATUSES and 0 <= task.days_until_due <= 7)
    command_critical = sum(1 for task in tasks if task.priority == 'Command Critical' and task.status in OPEN_STATUSES)
    pending_review = sum(1 for task in tasks if task.status == 'Pending Review')
    personnel_required = sum(task.total_personnel_required or 0 for task in tasks)
    personnel_completed = sum(task.personnel_completed or 0 for task in tasks)
    if personnel_required:
        completion_rate = round((personnel_completed / personnel_required) * 100)
    else:
        completion_rate = round((completed / total) * 100) if total else 0
    return {
        'total': total,
        'open': open_count,
        'completed': completed,
        'overdue': overdue,
        'due_soon': due_soon,
        'command_critical': command_critical,
        'pending_review': pending_review,
        'completion_rate': completion_rate,
    }


def _watch_readiness(tasks):
    rows = []
    for watch in WATCH_CHOICES:
        watch_tasks = [task for task in tasks if task.assigned_watch == watch]
        if not watch_tasks:
            continue
        avg = round(sum(task.percent_complete or 0 for task in watch_tasks) / len(watch_tasks))
        rows.append({
            'watch': watch,
            'task_count': len(watch_tasks),
            'open_count': sum(1 for task in watch_tasks if task.status in OPEN_STATUSES),
            'overdue_count': sum(1 for task in watch_tasks if task.is_overdue),
            'average_complete': avg,
        })
    return rows


def _task_distribution(tasks, attr_name, choices):
    total = len(tasks) or 1
    rows = []
    for choice in choices:
        count = sum(1 for task in tasks if getattr(task, attr_name, None) == choice)
        if not count:
            continue
        rows.append({
            'label': choice,
            'count': count,
            'percent': round((count / total) * 100),
        })
    return rows


def _at_risk_tasks(tasks, limit=6):
    risky = [
        task for task in tasks
        if task.status in OPEN_STATUSES
        and (task.is_overdue or task.priority == 'Command Critical' or 0 <= task.days_until_due <= 7)
    ]
    risky.sort(key=lambda task: (
        0 if task.is_overdue else 1,
        0 if task.priority == 'Command Critical' else 1,
        task.days_until_due,
        -(task.percent_complete or 0),
    ))
    return risky[:limit]


@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    _require_access()
    status_filter = (request.args.get('status') or '').strip()
    watch_filter = (request.args.get('watch') or '').strip()
    query = OperationsTask.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if watch_filter:
        query = query.filter_by(assigned_watch=watch_filter)
    tasks = query.order_by(OperationsTask.is_overdue.desc(), OperationsTask.due_date.asc(), OperationsTask.priority.desc()).limit(250).all()
    all_tasks = OperationsTask.query.order_by(OperationsTask.due_date.asc()).all()
    for task in all_tasks:
        _refresh_task_calculations(task)
    db.session.commit()
    return render_template(
        'assistant_operations/dashboard.html',
        title='Assistant Operations Tracker',
        user=current_user,
        can_create_tasks=can_create_assistant_operations_tasks(current_user),
        tasks=tasks,
        metrics=_dashboard_metrics(all_tasks),
        watch_readiness=_watch_readiness(all_tasks),
        category_distribution=_task_distribution(all_tasks, 'task_category', TASK_CATEGORIES),
        priority_distribution=_task_distribution(all_tasks, 'priority', PRIORITY_CHOICES),
        at_risk_tasks=_at_risk_tasks(all_tasks),
        leads=_active_leads(),
        personnel=_active_personnel(),
        watch_commanders=_role_users(ROLE_WATCH_COMMANDER),
        desk_sgts=_role_users(ROLE_DESK_SGT),
        assignment_target_choices=ASSIGNMENT_TARGET_CHOICES,
        assignment_label=_assignment_label,
        completion_target_choices=COMPLETION_TARGET_CHOICES,
        completion_label=_completion_label,
        task_categories=TASK_CATEGORIES,
        priority_choices=PRIORITY_CHOICES,
        status_choices=STATUS_CHOICES,
        watch_choices=WATCH_CHOICES,
        recurrence_choices=RECURRENCE_CHOICES,
        selected_status=status_filter,
        selected_watch=watch_filter,
    )


@bp.post('/tasks/new')
@login_required
def create_task():
    _require_access()
    _require_task_creator()
    _require_csrf()
    title = (request.form.get('task_title') or '').strip()
    category = (request.form.get('task_category') or '').strip()
    assigned_watch = (request.form.get('assigned_watch') or '').strip()
    due_date = _parse_date(request.form.get('due_date'))
    priority = (request.form.get('priority') or 'Normal').strip()
    assignment_target = (request.form.get('assignment_target') or 'SPECIFIC_LEAD').strip()
    if assignment_target not in dict(ASSIGNMENT_TARGET_CHOICES):
        assignment_target = 'SPECIFIC_LEAD'
    completion_target = (request.form.get('completion_target') or 'CUSTOM_COUNT').strip()
    if completion_target not in dict(COMPLETION_TARGET_CHOICES):
        completion_target = 'CUSTOM_COUNT'
    if not title or category not in TASK_CATEGORIES or assigned_watch not in WATCH_CHOICES or not due_date or priority not in PRIORITY_CHOICES:
        flash('Title, category, assigned watch, due date, and priority are required.', 'error')
        return redirect(url_for('assistant_operations.dashboard'))

    recipients = _resolve_assignment_recipients(assignment_target)
    if assignment_target.startswith('SPECIFIC') and not recipients:
        flash('Choose at least one person for that assignment target.', 'error')
        return redirect(url_for('assistant_operations.dashboard'))
    lead = recipients[0] if recipients else None
    recipient_names = ', '.join(user.display_name for user in recipients)
    completion_users = _resolve_completion_recipients(completion_target, assigned_watch)
    if completion_target == 'SPECIFIC_PERSONNEL' and not completion_users:
        flash('Choose at least one person who must complete the task.', 'error')
        return redirect(url_for('assistant_operations.dashboard'))
    required_names = ', '.join(user.display_name for user in completion_users)
    total_required = len(completion_users) if completion_target != 'CUSTOM_COUNT' else _int_field('total_personnel_required')
    task = OperationsTask(
        task_id=_generate_task_id(),
        task_title=title,
        task_category=category,
        description=(request.form.get('description') or '').strip(),
        assigned_watch=assigned_watch,
        assignment_target=assignment_target,
        assigned_user_ids_json=json.dumps([user.id for user in recipients]),
        assigned_user_names=recipient_names,
        assigned_lead_id=lead.id if lead else None,
        assigned_lead_name=lead.display_name if lead else _assignment_label(assignment_target),
        completion_target=completion_target,
        required_user_ids_json=json.dumps([user.id for user in completion_users]),
        required_user_names=required_names,
        created_by_id=current_user.id,
        start_date=_parse_date(request.form.get('start_date'), fallback=None),
        due_date=due_date,
        priority=priority,
        status='Not Started',
        total_personnel_required=total_required,
        personnel_completed=_int_field('personnel_completed'),
        recurring=bool(request.form.get('recurring')),
        recurrence_type=(request.form.get('recurrence_type') or 'One-Time').strip(),
        attachment_link=(request.form.get('attachment_link') or '').strip(),
        commander_notes=(request.form.get('commander_notes') or '').strip(),
        last_updated_by_id=current_user.id,
    )
    _refresh_task_calculations(task)
    db.session.add(task)
    db.session.flush()
    _audit(
        'assistant_operations_task_created',
        f'task_id={task.task_id}|title={task.task_title}|watch={task.assigned_watch}|target={task.assignment_target}|recipients={recipient_names}|completion_target={task.completion_target}|required={required_names or task.total_personnel_required}',
    )
    db.session.commit()
    flash('Assistant Operations task created.', 'success')
    return redirect(url_for('assistant_operations.dashboard'))


@bp.post('/tasks/<int:task_pk>/update')
@login_required
def update_task(task_pk):
    _require_access()
    _require_csrf()
    task = OperationsTask.query.get_or_404(task_pk)
    status = (request.form.get('status') or task.status).strip()
    if status not in STATUS_CHOICES:
        status = task.status
    lead_id = request.form.get('assigned_lead_id', type=int)
    lead = db.session.get(User, lead_id) if lead_id else None
    task.status = status
    task.assigned_lead_id = lead.id if lead else task.assigned_lead_id
    task.assigned_lead_name = lead.display_name if lead else (request.form.get('assigned_lead_name') or task.assigned_lead_name or '').strip()
    task.personnel_completed = _int_field('personnel_completed', task.personnel_completed or 0)
    task.total_personnel_required = _int_field('total_personnel_required', task.total_personnel_required or 0)
    if not task.total_personnel_required:
        task.percent_complete = _clamp_percent(request.form.get('percent_complete') or task.percent_complete)
    task.commander_notes = (request.form.get('commander_notes') or '').strip()
    task.attachment_link = (request.form.get('attachment_link') or '').strip()
    task.last_updated_by_id = current_user.id
    _refresh_task_calculations(task)
    _audit('assistant_operations_task_updated', f'task_id={task.task_id}|status={task.status}|percent={task.percent_complete}')
    db.session.commit()
    flash('Task status updated.', 'success')
    return redirect(url_for('assistant_operations.dashboard', status=request.args.get('status', ''), watch=request.args.get('watch', '')))


@bp.post('/tasks/<int:task_pk>/comments')
@login_required
def add_comment(task_pk):
    _require_access()
    _require_csrf()
    task = OperationsTask.query.get_or_404(task_pk)
    comment_text = (request.form.get('comment_text') or '').strip()
    if not comment_text:
        flash('Comment text is required.', 'error')
        return redirect(url_for('assistant_operations.dashboard'))
    comment = OperationsTaskComment(
        comment_id=_generate_comment_id(),
        task_id=task.id,
        comment_by_id=current_user.id,
        watch=task.assigned_watch,
        comment_text=comment_text,
        status_at_comment=task.status,
        percent_at_comment=task.percent_complete or 0,
        follow_up_required=bool(request.form.get('follow_up_required')),
        follow_up_date=_parse_date(request.form.get('follow_up_date')),
    )
    db.session.add(comment)
    task.last_updated_by_id = current_user.id
    task.last_updated_date = utcnow_naive()
    _audit('assistant_operations_task_comment_added', f'task_id={task.task_id}|comment_id={comment.comment_id}')
    db.session.commit()
    flash('Comment added.', 'success')
    return redirect(url_for('assistant_operations.dashboard'))
