from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Announcement, ROLE_WATCH_COMMANDER


bp = Blueprint('announcements', __name__)


def _visible_announcements():
    query = Announcement.query.filter(Announcement.is_active.is_(True))
    scopes = {'ALL'}
    if current_user.has_role(ROLE_WATCH_COMMANDER):
        scopes.add('WATCH_COMMANDER')
    scopes.add(current_user.normalized_role)
    return (
        query.filter(Announcement.scope.in_(sorted(scopes)))
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
        .all()
    )


@bp.route('/announcements', methods=['GET', 'POST'])
@login_required
def board():
    if request.method == 'POST':
        if not current_user.can_manage_team():
            abort(403)

        title = (request.form.get('title') or '').strip()
        message = (request.form.get('message') or '').strip()
        scope = (request.form.get('scope') or 'ALL').strip().upper()
        if scope not in {'ALL', 'WATCH_COMMANDER', 'PATROL_OFFICER', 'DESK_SGT', 'FIELD_TRAINING_OFFICER'}:
            scope = 'ALL'

        if not title or not message:
            flash('Title and message are required.', 'error')
            return redirect(url_for('announcements.board'))

        item = Announcement(
            title=title,
            message=message,
            scope=scope,
            created_by=current_user.id,
        )
        db.session.add(item)
        db.session.commit()
        flash('Announcement posted.', 'success')
        return redirect(url_for('announcements.board'))

    scope_filter = (request.args.get('scope') or '').strip().upper()
    announcements = _visible_announcements()
    if scope_filter:
        announcements = [item for item in announcements if item.scope == scope_filter]

    return render_template(
        'announcements.html',
        user=current_user,
        announcements=announcements,
        can_post_announcements=current_user.can_manage_team(),
        scope_filter=scope_filter,
    )


@bp.route('/announcements/<int:announcement_id>/toggle', methods=['POST'])
@login_required
def toggle(announcement_id):
    if not current_user.can_manage_team():
        abort(403)

    item = Announcement.query.get_or_404(announcement_id)
    item.is_active = not item.is_active
    db.session.commit()
    flash('Announcement updated.', 'success')
    return redirect(url_for('announcements.board'))
