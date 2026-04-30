import os
import base64
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, current_app, abort, send_file
from flask_login import login_required, current_user
from ..extensions import db
from ..models import TrainingRoster, TrainingSignature, AuditLog, User
from ..permissions import can_manage_site
from ..services.pdf_signing import append_signature_page

bp = Blueprint('training', __name__)


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _parse_yyyymmdd(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return None

def require_admin():
    if not can_manage_site(current_user):
        abort(403)

@bp.route('/training')
@login_required
def training_list():
    rosters = TrainingRoster.query.order_by(TrainingRoster.uploaded_at.desc()).all()
    return render_template('training_list.html', rosters=rosters, user=current_user)

@bp.route('/training/menu')
@login_required
def training_menu():
    return render_template('training_menu.html', user=current_user)

@bp.route('/training/search')
@login_required
def training_search():
    title = (request.args.get('title') or '').strip()
    description = (request.args.get('description') or '').strip()
    date_from_raw = (request.args.get('date_from') or '').strip()
    date_to_raw = (request.args.get('date_to') or '').strip()

    date_from = _parse_yyyymmdd(date_from_raw)
    date_to = _parse_yyyymmdd(date_to_raw)
    error = None
    if date_from_raw and not date_from:
        error = 'Start date must be in YYYYMMDD.'
    if date_to_raw and not date_to:
        error = 'End date must be in YYYYMMDD.'

    rosters = []
    if not error and (title or description or date_from or date_to):
        query = TrainingRoster.query
        if title:
            query = query.filter(TrainingRoster.title.ilike(f"%{title}%"))
        if description:
            query = query.filter(TrainingRoster.description.ilike(f"%{description}%"))
        if date_from:
            query = query.filter(TrainingRoster.uploaded_at >= date_from)
        if date_to:
            query = query.filter(TrainingRoster.uploaded_at <= date_to)
        rosters = query.order_by(TrainingRoster.uploaded_at.desc()).all()

    return render_template(
        'training_search.html',
        user=current_user,
        rosters=rosters,
        error=error,
        title=title,
        description=description,
        date_from=date_from_raw,
        date_to=date_to_raw,
    )

@bp.route('/training/upload', methods=['GET', 'POST'])
@login_required
def training_upload():
    require_admin()
    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form.get('title') or (file.filename if file else 'Roster')
        description = request.form.get('description')
        if not file:
            return render_template('training_upload.html', error='No file uploaded.', user=current_user)
        save_dir = current_app.config['TRAINING_UPLOAD']
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{int(_utcnow_naive().timestamp())}-{file.filename}".replace(' ', '_')
        path = os.path.join(save_dir, filename)
        file.save(path)
        roster = TrainingRoster(title=title, description=description, file_path_original=path,
                                uploaded_by=current_user.id)
        db.session.add(roster)
        db.session.add(AuditLog(actor_id=current_user.id, action='training_upload', details=title))
        db.session.commit()
        return redirect(url_for('training.training_list'))
    return render_template('training_upload.html', user=current_user)

@bp.route('/training/<int:roster_id>')
@login_required
def training_detail(roster_id):
    roster = TrainingRoster.query.get_or_404(roster_id)
    signatures = TrainingSignature.query.filter_by(roster_id=roster_id).order_by(TrainingSignature.signed_at.desc()).all()
    users = {u.id: u for u in User.query.all()}
    return render_template('training_detail.html', roster=roster, signatures=signatures, users=users, user=current_user)

@bp.route('/training/<int:roster_id>/sign', methods=['POST'])
@login_required
def training_sign(roster_id):
    roster = TrainingRoster.query.get_or_404(roster_id)
    existing = TrainingSignature.query.filter_by(roster_id=roster_id, user_id=current_user.id).first()
    if existing:
        return redirect(url_for('training.training_detail', roster_id=roster_id))

    data_url = request.form.get('signature_data')
    comment = request.form.get('comment')
    if not data_url:
        return redirect(url_for('training.training_detail', roster_id=roster_id))

    header, encoded = data_url.split(',', 1)
    img_bytes = base64.b64decode(encoded)
    sig_dir = current_app.config['SIGNATURES_DIR']
    os.makedirs(sig_dir, exist_ok=True)
    sig_name = f"sig-{roster_id}-{current_user.id}-{int(_utcnow_naive().timestamp())}.png"
    sig_path = os.path.join(sig_dir, sig_name)
    with open(sig_path, 'wb') as f:
        f.write(img_bytes)

    signature = TrainingSignature(roster_id=roster_id, user_id=current_user.id,
                                  signature_path=sig_path, comment=comment)
    db.session.add(signature)
    db.session.add(AuditLog(actor_id=current_user.id, action='training_sign', details=f'Roster {roster_id}'))
    db.session.commit()

    compiled = roster.file_path_compiled or roster.file_path_original + '.compiled.pdf'
    append_signature_page(roster.file_path_original, sig_path, current_user.display_name, _utcnow_naive().isoformat(), compiled)
    roster.file_path_compiled = compiled
    db.session.commit()

    return redirect(url_for('training.training_detail', roster_id=roster_id))

@bp.route('/training/<int:roster_id>/download')
@login_required
def training_download(roster_id):
    roster = TrainingRoster.query.get_or_404(roster_id)
    path = roster.file_path_compiled or roster.file_path_original
    return send_file(path, as_attachment=True)
