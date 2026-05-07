import os
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import AuditLog, BodycamFootage, Report, utcnow_naive

bp = Blueprint('bodycam', __name__)

_VIDEO_EXTENSIONS = {
    'video/webm': '.webm',
    'video/mp4': '.mp4',
    'video/quicktime': '.mov',
}


def _storage_root() -> Path:
    root = Path(current_app.config['UPLOAD_ROOT']) / 'bodycam'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _can_view(item: BodycamFootage) -> bool:
    if item.officer_user_id == current_user.id:
        return True
    return bool(current_user.can_manage_team() or current_user.can_manage_site())


def _safe_item_or_404(footage_id: int) -> BodycamFootage:
    item = db.session.get(BodycamFootage, footage_id)
    if not item:
        abort(404)
    if not _can_view(item):
        abort(403)
    return item


def _visible_query():
    query = BodycamFootage.query
    if not (current_user.can_manage_team() or current_user.can_manage_site()):
        query = query.filter_by(officer_user_id=current_user.id)
    return query.order_by(BodycamFootage.created_at.desc(), BodycamFootage.id.desc())


@bp.get('/bodycam')
@login_required
def library():
    items = _visible_query().limit(100).all()
    return render_template('bodycam_library.html', items=items, user=current_user)


@bp.get('/bodycam/new')
@login_required
def new_recording():
    return render_template('bodycam_record.html', user=current_user)


@bp.get('/mobile/bodycam')
@login_required
def mobile_recording():
    return render_template(
        'mobile_bodycam_record.html',
        **{
            'title': 'Body Cam Mode | MCPD Mobile',
            'body_class': 'mobile-foundation',
            'mobile_title': 'Body Cam Mode',
            'mobile_active_tab': 'more',
            'mobile_header_note': 'Record video, audio, and browser-supported transcription.',
            'user': current_user,
        },
    )


@bp.get('/mobile/bodycam/footage')
@login_required
def mobile_library():
    items = _visible_query().limit(50).all()
    return render_template(
        'mobile_bodycam_library.html',
        items=items,
        **{
            'title': 'Bodycam Footage | MCPD Mobile',
            'body_class': 'mobile-foundation',
            'mobile_title': 'Bodycam Footage',
            'mobile_active_tab': 'more',
            'user': current_user,
        },
    )


@bp.get('/bodycam/<int:footage_id>')
@login_required
def detail(footage_id):
    item = _safe_item_or_404(footage_id)
    return render_template('bodycam_detail.html', item=item, user=current_user)


@bp.post('/bodycam/upload')
@login_required
def upload():
    upload_file = request.files.get('video')
    if not upload_file or not upload_file.filename:
        return jsonify({'ok': False, 'error': 'No video was provided.'}), 400

    mime_type = (upload_file.mimetype or '').lower()
    extension = _VIDEO_EXTENSIONS.get(mime_type) or Path(upload_file.filename).suffix.lower() or '.webm'
    if extension not in {'.webm', '.mp4', '.mov', '.m4v'}:
        return jsonify({'ok': False, 'error': 'Unsupported video format.'}), 400

    timestamp = utcnow_naive().strftime('%Y%m%d-%H%M%S')
    base_name = secure_filename(request.form.get('title') or upload_file.filename or 'bodycam')
    file_name = f'bodycam-{current_user.id}-{timestamp}-{base_name}'
    if not file_name.lower().endswith(extension):
        file_name += extension

    officer_dir = _storage_root() / str(current_user.id)
    officer_dir.mkdir(parents=True, exist_ok=True)
    target = officer_dir / file_name
    upload_file.save(target)

    title = (request.form.get('title') or '').strip() or f'Bodycam Recording {timestamp}'
    report_id = request.form.get('report_id', type=int)
    if report_id and not db.session.get(Report, report_id):
        report_id = None

    item = BodycamFootage(
        officer_user_id=current_user.id,
        report_id=report_id,
        title=title[:200],
        incident_number=(request.form.get('incident_number') or '').strip()[:80] or None,
        location=(request.form.get('location') or '').strip()[:255] or None,
        file_path=str(target),
        file_name=file_name,
        mime_type=mime_type or 'video/webm',
        duration_seconds=request.form.get('duration_seconds', type=int),
        transcript_text=(request.form.get('transcript_text') or '').strip() or None,
        notes=(request.form.get('notes') or '').strip() or None,
    )
    db.session.add(item)
    db.session.add(AuditLog(actor_id=current_user.id, action='bodycam_upload', details=title[:250]))
    db.session.commit()
    return jsonify({'ok': True, 'id': item.id, 'detailUrl': url_for('bodycam.detail', footage_id=item.id)})


@bp.get('/bodycam/<int:footage_id>/media')
@login_required
def media(footage_id):
    item = _safe_item_or_404(footage_id)
    path = Path(item.file_path)
    try:
        path.relative_to(_storage_root())
    except ValueError:
        abort(403)
    if not path.exists() or not path.is_file():
        abort(404)
    return send_file(path, mimetype=item.mime_type or 'video/webm', as_attachment=False, download_name=item.file_name)


@bp.get('/bodycam/<int:footage_id>/download')
@login_required
def download(footage_id):
    item = _safe_item_or_404(footage_id)
    path = Path(item.file_path)
    try:
        path.relative_to(_storage_root())
    except ValueError:
        abort(403)
    if not path.exists() or not path.is_file():
        abort(404)
    return send_file(path, mimetype=item.mime_type or 'video/webm', as_attachment=True, download_name=item.file_name)


@bp.get('/tools/narrative')
@login_required
def narrative_tool():
    return render_template('narrative_5w_tool.html', user=current_user, mobile_mode=False, tool_mode='narrative')


@bp.get('/tools/5w')
@login_required
def five_w_tool():
    return render_template('narrative_5w_tool.html', user=current_user, mobile_mode=False, tool_mode='5w')


@bp.get('/bodycam/narrative')
@login_required
def bodycam_narrative_alias():
    return redirect(url_for('bodycam.narrative_tool'))


@bp.get('/mobile/tools/narrative')
@login_required
def mobile_narrative_tool():
    return render_template(
        'mobile_narrative_5w_tool.html',
        **{
            'title': 'Narrative Creator | MCPD Mobile',
            'body_class': 'mobile-foundation',
            'mobile_title': 'Narrative Creator',
            'mobile_active_tab': 'more',
            'user': current_user,
            'tool_mode': 'narrative',
        },
    )


@bp.get('/mobile/tools/5w')
@login_required
def mobile_five_w_tool():
    return render_template(
        'mobile_narrative_5w_tool.html',
        **{
            'title': '5W Builder | MCPD Mobile',
            'body_class': 'mobile-foundation',
            'mobile_title': '5W Builder',
            'mobile_active_tab': 'more',
            'user': current_user,
            'tool_mode': '5w',
        },
    )
