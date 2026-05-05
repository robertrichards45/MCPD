import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone

from flask import (
    Blueprint, abort, current_app, flash, redirect,
    render_template, request, send_file, url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import OfficerQualification, QualificationCategory, User
from ..permissions import can_manage_site, can_supervisor_review

bp = Blueprint('qual_tracker', __name__)

_ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png'}


def _today():
    return date.today().isoformat()


def _expiration_date(completed_str, validity_days):
    try:
        d = date.fromisoformat(completed_str)
        return (d + timedelta(days=validity_days)).isoformat()
    except (ValueError, TypeError):
        return ''


def _status(expiration_str, warn_days):
    """Returns 'expired' | 'critical' | 'warning' | 'current' | 'unknown'."""
    if not expiration_str:
        return 'unknown'
    try:
        exp = date.fromisoformat(expiration_str)
        today = date.today()
        if exp < today:
            return 'expired'
        days_left = (exp - today).days
        if days_left <= 7:
            return 'critical'
        if days_left <= warn_days:
            return 'warning'
        return 'current'
    except ValueError:
        return 'unknown'


def _days_left(expiration_str):
    if not expiration_str:
        return None
    try:
        exp = date.fromisoformat(expiration_str)
        return (exp - date.today()).days
    except ValueError:
        return None


def _latest_record(officer_id, category_id):
    return (
        OfficerQualification.query
        .filter_by(officer_id=officer_id, category_id=category_id)
        .order_by(OfficerQualification.completed_date.desc())
        .first()
    )


def _save_doc(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in _ALLOWED_EXT:
        return None
    save_dir = os.path.join(current_app.config['UPLOAD_ROOT'], 'qualifications')
    os.makedirs(save_dir, exist_ok=True)
    filename = f"qual-{uuid.uuid4().hex}.{ext}"
    path = os.path.join(save_dir, filename)
    file.save(path)
    return path


def _required_roles(category):
    try:
        return json.loads(category.required_roles) if category.required_roles else []
    except (ValueError, TypeError):
        return []


def _officer_needs_category(officer, category):
    roles = _required_roles(category)
    if not roles:
        return True
    return (officer.normalized_role or '') in roles


# ── Personal tracker ──────────────────────────────────────────────────────────

@bp.route('/training/tracker')
@login_required
def tracker_personal():
    categories = QualificationCategory.query.filter_by(active=True).order_by(QualificationCategory.name).all()
    rows = []
    for cat in categories:
        if not _officer_needs_category(current_user, cat):
            continue
        rec = _latest_record(current_user.id, cat.id)
        status = _status(rec.expiration_date if rec else None, cat.warn_days_before)
        rows.append({
            'category': cat,
            'record': rec,
            'status': status,
            'days_left': _days_left(rec.expiration_date if rec else None),
        })

    rows.sort(key=lambda r: {'expired': 0, 'critical': 1, 'warning': 2, 'unknown': 3, 'current': 4}.get(r['status'], 5))
    warnings = [r for r in rows if r['status'] in ('expired', 'critical', 'warning')]

    return render_template(
        'qual_tracker_personal.html',
        title='My Qualifications — MCPD Portal',
        rows=rows,
        warnings=warnings,
        can_log=can_supervisor_review(current_user),
        user=current_user,
    )


# ── Readiness dashboard (supervisors) ────────────────────────────────────────

@bp.route('/training/tracker/readiness')
@login_required
def tracker_readiness():
    if not can_supervisor_review(current_user):
        abort(403)

    categories = QualificationCategory.query.filter_by(active=True).order_by(QualificationCategory.name).all()
    officers = User.query.filter_by(active=True).order_by(User.last_name, User.first_name, User.username).all()

    grid = []
    for officer in officers:
        officer_cats = [c for c in categories if _officer_needs_category(officer, c)]
        if not officer_cats:
            continue
        cells = []
        worst = 'current'
        order = {'expired': 0, 'critical': 1, 'warning': 2, 'unknown': 3, 'current': 4}
        for cat in officer_cats:
            rec = _latest_record(officer.id, cat.id)
            st = _status(rec.expiration_date if rec else None, cat.warn_days_before)
            if order.get(st, 5) < order.get(worst, 5):
                worst = st
            cells.append({'category': cat, 'record': rec, 'status': st, 'days_left': _days_left(rec.expiration_date if rec else None)})
        grid.append({'officer': officer, 'cells': cells, 'worst_status': worst})

    grid.sort(key=lambda r: {'expired': 0, 'critical': 1, 'warning': 2, 'unknown': 3, 'current': 4}.get(r['worst_status'], 5))

    total = len(grid)
    issues = sum(1 for r in grid if r['worst_status'] in ('expired', 'critical', 'warning', 'unknown'))

    return render_template(
        'qual_tracker_readiness.html',
        title='Readiness Dashboard — MCPD Portal',
        categories=categories,
        grid=grid,
        total=total,
        issues=issues,
        user=current_user,
    )


# ── Log a completion ──────────────────────────────────────────────────────────

@bp.route('/training/tracker/log', methods=['GET', 'POST'])
@login_required
def tracker_log():
    if not can_supervisor_review(current_user):
        abort(403)

    categories = QualificationCategory.query.filter_by(active=True).order_by(QualificationCategory.name).all()
    officers = User.query.filter_by(active=True).order_by(User.last_name, User.first_name, User.username).all()
    preselect_officer = request.args.get('officer_id', type=int)
    preselect_cat = request.args.get('category_id', type=int)

    if request.method == 'POST':
        officer_id = request.form.get('officer_id', type=int)
        category_id = request.form.get('category_id', type=int)
        completed_date = request.form.get('completed_date', '').strip()
        notes = request.form.get('notes', '').strip() or None

        cat = QualificationCategory.query.get(category_id) if category_id else None
        if not officer_id or not cat or not completed_date:
            flash('Officer, qualification type, and completion date are required.', 'danger')
        else:
            exp = _expiration_date(completed_date, cat.validity_days)
            rec = OfficerQualification(
                officer_id=officer_id,
                category_id=category_id,
                completed_date=completed_date,
                expiration_date=exp,
                notes=notes,
                logged_by=current_user.id,
            )
            doc = request.files.get('document')
            rec.file_path = _save_doc(doc)
            db.session.add(rec)
            db.session.commit()
            flash('Qualification logged.', 'success')
            return redirect(url_for('qual_tracker.tracker_readiness'))

    return render_template(
        'qual_tracker_log.html',
        title='Log Qualification — MCPD Portal',
        categories=categories,
        officers=officers,
        preselect_officer=preselect_officer,
        preselect_cat=preselect_cat,
        today=_today(),
        user=current_user,
    )


# ── Document serve ────────────────────────────────────────────────────────────

@bp.route('/training/tracker/record/<int:record_id>/doc')
@login_required
def tracker_doc(record_id):
    rec = OfficerQualification.query.get_or_404(record_id)
    if rec.officer_id != current_user.id and not can_supervisor_review(current_user):
        abort(403)
    if not rec.file_path or not os.path.isfile(rec.file_path):
        abort(404)
    return send_file(rec.file_path)


# ── Delete record ─────────────────────────────────────────────────────────────

@bp.route('/training/tracker/record/<int:record_id>/delete', methods=['POST'])
@login_required
def tracker_delete(record_id):
    if not can_supervisor_review(current_user):
        abort(403)
    rec = OfficerQualification.query.get_or_404(record_id)
    db.session.delete(rec)
    db.session.commit()
    flash('Record removed.', 'success')
    return redirect(request.referrer or url_for('qual_tracker.tracker_readiness'))


# ── Manage categories (admin) ─────────────────────────────────────────────────

@bp.route('/training/tracker/categories')
@login_required
def tracker_categories():
    if not can_manage_site(current_user):
        abort(403)
    cats = QualificationCategory.query.order_by(QualificationCategory.name).all()
    return render_template('qual_tracker_categories.html', title='Qualification Types — MCPD Portal', cats=cats)


@bp.route('/training/tracker/categories/new', methods=['GET', 'POST'])
@login_required
def tracker_category_new():
    if not can_manage_site(current_user):
        abort(403)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name is required.', 'danger')
        else:
            cat = QualificationCategory(
                name=name,
                description=request.form.get('description', '').strip() or None,
                validity_days=int(request.form.get('validity_days') or 365),
                warn_days_before=int(request.form.get('warn_days_before') or 30),
                required_roles=request.form.get('required_roles') or None,
                created_by=current_user.id,
            )
            db.session.add(cat)
            db.session.commit()
            flash(f'"{name}" added.', 'success')
            return redirect(url_for('qual_tracker.tracker_categories'))
    return render_template('qual_tracker_category_form.html', title='New Qualification Type', cat=None)


@bp.route('/training/tracker/categories/<int:cat_id>/edit', methods=['GET', 'POST'])
@login_required
def tracker_category_edit(cat_id):
    if not can_manage_site(current_user):
        abort(403)
    cat = QualificationCategory.query.get_or_404(cat_id)
    if request.method == 'POST':
        cat.name = request.form.get('name', '').strip() or cat.name
        cat.description = request.form.get('description', '').strip() or None
        cat.validity_days = int(request.form.get('validity_days') or cat.validity_days)
        cat.warn_days_before = int(request.form.get('warn_days_before') or cat.warn_days_before)
        cat.required_roles = request.form.get('required_roles') or None
        cat.active = request.form.get('active') == '1'
        db.session.commit()
        flash('Updated.', 'success')
        return redirect(url_for('qual_tracker.tracker_categories'))
    return render_template('qual_tracker_category_form.html', title='Edit Qualification Type', cat=cat)
