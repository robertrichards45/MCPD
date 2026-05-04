import os
import uuid
from datetime import datetime, timezone

from flask import (
    Blueprint, abort, current_app, flash, redirect,
    render_template, request, send_file, url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    BOLO_STATUS_ACTIVE, BOLO_STATUS_CANCELLED, BOLO_STATUS_LOCATED,
    BOLO_THREAT_ARMED, BOLO_THREAT_HIGH, BOLO_THREAT_LOW, BOLO_THREAT_MODERATE,
    BOLOEntry,
)
from ..permissions import can_supervisor_review

bp = Blueprint('bolo', __name__)

_ALLOWED_PHOTO_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
_THREAT_ORDER = {BOLO_THREAT_ARMED: 0, BOLO_THREAT_HIGH: 1, BOLO_THREAT_MODERATE: 2, BOLO_THREAT_LOW: 3}


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _supervisor_required():
    if not can_supervisor_review(current_user):
        abort(403)


def _save_photo(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in _ALLOWED_PHOTO_EXT:
        return None
    save_dir = os.path.join(current_app.config['UPLOAD_ROOT'], 'bolo')
    os.makedirs(save_dir, exist_ok=True)
    filename = f"bolo-{uuid.uuid4().hex}.{ext}"
    path = os.path.join(save_dir, filename)
    file.save(path)
    return path


def _delete_photo(path):
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _auto_expire():
    """Mark entries whose expiration_date has passed as LOCATED/expired — just set cancelled."""
    today = _utcnow().date().isoformat()
    expired = BOLOEntry.query.filter(
        BOLOEntry.status == BOLO_STATUS_ACTIVE,
        BOLOEntry.expiration_date != None,
        BOLOEntry.expiration_date < today,
    ).all()
    for e in expired:
        e.status = BOLO_STATUS_CANCELLED
        e.resolution_notes = (e.resolution_notes or '') + ' [Auto-expired]'
    if expired:
        db.session.commit()


# ── Board ─────────────────────────────────────────────────────────────────────

@bp.route('/bolo/')
@login_required
def bolo_board():
    _auto_expire()
    status_filter = request.args.get('status', 'ACTIVE')
    q = (request.args.get('q') or '').strip()

    query = BOLOEntry.query
    if status_filter in (BOLO_STATUS_ACTIVE, BOLO_STATUS_LOCATED, BOLO_STATUS_CANCELLED):
        query = query.filter(BOLOEntry.status == status_filter)
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                BOLOEntry.subject_name.ilike(like),
                BOLOEntry.aliases.ilike(like),
                BOLOEntry.offense.ilike(like),
                BOLOEntry.vehicle_plate.ilike(like),
                BOLOEntry.vehicle_description.ilike(like),
            )
        )

    entries = query.order_by(BOLOEntry.created_at.desc()).all()
    # Sort active entries by threat level severity
    if status_filter == BOLO_STATUS_ACTIVE:
        entries = sorted(entries, key=lambda e: _THREAT_ORDER.get(e.threat_level, 99))

    active_count = BOLOEntry.query.filter_by(status=BOLO_STATUS_ACTIVE).count()

    return render_template(
        'bolo_board.html',
        title='BOLO Board — MCPD Portal',
        entries=entries,
        status_filter=status_filter,
        q=q,
        active_count=active_count,
        can_manage=can_supervisor_review(current_user),
        BOLO_STATUS_ACTIVE=BOLO_STATUS_ACTIVE,
        BOLO_STATUS_LOCATED=BOLO_STATUS_LOCATED,
        BOLO_STATUS_CANCELLED=BOLO_STATUS_CANCELLED,
        BOLO_THREAT_ARMED=BOLO_THREAT_ARMED,
        BOLO_THREAT_HIGH=BOLO_THREAT_HIGH,
        BOLO_THREAT_MODERATE=BOLO_THREAT_MODERATE,
        BOLO_THREAT_LOW=BOLO_THREAT_LOW,
    )


# ── Detail ────────────────────────────────────────────────────────────────────

@bp.route('/bolo/<int:entry_id>')
@login_required
def bolo_detail(entry_id):
    entry = BOLOEntry.query.get_or_404(entry_id)
    return render_template(
        'bolo_detail.html',
        title=f'BOLO — {entry.subject_name}',
        entry=entry,
        can_manage=can_supervisor_review(current_user),
        BOLO_STATUS_ACTIVE=BOLO_STATUS_ACTIVE,
        BOLO_THREAT_ARMED=BOLO_THREAT_ARMED,
        BOLO_THREAT_HIGH=BOLO_THREAT_HIGH,
        BOLO_THREAT_MODERATE=BOLO_THREAT_MODERATE,
        BOLO_THREAT_LOW=BOLO_THREAT_LOW,
    )


# ── Photo serve ───────────────────────────────────────────────────────────────

@bp.route('/bolo/<int:entry_id>/photo')
@login_required
def bolo_photo(entry_id):
    entry = BOLOEntry.query.get_or_404(entry_id)
    if not entry.photo_path or not os.path.isfile(entry.photo_path):
        abort(404)
    return send_file(entry.photo_path)


# ── Create ────────────────────────────────────────────────────────────────────

@bp.route('/bolo/new', methods=['GET', 'POST'])
@login_required
def bolo_new():
    _supervisor_required()
    if request.method == 'POST':
        entry = BOLOEntry(
            subject_name=request.form.get('subject_name', '').strip(),
            aliases=request.form.get('aliases', '').strip() or None,
            race=request.form.get('race', '').strip() or None,
            sex=request.form.get('sex', '').strip() or None,
            dob=request.form.get('dob', '').strip() or None,
            height=request.form.get('height', '').strip() or None,
            weight=request.form.get('weight', '').strip() or None,
            hair=request.form.get('hair', '').strip() or None,
            eyes=request.form.get('eyes', '').strip() or None,
            offense=request.form.get('offense', '').strip() or None,
            description=request.form.get('description', '').strip() or None,
            vehicle_description=request.form.get('vehicle_description', '').strip() or None,
            vehicle_plate=request.form.get('vehicle_plate', '').strip().upper() or None,
            threat_level=request.form.get('threat_level', BOLO_THREAT_LOW),
            expiration_date=request.form.get('expiration_date', '').strip() or None,
            status=BOLO_STATUS_ACTIVE,
            created_by=current_user.id,
        )
        if not entry.subject_name:
            flash('Subject name is required.', 'danger')
            return render_template('bolo_form.html', title='New BOLO', entry=None,
                                   BOLO_THREAT_LOW=BOLO_THREAT_LOW, BOLO_THREAT_MODERATE=BOLO_THREAT_MODERATE,
                                   BOLO_THREAT_HIGH=BOLO_THREAT_HIGH, BOLO_THREAT_ARMED=BOLO_THREAT_ARMED)

        photo = request.files.get('photo')
        entry.photo_path = _save_photo(photo)

        db.session.add(entry)
        db.session.commit()
        flash(f'BOLO issued for {entry.subject_name}.', 'success')
        return redirect(url_for('bolo.bolo_detail', entry_id=entry.id))

    return render_template(
        'bolo_form.html',
        title='New BOLO',
        entry=None,
        BOLO_THREAT_LOW=BOLO_THREAT_LOW,
        BOLO_THREAT_MODERATE=BOLO_THREAT_MODERATE,
        BOLO_THREAT_HIGH=BOLO_THREAT_HIGH,
        BOLO_THREAT_ARMED=BOLO_THREAT_ARMED,
    )


# ── Edit ──────────────────────────────────────────────────────────────────────

@bp.route('/bolo/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def bolo_edit(entry_id):
    _supervisor_required()
    entry = BOLOEntry.query.get_or_404(entry_id)

    if request.method == 'POST':
        entry.subject_name = request.form.get('subject_name', '').strip() or entry.subject_name
        entry.aliases = request.form.get('aliases', '').strip() or None
        entry.race = request.form.get('race', '').strip() or None
        entry.sex = request.form.get('sex', '').strip() or None
        entry.dob = request.form.get('dob', '').strip() or None
        entry.height = request.form.get('height', '').strip() or None
        entry.weight = request.form.get('weight', '').strip() or None
        entry.hair = request.form.get('hair', '').strip() or None
        entry.eyes = request.form.get('eyes', '').strip() or None
        entry.offense = request.form.get('offense', '').strip() or None
        entry.description = request.form.get('description', '').strip() or None
        entry.vehicle_description = request.form.get('vehicle_description', '').strip() or None
        entry.vehicle_plate = (request.form.get('vehicle_plate', '').strip().upper()) or None
        entry.threat_level = request.form.get('threat_level', entry.threat_level)
        entry.expiration_date = request.form.get('expiration_date', '').strip() or None
        entry.updated_at = _utcnow()

        photo = request.files.get('photo')
        if photo and photo.filename:
            _delete_photo(entry.photo_path)
            entry.photo_path = _save_photo(photo)

        db.session.commit()
        flash('BOLO updated.', 'success')
        return redirect(url_for('bolo.bolo_detail', entry_id=entry.id))

    return render_template(
        'bolo_form.html',
        title='Edit BOLO',
        entry=entry,
        BOLO_THREAT_LOW=BOLO_THREAT_LOW,
        BOLO_THREAT_MODERATE=BOLO_THREAT_MODERATE,
        BOLO_THREAT_HIGH=BOLO_THREAT_HIGH,
        BOLO_THREAT_ARMED=BOLO_THREAT_ARMED,
    )


# ── Locate ────────────────────────────────────────────────────────────────────

@bp.route('/bolo/<int:entry_id>/locate', methods=['POST'])
@login_required
def bolo_locate(entry_id):
    entry = BOLOEntry.query.get_or_404(entry_id)
    if entry.status != BOLO_STATUS_ACTIVE:
        flash('This BOLO is already closed.', 'warning')
        return redirect(url_for('bolo.bolo_detail', entry_id=entry.id))
    notes = (request.form.get('resolution_notes') or '').strip()
    entry.status = BOLO_STATUS_LOCATED
    entry.resolved_at = _utcnow()
    entry.resolved_by = current_user.id
    entry.resolution_notes = notes or None
    db.session.commit()
    flash(f'{entry.subject_name} marked as located.', 'success')
    return redirect(url_for('bolo.bolo_board'))


# ── Cancel ────────────────────────────────────────────────────────────────────

@bp.route('/bolo/<int:entry_id>/cancel', methods=['POST'])
@login_required
def bolo_cancel(entry_id):
    _supervisor_required()
    entry = BOLOEntry.query.get_or_404(entry_id)
    entry.status = BOLO_STATUS_CANCELLED
    entry.resolved_at = _utcnow()
    entry.resolved_by = current_user.id
    entry.resolution_notes = (request.form.get('resolution_notes') or '').strip() or 'Cancelled by supervisor.'
    db.session.commit()
    flash('BOLO cancelled.', 'success')
    return redirect(url_for('bolo.bolo_board'))
