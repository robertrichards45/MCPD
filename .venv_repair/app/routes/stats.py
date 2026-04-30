import os
import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, current_app, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..models import User, StatCategory, OfficerStat, StatsUpload, AuditLog
from ..permissions import can_manage_site, can_view_user

try:
    from ..services.excel_stats_parser import parse_excel
except Exception:
    parse_excel = None

bp = Blueprint('stats', __name__)


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def require_admin():
    if not can_manage_site(current_user):
        abort(403)


def year_key_for(date):
    if date.month >= 4:
        return f"{date.year}-{date.year+1}"
    return f"{date.year-1}-{date.year}"

@bp.route('/stats')
@login_required
def stats_home():
    year_key = year_key_for(_utcnow_naive())
    if current_user.can_manage_team():
        if can_manage_site(current_user):
            users = User.query.filter_by(active=True).all()
        else:
            users = [current_user] + list(current_user.direct_reports)
        categories = StatCategory.query.all()
        stats = OfficerStat.query.filter_by(year_key=year_key).all()
        return render_template('stats_admin.html', users=users, categories=categories, stats=stats, year_key=year_key, user=current_user)

    categories = StatCategory.query.all()
    stats = OfficerStat.query.filter_by(user_id=current_user.id, year_key=year_key).all()
    return render_template('stats_user.html', categories=categories, stats=stats, year_key=year_key, user=current_user)

@bp.route('/stats/upload', methods=['GET', 'POST'])
@login_required
def stats_upload():
    require_admin()
    if request.method == 'POST':
        if parse_excel is None:
            return render_template(
                'stats_upload.html',
                error='Stats import is unavailable: openpyxl is not installed on this system.',
                user=current_user
            )
        file = request.files.get('file')
        if not file:
            return render_template('stats_upload.html', error='No file uploaded.', user=current_user)
        save_dir = current_app.config['STATS_UPLOAD']
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{int(_utcnow_naive().timestamp())}-{file.filename}".replace(' ', '_')
        path = os.path.join(save_dir, filename)
        file.save(path)

        rows, layout = parse_excel(path)
        year_key = year_key_for(_utcnow_naive())
        unmatched = []
        categories_seen = set()

        for r in rows:
            officer_val = str(r['officer']).strip()
            category_val = str(r['category']).strip()
            if not officer_val or not category_val:
                continue
            categories_seen.add(category_val)
            user = User.query.filter(User.username.ilike(officer_val)).first() or User.query.filter(User.name.ilike(officer_val)).first()
            if not user:
                unmatched.append(officer_val)
                continue
            category = StatCategory.query.filter_by(name=category_val).first()
            if not category:
                category = StatCategory(name=category_val, target_value=0)
                db.session.add(category)
                db.session.flush()
            stat = OfficerStat.query.filter_by(user_id=user.id, category_id=category.id, year_key=year_key).first()
            if not stat:
                stat = OfficerStat(user_id=user.id, category_id=category.id, year_key=year_key, value=0)
                db.session.add(stat)
            stat.value = int(r['value'])

        upload = StatsUpload(uploaded_by=current_user.id, filename=file.filename, file_path=path,
                             parse_summary_json=json.dumps({
                                 'layout': layout,
                                 'unmatched_officers': list(set(unmatched)),
                                 'rows': len(rows),
                                 'categories': sorted(list(categories_seen))
                             }))
        db.session.add(upload)
        db.session.add(AuditLog(actor_id=current_user.id, action='stats_upload', details=file.filename))
        db.session.commit()
        return redirect(url_for('admin.stats_uploads'))

    return render_template('stats_upload.html', user=current_user)

@bp.route('/stats/<int:user_id>')
@login_required
def stats_user(user_id):
    year_key = year_key_for(_utcnow_naive())
    user_obj = User.query.get_or_404(user_id)
    if not can_view_user(current_user, user_obj):
        abort(403)
    categories = StatCategory.query.all()
    stats = OfficerStat.query.filter_by(user_id=user_obj.id, year_key=year_key).all()
    return render_template('stats_user.html', categories=categories, stats=stats, year_key=year_key, user=current_user, profile_user=user_obj)

@bp.route('/officers/<int:user_id>')
@login_required
def officer_profile(user_id):
    year_key = year_key_for(_utcnow_naive())
    user_obj = User.query.get_or_404(user_id)
    if not can_view_user(current_user, user_obj):
        abort(403)
    categories = StatCategory.query.all()
    stats = OfficerStat.query.filter_by(user_id=user_obj.id, year_key=year_key).all()
    return render_template('officer_profile.html', profile=user_obj, categories=categories, stats=stats, year_key=year_key, user=current_user)
