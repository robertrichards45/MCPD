import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_login import current_user, login_required
from jinja2 import TemplateNotFound
from werkzeug.utils import secure_filename

from ..permissions import can_manage_site
from ..services.ai_client import (
    _ALLOWED_VOICES,
    ask_openai_with_system,
    configured_openai_api_key,
    is_ai_unavailable_message,
    openai_key_status,
    openai_tts,
)

try:
    from ..services.smart_filing import allowed_file, build_storage_path, classify_document, smart_title
except Exception:
    allowed_file = None
    build_storage_path = None
    classify_document = None
    smart_title = None

bp = Blueprint('assistant', __name__)

_SYSTEM_PROMPT = (
    "You are MCPD Assistant, a knowledgeable and professional AI assistant built into the Marine Corps "
    "Police Department field portal. You help officers with questions about law, policy, report writing, "
    "incident procedures, UCMJ, use of force, traffic enforcement, and general police work. "
    "You can also help officers move around the portal and complete forms by asking one clear question at a time. "
    "Keep a natural multi-turn conversation like a professional voice assistant. "
    "Be concise, direct, and professional. When you don't know something with confidence, say so clearly. "
    "Avoid unnecessary filler phrases. Speak plainly as if briefing another officer. "
    "Never invent form answers, legal citations, evidence, statements, or report facts."
)


def _local_assistant_reply(message: str) -> str:
    """Reliable MCPD fallback when premium AI is not configured or unavailable."""
    text = (message or '').strip().lower()
    if not text:
        return 'Tell me what you need help with, such as starting a report, finding paperwork, searching law, or opening forms.'

    if any(term in text for term in ('start report', 'start a report', 'new report', 'incident report', 'write report', 'start a call')):
        return (
            'To start a report, open Start Report and work through Parties, Facts, Narrative, Paperwork, and Review. '
            f'Start here: {url_for("reports.new_report")}. On mobile, use {url_for("mobile.incident_start")}.'
        )
    if any(term in text for term in ('law', 'charge', 'statute', 'ucmj', 'federal', 'georgia', 'order applies')):
        return (
            'Use Law Lookup in plain language. Describe what happened, who was involved, where it happened, and whether it was on base. '
            f'Open Law Lookup: {url_for("legal.legal_lookup")}. Verify final charge selection with supervisor/legal review.'
        )
    if any(term in text for term in ('paperwork', 'forms needed', 'what forms', 'navigator', 'packet')):
        return (
            'Use the Paperwork Navigator for required and likely paperwork. Select the call type, confirm the facts, then add only the forms actually used. '
            f'Open Navigator: {url_for("reference.incident_paperwork_guide")}.'
        )
    if any(term in text for term in ('form', 'pdf', 'statement', 'domestic supplemental', 'stat sheet')):
        return (
            'Open Forms Library, choose the official form, fill only fields shown on the source PDF, then preview before download or email. '
            f'Open Forms: {url_for("forms.list_forms")}.'
        )
    if any(term in text for term in ('training', 'roster', 'sign training', 'qualification')):
        return (
            'Open Training to view assigned rosters, sign your own line, and track completions. '
            f'Open Training: {url_for("training.training_menu")}.'
        )
    if any(term in text for term in ('personnel', 'officer', 'watch', 'shift', 'role', 'installation')):
        return (
            'Personnel tools let authorized users edit officer profiles, roles, installation, shift, and watch assignments. '
            f'Open Personnel: {url_for("auth.manage_users")}.'
        )
    if any(term in text for term in ('scanner', 'scan id', 'license', 'driver license', 'camera')):
        return (
            'For ID scanning, use the mobile person editor. Live camera scanning requires browser camera support and HTTPS on phones; '
            'manual entry and paste/photo fallback should remain available so the report flow is not blocked.'
        )
    if any(term in text for term in ('accident', 'crash', 'diagram', 'reconstruction')):
        return (
            'Use Accident Reconstruction under Reports for crash diagrams, measurements, vehicles, media, timeline, and export. '
            f'Open Accident Reconstruction: {url_for("reports.accident_reconstruction_list")}.'
        )
    return (
        'I can help with report workflow, Law Lookup, paperwork guidance, forms, training, personnel, scanner fallback, and accident reconstruction. '
        'Tell me the task or describe the incident in plain language.'
    )


def _message_has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _assistant_action_for(message: str, page: dict | None = None) -> dict | None:
    """Return safe client actions for site navigation and guided form completion."""
    text = (message or '').strip().lower()
    normalized_text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    path = str((page or {}).get('path') or '')
    if not text:
        return None

    if path.startswith('/forms/') and '/fill' in path and _message_has_any(
        text,
        (
            'fill this form',
            'fill out this form',
            'help me fill',
            'ask me questions',
            'walk me through',
            'guided form',
            'complete this form',
        ),
    ):
        return {
            'type': 'form_interview',
            'message': 'I will ask the form questions one at a time and fill the matching fields on this page.',
        }

    navigation_targets = [
        (('dashboard', 'home screen', 'main menu', 'command dashboard'), 'Dashboard', url_for('dashboard.dashboard')),
        (('customize dashboard', 'dashboard settings'), 'Customize Dashboard', url_for('dashboard.customize_dashboard')),
        (('law lookup', 'legal lookup', 'look up law', 'search law', 'charges', 'statutes'), 'Law Lookup', url_for('legal.legal_lookup')),
        (('start report', 'new report', 'incident report', 'write report', 'start incident'), 'Start Report', url_for('reports.new_report')),
        (('reports center', 'all reports', 'reports page', 'report center'), 'Reports Center', url_for('reports.list_reports')),
        (('forms library', 'forms page', 'open forms', 'find form', 'forms'), 'Forms Library', url_for('forms.list_forms')),
        (('saved forms', 'saved work', 'drafts'), 'Saved Work', url_for('forms.saved_forms')),
        (('orders', 'memos', 'orders and memos', 'orders & memos', 'base orders'), 'Orders & Memos', url_for('orders.library')),
        (('training', 'roster', 'training roster', 'training menu'), 'Training', url_for('training.training_menu')),
        (('personnel', 'officers', 'manage users', 'officer profiles', 'users'), 'Personnel', url_for('auth.manage_users')),
        (('watch commander', 'watch commander hub', 'watch dashboard'), 'Watch Commander Hub', url_for('watch_commander.dashboard')),
        (('approve officers', 'assign officers', 'supervisor dashboard'), 'Approve / Assign Officers', url_for('mobile.supervisor_dashboard')),
        (('admin', 'administration', 'admin users'), 'Administration', url_for('auth.manage_users')),
        (('body cam', 'bodycam mode', 'body camera'), 'Body Cam Mode', url_for('bodycam.new_recording')),
        (('bodycam footage', 'body cam footage', 'bodycam library'), 'Bodycam Footage', url_for('bodycam.library')),
        (('narrative creator', 'narrative tool'), 'Narrative Creator', url_for('bodycam.narrative_tool')),
        (('5w', '5ws', '5 w', 'five w', 'five ws', '5w builder'), '5W Builder', url_for('bodycam.five_w_tool')),
        (('site builder', 'builder', 'builder mode'), 'Site Builder', url_for('admin.site_builder')),
        (('accident tools', 'crash tools', 'accident diagram'), 'Accident Tools', url_for('reports.accidents')),
        (('officer accident diagram', 'simple accident diagram'), 'Officer Accident Diagram', url_for('reports.officer_accident_diagram_new')),
        (('accident reconstruction', 'reconstruction tool', 'investigator reconstruction'), 'Accident Reconstruction', url_for('reports.investigator_reconstruction_new')),
        (('scanner', 'scan id', 'camera scanner', 'id scanner'), 'Mobile ID Scanner', url_for('mobile.incident_person_editor')),
        (('mobile home', 'phone home', 'mobile page', 'mobile dashboard'), 'Mobile Home', url_for('mobile.home')),
        (('stats', 'my stats', 'performance'), 'My Stats', url_for('performance.my_stats')),
    ]
    should_navigate = _message_has_any(text, ('open ', 'go to ', 'take me to ', 'navigate', 'show me ', 'pull up ', 'launch ', 'switch to '))
    short_direct_command = len(normalized_text.split()) <= 4
    if should_navigate or short_direct_command:
        for terms, label, target_url in navigation_targets:
            if _message_has_any(text, terms):
                return {'type': 'navigate', 'url': target_url, 'label': label}

    if _message_has_any(text, ('fill a form', 'fill out a form', 'complete a form')):
        return {'type': 'navigate', 'url': url_for('forms.list_forms'), 'label': 'Forms Library'}

    return None


def _check_csrf():
    token = (
        request.headers.get('X-CSRFToken')
        or (request.get_json(silent=True) or {}).get('_csrf_token')
        or ''
    )
    expected = session.get('_csrf_token', '')
    return bool(expected and hmac.compare_digest(str(token), str(expected)))


@bp.post('/api/assistant/ask')
@login_required
def assistant_ask():
    if not _check_csrf():
        return jsonify({'ok': False, 'error': 'Invalid request.'}), 403

    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    history = body.get('history') or []
    page = body.get('page') if isinstance(body.get('page'), dict) else {}

    if not message:
        return jsonify({'ok': False, 'error': 'No message provided.'}), 400

    action = _assistant_action_for(message, page)
    api_key = configured_openai_api_key()
    answer = ask_openai_with_system(message, _SYSTEM_PROMPT, api_key, history=history)
    mode = 'premium'
    if is_ai_unavailable_message(answer):
        answer = _local_assistant_reply(message)
        mode = 'local_fallback'
    if action and action.get('type') == 'navigate':
        answer = f"{answer}\n\nOpening {action.get('label')} now."
    if action and action.get('type') == 'form_interview':
        answer = action.get('message') or answer
    return jsonify({'ok': True, 'reply': answer, 'mode': mode, 'action': action})


@bp.post('/api/assistant/speak')
@login_required
def assistant_speak():
    if not _check_csrf():
        return jsonify({'ok': False, 'error': 'Invalid request.'}), 403

    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    voice = (body.get('voice') or 'coral').strip().lower()
    if voice not in _ALLOWED_VOICES:
        voice = 'coral'
    speed_name = (body.get('speed') or 'normal').strip().lower()
    speed_map = {
        'normal': 0.95,
        'fast': 1.08,
        'veryfast': 1.18,
    }
    speed = speed_map.get(speed_name, speed_map['normal'])

    if not text:
        return jsonify({'ok': False, 'error': 'No text provided.'}), 400

    api_key = configured_openai_api_key()
    audio = openai_tts(text, api_key, voice=voice, speed=speed)
    if audio:
        return Response(audio, mimetype='audio/mpeg')

    return jsonify({'ok': False, 'error': 'TTS unavailable.'}), 503


@bp.get('/api/assistant/voices')
@login_required
def assistant_voices():
    return jsonify({'voices': sorted(_ALLOWED_VOICES)})


@bp.get('/api/assistant/status')
@login_required
def assistant_status():
    if not can_manage_site(current_user):
        return jsonify({'ok': False, 'error': 'Forbidden.'}), 403
    status = openai_key_status(configured_openai_api_key())
    return jsonify({'ok': True, 'openai': status})


_SUPERVISOR_ROLES = {
    'WEBSITE_CONTROLLER',
    'WATCH_COMMANDER',
    'DESK_SGT',
    'FIELD_TRAINING_OFFICER',
    'ACCIDENT_INVESTIGATOR',
    'SRT',
    'K9',
    'ASSISTANT_OPERATIONS_OFFICER',
    'OPERATIONS_OFFICER',
    'DEPUTY_CHIEF',
    'CHIEF',
}


def _role_keys(user) -> set[str]:
    keys = set()
    role_keys = getattr(user, 'role_keys', None)
    if role_keys:
        keys.update(str(item).upper() for item in role_keys)
    role = getattr(user, 'normalized_role', None) or getattr(user, 'role', None)
    if role:
        keys.add(str(role).upper())
    return {key.replace('-', '_').replace(' ', '_') for key in keys}


def _is_supervisor() -> bool:
    return bool(getattr(current_user, 'is_authenticated', False) and (can_manage_site(current_user) or _role_keys(current_user) & _SUPERVISOR_ROLES))


def _supervisor_required_json():
    if not _is_supervisor():
        return jsonify({'ok': False, 'error': 'Supervisor access required.'}), 403
    return None


def _store_dir() -> Path:
    path = Path(current_app.instance_path) / 'wc_admin'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _files_root() -> Path:
    path = Path(current_app.instance_path) / 'wc_admin_files'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_store(name: str, default):
    path = _store_dir() / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _save_json_store(name: str, data) -> None:
    (_store_dir() / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')


def _safe_text(value, max_len=4000) -> str:
    return str(value or '').strip()[:max_len]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _counseling_text(payload: dict) -> str:
    officer_name = _safe_text(payload.get('officer_name'), 120) or 'the officer'
    counseling_type = _safe_text(payload.get('counseling_type'), 80) or 'Professional Counseling'
    category = _safe_text(payload.get('category'), 80)
    facts = _safe_text(payload.get('facts'))
    standard = _safe_text(payload.get('standard'))
    corrective_action = _safe_text(payload.get('corrective_action'))
    follow_up = _safe_text(payload.get('follow_up'))
    lines = [counseling_type, f'Officer: {officer_name}']
    if category:
        lines.append(f'Category: {category}')
    lines.extend([
        '',
        'Facts:',
        facts or 'Facts were not provided. Add specific observed conduct before final use.',
        '',
        'Expected Standard:',
        standard or 'Applicable standard was not provided. Confirm the correct order, policy, or supervisor direction before final use.',
        '',
        'Corrective Action:',
        corrective_action or 'Corrective action was not provided.',
        '',
        'Follow-Up:',
        follow_up or 'Follow-up requirements were not provided.',
        '',
        'Supervisor note: Review for accuracy and policy compliance before issuing.',
    ])
    return '\n'.join(lines)


def _award_text(payload: dict) -> str:
    officer_name = _safe_text(payload.get('officer_name'), 120) or 'the officer'
    award_type = _safe_text(payload.get('award_type'), 80) or 'Award Recommendation'
    actions = _safe_text(payload.get('actions'))
    impact = _safe_text(payload.get('impact'))
    period = _safe_text(payload.get('period'), 120)
    lines = [award_type, f'Nominee: {officer_name}']
    if period:
        lines.append(f'Period: {period}')
    lines.extend([
        '',
        'Recommended Citation:',
        f'{officer_name} is recommended for recognition for actions described by the supervisor. '
        f'{actions or "Specific actions were not provided."} '
        f'{impact or "Operational impact should be added before final submission."}',
        '',
        'Supervisor note: Verify facts, dates, and award criteria before submission.',
    ])
    return '\n'.join(lines)


def _fallback_allowed_file(filename: str) -> bool:
    return Path(filename or '').suffix.lower().lstrip('.') in {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'xls', 'xlsx', 'csv', 'txt'}


def _fallback_classify(filename: str, description: str = '') -> str:
    text = f'{filename} {description}'.lower()
    for needle, area in [
        ('accident', 'accident_investigation'),
        ('crash', 'accident_investigation'),
        ('award', 'awards'),
        ('counsel', 'counseling'),
        ('medical', 'medical'),
        ('training', 'training'),
        ('pdi', 'pdi'),
        ('police department instruction', 'pdi'),
        ('order', 'marine_corps_orders'),
        ('form', 'forms'),
        ('srt', 'srt'),
        ('k9', 'k9'),
    ]:
        if needle in text:
            return area
    return 'general'


def _file_index() -> list[dict]:
    data = _json_store('file_index.json', [])
    return data if isinstance(data, list) else []


def _save_file_index(items: list[dict]) -> None:
    _save_json_store('file_index.json', items)


@bp.get('/admin/watch-commander')
@login_required
def watch_commander_console():
    if not _is_supervisor():
        return render_template('forbidden.html', error_message='Supervisor access required.'), 403
    return redirect(url_for('watch_commander.dashboard'))


@bp.get('/admin/officer-files')
@login_required
def officer_files_console():
    if not _is_supervisor():
        return render_template('forbidden.html', error_message='Supervisor access required.'), 403
    try:
        return render_template('wc_officer_files.html', title='Officer Files')
    except TemplateNotFound:
        current_app.logger.warning('wc_officer_files.html missing; falling back to Watch Commander console.')
    return redirect(url_for('assistant.watch_commander_console'))


@bp.post('/api/admin/counseling/generate')
@login_required
def generate_counseling():
    denied = _supervisor_required_json()
    if denied:
        return denied
    return jsonify({'ok': True, 'text': _counseling_text(request.get_json(silent=True) or {})})


@bp.post('/api/admin/awards/generate')
@login_required
def generate_award():
    denied = _supervisor_required_json()
    if denied:
        return denied
    return jsonify({'ok': True, 'text': _award_text(request.get_json(silent=True) or {})})


@bp.post('/api/admin/learning/submit')
@login_required
def submit_learning():
    denied = _supervisor_required_json()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    items = _json_store('learning_pending.json', [])
    entry = {
        'id': f"learn-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        'submitted_by': getattr(current_user, 'id', None),
        'submitted_at': _utc_stamp(),
        'category': _safe_text(payload.get('category'), 80),
        'prompt': _safe_text(payload.get('prompt')),
        'approved_answer': _safe_text(payload.get('approved_answer')),
        'notes': _safe_text(payload.get('notes')),
    }
    items.append(entry)
    _save_json_store('learning_pending.json', items)
    return jsonify({'ok': True, 'entry': entry})


@bp.get('/api/admin/learning/pending')
@login_required
def pending_learning():
    denied = _supervisor_required_json()
    if denied:
        return denied
    return jsonify({'ok': True, 'entries': _json_store('learning_pending.json', [])})


@bp.post('/api/admin/learning/approve')
@login_required
def approve_learning():
    denied = _supervisor_required_json()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    entry_id = _safe_text(payload.get('id'), 120)
    pending = _json_store('learning_pending.json', [])
    approved = _json_store('learning_approved.json', [])
    match = None
    remaining = []
    for entry in pending:
        if str(entry.get('id')) == entry_id and match is None:
            match = entry
        else:
            remaining.append(entry)
    if not match:
        return jsonify({'ok': False, 'error': 'Learning entry not found.'}), 404
    match['approved_by'] = getattr(current_user, 'id', None)
    match['approved_at'] = _utc_stamp()
    approved.append(match)
    _save_json_store('learning_pending.json', remaining)
    _save_json_store('learning_approved.json', approved)
    return jsonify({'ok': True, 'entry': match})


@bp.post('/api/admin/files/upload')
@login_required
def admin_files_upload():
    denied = _supervisor_required_json()
    if denied:
        return denied
    uploads = request.files.getlist('files') or request.files.getlist('file')
    officer_id = _safe_text(request.form.get('officer_id'), 80)
    requested_area = _safe_text(request.form.get('area'), 80)
    description = _safe_text(request.form.get('description'), 1000)
    if not uploads:
        return jsonify({'ok': False, 'error': 'No files provided.'}), 400

    saved = []
    index = _file_index()
    root = _files_root()
    for upload in uploads:
        original = upload.filename or ''
        is_allowed = allowed_file(original) if allowed_file else _fallback_allowed_file(original)
        if not original or not is_allowed:
            continue
        filename = secure_filename(original)
        area = requested_area or (classify_document(filename, description) if classify_document else _fallback_classify(filename, description))
        area = re.sub(r'[^A-Za-z0-9_.-]+', '_', area or 'general').strip('._') or 'general'
        title = smart_title(filename, description) if smart_title else Path(filename).stem.replace('_', ' ').title()
        relative = build_storage_path(officer_id or 'unassigned', area, filename) if build_storage_path else str(Path(officer_id or 'unassigned') / area / filename)
        relative_path = Path(relative)
        target = (root / relative_path).resolve()
        if os.path.commonpath([str(root.resolve()), str(target)]) != str(root.resolve()):
            return jsonify({'ok': False, 'error': 'Invalid upload path.'}), 400
        target.parent.mkdir(parents=True, exist_ok=True)
        upload.save(target)
        record = {
            'id': f"file-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            'officer_id': officer_id,
            'area': area,
            'description': description,
            'title': title,
            'file_name': filename,
            'original_file_name': original,
            'rel_path': str(relative_path).replace('\\', '/'),
            'uploaded_by': getattr(current_user, 'id', None),
            'uploaded_at': _utc_stamp(),
        }
        index.append(record)
        saved.append(record)
    _save_file_index(index)
    return jsonify({'ok': True, 'files': saved})


@bp.get('/api/admin/files')
@login_required
def admin_files_list():
    denied = _supervisor_required_json()
    if denied:
        return denied
    officer_id = request.args.get('officer_id')
    area = request.args.get('area')
    items = _file_index()
    if officer_id:
        items = [item for item in items if str(item.get('officer_id')) == str(officer_id)]
    if area:
        items = [item for item in items if str(item.get('area')) == str(area)]
    return jsonify({'ok': True, 'files': items})


@bp.get('/api/admin/files/download/<path:rel_path>')
@login_required
def admin_files_download(rel_path):
    if not _is_supervisor():
        return jsonify({'ok': False, 'error': 'Supervisor access required.'}), 403
    root = _files_root().resolve()
    target = (root / rel_path).resolve()
    if os.path.commonpath([str(root), str(target)]) != str(root) or not target.exists() or not target.is_file():
        return jsonify({'ok': False, 'error': 'File not found.'}), 404
    return send_from_directory(root, str(target.relative_to(root)), as_attachment=True)
