import hmac
import os
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import AuditLog, BodycamFootage, Report, utcnow_naive
from ..services.ai_client import ask_openai_with_system, configured_openai_api_key, is_ai_unavailable_message

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


@bp.get('/tools/blotter')
@login_required
def blotter_tool():
    return render_template('narrative_5w_tool.html', user=current_user, mobile_mode=False, tool_mode='blotter')


@bp.get('/mobile/tools/blotter')
@login_required
def mobile_blotter_tool():
    return render_template(
        'mobile_narrative_5w_tool.html',
        **{
            'title': 'Blotter Writer | MCPD Mobile',
            'body_class': 'mobile-foundation',
            'mobile_title': 'Blotter Writer',
            'mobile_active_tab': 'more',
            'user': current_user,
            'tool_mode': 'blotter',
        },
    )


_NARRATIVE_CHECK_PROMPT = (
    "You are an MCPD narrative quality evaluator. You evaluate police incident report narratives and 5W summaries "
    "against Marine Corps Police Department standards.\n\n"
    "Evaluate the submitted text and return a JSON object with:\n"
    "- score: integer 1-10 (10 = publication-ready)\n"
    "- grade: letter grade (A/B/C/D/F)\n"
    "- strengths: list of 1-3 specific things done well\n"
    "- issues: list of specific problems found\n"
    "- suggestions: list of 1-3 concrete improvement actions\n"
    "- improved_opening: one improved opening sentence using the facts given\n\n"
    "MCPD Narrative Standards:\n"
    "- Must include: date/time, location, who (victim/suspect/witness with identifiers), what happened, "
    "officer arrival and observations, actions taken, disposition, supervisor notification if required.\n"
    "- Must use chronological order starting with officer dispatch or response.\n"
    "- Must use objective language — no assumptions or opinions.\n"
    "- Must include legal basis language for any detention, arrest, or search.\n"
    "- Must document evidence collection and chain of custody if applicable.\n"
    "- Common failures: missing times, no legal authority stated, vague dispositions, undefined acronyms, "
    "inconsistent person references, invented facts.\n\n"
    "Return only the JSON object. No extra text."
)

_BLOTTER_PROMPT = (
    "You are an MCPD blotter writer. Convert the officer's call log entries into a professionally formatted "
    "watch blotter for MCLB Albany.\n\n"
    "A blotter entry should be 1-3 sentences per call: time, nature of call, location, disposition. "
    "Use past tense, objective language, and standard police terminology. "
    "Do not invent facts not in the officer's notes.\n\n"
    "Format: numbered list. Example:\n"
    "1. 1423 — Larceny report at PX parking lot. Vehicle broken into; laptop stolen. Victim statement taken; "
    "case forwarded for follow-up.\n\n"
    "Convert the following call log into a watch blotter. Include a header line: "
    "'MCLB Albany Watch Blotter — [infer date/shift if stated, otherwise [Date/Shift]]'"
)


def _csrf_ok() -> bool:
    token = (
        request.headers.get('X-CSRFToken')
        or (request.get_json(silent=True) or {}).get('_csrf_token')
        or ''
    )
    expected = session.get('_csrf_token', '')
    return bool(expected and hmac.compare_digest(str(token), str(expected)))


@bp.post('/api/tools/narrative/check')
@login_required
def narrative_quality_check():
    if not _csrf_ok():
        return jsonify({'ok': False, 'error': 'Invalid request.'}), 403
    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    if not text:
        return jsonify({'ok': False, 'error': 'No text provided.'}), 400
    if len(text) > 8000:
        text = text[:8000]

    api_key = configured_openai_api_key()
    raw = ask_openai_with_system(text, _NARRATIVE_CHECK_PROMPT, api_key)
    if is_ai_unavailable_message(raw):
        return jsonify({'ok': False, 'error': 'AI quality check is unavailable. Check your OpenAI key.'}), 503

    import json as _json
    try:
        start = raw.find('{')
        end = raw.rfind('}') + 1
        result = _json.loads(raw[start:end]) if start >= 0 and end > start else {}
    except Exception:
        result = {}

    if not result.get('score'):
        return jsonify({'ok': False, 'error': 'Could not parse quality check result.'}), 500

    return jsonify({'ok': True, 'result': result})


@bp.post('/api/tools/blotter/generate')
@login_required
def blotter_generate():
    if not _csrf_ok():
        return jsonify({'ok': False, 'error': 'Invalid request.'}), 403
    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    if not text:
        return jsonify({'ok': False, 'error': 'No call log provided.'}), 400
    if len(text) > 8000:
        text = text[:8000]

    api_key = configured_openai_api_key()
    result = ask_openai_with_system(text, _BLOTTER_PROMPT, api_key)
    if is_ai_unavailable_message(result):
        return jsonify({'ok': False, 'error': 'AI blotter generation is unavailable.'}), 503

    return jsonify({'ok': True, 'blotter': result})
