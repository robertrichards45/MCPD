import hmac
import json
import os
import re
from datetime import datetime

from flask import Blueprint, Response, g, jsonify, request, session, url_for
from flask_login import current_user, login_required

from ..permissions import can_manage_site
from ..services.ai_client import _ALLOWED_VOICES, ask_openai_with_system, is_ai_unavailable_message, openai_key_status, openai_tts

bp = Blueprint('assistant', __name__)

_SYSTEM_PROMPT = (
    "You are MCPD Assistant, a knowledgeable and professional AI assistant built into the Marine Corps "
    "Police Department field portal. You help officers with questions about law, policy, report writing, "
    "incident procedures, UCMJ, use of force, traffic enforcement, and general police work. "
    "Be concise, direct, and professional. When you don't know something with confidence, say so clearly. "
    "Avoid unnecessary filler phrases. Speak plainly as if briefing another officer."
)

_RADIO_SYSTEM_PROMPT = (
    "You are MCPD Assistant in radio mode. Respond like a professional field communications assistant. "
    "Use short, clear, command-style sentences. Keep responses brief. Do not use filler. "
    "Address the officer by their role, call sign, or unit label when provided. "
    "For navigation or workflow questions, give the next action first. For report or legal questions, give concise guidance and tell the officer to verify facts and policy. "
    "Do not invent facts, charges, evidence, statements, or policy."
)


def _safe_user_context():
    if not getattr(current_user, 'is_authenticated', False):
        return ''
    pieces = []
    display_name = getattr(current_user, 'display_name', '') or getattr(current_user, 'username', '') or ''
    role_label = getattr(current_user, 'role_label', '') or getattr(current_user, 'role', '') or ''
    officer_number = getattr(current_user, 'officer_number', '') or getattr(current_user, 'badge_employee_id', '') or ''
    section_unit = getattr(current_user, 'section_unit', '') or ''
    if display_name:
        pieces.append(f'Officer name/display: {display_name}')
    if role_label:
        pieces.append(f'Officer role: {role_label}')
    if officer_number:
        pieces.append(f'Officer/unit identifier: {officer_number}')
    if section_unit:
        pieces.append(f'Section/unit: {section_unit}')
    return '; '.join(pieces)


def _extract_spoken_unit_label(message: str) -> str:
    text = (message or '').strip()
    patterns = [
        r'\b(unit\s*[0-9A-Za-z-]{1,10})\b',
        r'\b(patrol\s*[0-9A-Za-z-]{1,10})\b',
        r'\b(post\s*[0-9A-Za-z-]{1,10})\b',
        r'\b(watch\s+commander)\b',
        r'\b(desk\s+sergeant|desk\s+sgt|desk)\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return ' '.join(match.group(1).split()).title()
    return ''


def _build_radio_prompt(message: str) -> str:
    user_context = _safe_user_context()
    spoken_unit = _extract_spoken_unit_label(message)
    context_parts = []
    if user_context:
        context_parts.append('Logged-in officer context: ' + user_context + '.')
    if spoken_unit:
        context_parts.append('Use this call sign/unit label when appropriate: ' + spoken_unit + '.')
    if context_parts:
        return _RADIO_SYSTEM_PROMPT + ' ' + ' '.join(context_parts)
    return _RADIO_SYSTEM_PROMPT


def _local_assistant_reply(message: str) -> str:
    text = (message or '').strip().lower()
    if not text:
        return 'Tell me what you need help with, such as starting a report, finding paperwork, searching law, or opening forms.'
    if any(term in text for term in ('start report', 'start a report', 'new report', 'incident report', 'write report', 'start a call')):
        return ('To start a report, open Start Report and work through Parties, Facts, Narrative, Paperwork, and Review. '
                f'Start here: {url_for("reports.new_report")}. On mobile, use {url_for("mobile.incident_start")}.')
    if any(term in text for term in ('law', 'charge', 'statute', 'ucmj', 'federal', 'georgia', 'order applies')):
        return ('Use Law Lookup in plain language. Describe what happened, who was involved, where it happened, and whether it was on base. '
                f'Open Law Lookup: {url_for("legal.legal_lookup")}. Verify final charge selection with supervisor/legal review.')
    if any(term in text for term in ('paperwork', 'forms needed', 'what forms', 'navigator', 'packet')):
        return ('Use the Paperwork Navigator for required and likely paperwork. Select the call type, confirm the facts, then add only the forms actually used. '
                f'Open Navigator: {url_for("reference.incident_paperwork_guide")}.')
    if any(term in text for term in ('form', 'pdf', 'statement', 'domestic supplemental', 'stat sheet')):
        return ('Open Forms Library, choose the official form, fill only fields shown on the source PDF, then preview before download or email. '
                f'Open Forms: {url_for("forms.list_forms")}.')
    if any(term in text for term in ('training', 'roster', 'sign training', 'qualification')):
        return ('Open Training to view assigned rosters, sign your own line, and track completions. '
                f'Open Training: {url_for("training.training_menu")}.')
    if any(term in text for term in ('personnel', 'officer', 'watch', 'shift', 'role', 'installation')):
        return ('Personnel tools let authorized users edit officer profiles, roles, installation, shift, and watch assignments. '
                f'Open Personnel: {url_for("auth.manage_users")}.')
    if any(term in text for term in ('scanner', 'scan id', 'license', 'driver license', 'camera')):
        return ('For ID scanning, use the mobile person editor. Live camera scanning requires browser camera support and HTTPS on phones; '
                'manual entry and paste/photo fallback should remain available so the report flow is not blocked.')
    if any(term in text for term in ('accident', 'crash', 'diagram', 'reconstruction')):
        return ('Use Accident Reconstruction under Reports for crash diagrams, measurements, vehicles, media, timeline, and export. '
                f'Open Accident Reconstruction: {url_for("reports.accident_reconstruction_list")}.')
    return ('I can help with report workflow, Law Lookup, paperwork guidance, forms, training, personnel, scanner fallback, and accident reconstruction. '
            'Tell me the task or describe the incident in plain language.')


def _check_csrf():
    token = request.headers.get('X-CSRFToken') or (request.get_json(silent=True) or {}).get('_csrf_token') or ''
    expected = session.get('_csrf_token', '')
    return bool(expected and hmac.compare_digest(str(token), str(expected)))


def _admin_store_path(filename):
    base = os.path.join(os.getcwd(), 'instance', 'wc_admin')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename)


def _load_json_store(filename, default):
    path = _admin_store_path(filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return default


def _save_json_store(filename, data):
    path = _admin_store_path(filename)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2)


def _is_supervisor():
    role = (getattr(current_user, 'normalized_role', '') or getattr(current_user, 'role', '') or '').upper()
    return role in {'WEBSITE_CONTROLLER', 'WATCH_COMMANDER', 'DESK_SGT', 'FIELD_TRAINING_OFFICER'} or can_manage_site(current_user)


def _require_supervisor_json():
    if not _is_supervisor():
        return jsonify({'ok': False, 'error': 'Supervisor access required.'}), 403
    return None


def _build_counseling_text(data):
    officer = data.get('officer_name') or 'the officer'
    ctype = data.get('counseling_type') or 'Performance Counseling'
    category = data.get('category') or 'General'
    facts = data.get('facts') or 'No facts entered.'
    standard = data.get('standard') or 'Officer is expected to comply with MCPD standards, post orders, lawful instructions, and professional conduct requirements.'
    corrective = data.get('corrective_action') or 'Officer will correct the deficiency immediately and comply with all future instructions and standards.'
    followup = data.get('follow_up') or 'Supervisor will monitor future performance and document additional issues if necessary.'
    return (
        f'{ctype}\n\n'
        f'Officer: {officer}\n'
        f'Category: {category}\n'
        f'Date: {datetime.utcnow().strftime("%Y-%m-%d")}\n\n'
        f'Facts/Reason for Counseling:\n{facts}\n\n'
        f'Standard/Expectation:\n{standard}\n\n'
        f'Corrective Action/Plan:\n{corrective}\n\n'
        f'Follow-Up:\n{followup}\n\n'
        'This counseling documents the supervisor guidance provided and does not replace any required LER, HR, command, or administrative action when applicable.'
    )


def _build_award_text(data):
    officer = data.get('officer_name') or 'the officer'
    award_type = data.get('award_type') or 'On-the-Spot Cash Award'
    impact = data.get('impact') or 'positively impacted department operations and mission readiness'
    actions = data.get('actions') or 'performed duties above the expected standard'
    period = data.get('period') or 'the reporting period'
    return (
        f'{award_type} Recommendation\n\n'
        f'Nominee: {officer}\n'
        f'Period: {period}\n\n'
        f'Recommended Narrative:\nDuring {period}, {officer} {actions}. These actions {impact}. '
        'The officer demonstrated initiative, professionalism, and commitment to mission accomplishment. '
        f'Recommend approval of a {award_type.lower()} in recognition of this contribution.'
    )


@bp.post('/api/assistant/ask')
@login_required
def assistant_ask():
    if not _check_csrf():
        return jsonify({'ok': False, 'error': 'Invalid request.'}), 403
    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    history = body.get('history') or []
    voice_mode = (body.get('voice') or '').strip().lower()
    if not message:
        return jsonify({'ok': False, 'error': 'No message provided.'}), 400
    api_key = os.environ.get('OPENAI_API_KEY', '')
    system_prompt = _build_radio_prompt(message) if voice_mode == 'dispatcher' else _SYSTEM_PROMPT
    answer = ask_openai_with_system(message, system_prompt, api_key, history=history)
    mode = 'premium_radio_unit_aware' if voice_mode == 'dispatcher' else 'premium'
    if is_ai_unavailable_message(answer):
        answer = _local_assistant_reply(message)
        mode = 'local_fallback'
    return jsonify({'ok': True, 'reply': answer, 'mode': mode})


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
    if not text:
        return jsonify({'ok': False, 'error': 'No text provided.'}), 400
    api_key = os.environ.get('OPENAI_API_KEY', '')
    audio = openai_tts(text, api_key, voice=voice)
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
    status = openai_key_status(os.environ.get('OPENAI_API_KEY', ''))
    return jsonify({'ok': True, 'openai': status})


@bp.post('/api/admin/narrative-learning/submit')
@login_required
def submit_narrative_learning():
    body = request.get_json(silent=True) or {}
    items = _load_json_store('narrative_learning_pending.json', [])
    entry = {
        'id': f'nl-{int(datetime.utcnow().timestamp())}-{len(items)+1}',
        'incidentType': body.get('incidentType', 'general'),
        'original': body.get('original', ''),
        'edited': body.get('edited', ''),
        'submittedBy': getattr(current_user, 'username', 'unknown'),
        'status': 'pending',
        'createdAt': datetime.utcnow().isoformat(),
    }
    items.insert(0, entry)
    _save_json_store('narrative_learning_pending.json', items[:200])
    return jsonify({'ok': True, 'entry': entry})


@bp.get('/api/admin/narrative-learning/pending')
@login_required
def list_narrative_learning_pending():
    denied = _require_supervisor_json()
    if denied:
        return denied
    return jsonify({'ok': True, 'items': _load_json_store('narrative_learning_pending.json', [])})


@bp.post('/api/admin/narrative-learning/approve')
@login_required
def approve_narrative_learning():
    denied = _require_supervisor_json()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    entry_id = body.get('id')
    pending = _load_json_store('narrative_learning_pending.json', [])
    approved = _load_json_store('narrative_learning_approved.json', [])
    remaining = []
    approved_entry = None
    for item in pending:
        if item.get('id') == entry_id:
            approved_entry = dict(item)
            approved_entry['status'] = 'approved'
            approved_entry['approvedBy'] = getattr(current_user, 'username', 'unknown')
            approved_entry['approvedAt'] = datetime.utcnow().isoformat()
        else:
            remaining.append(item)
    if not approved_entry:
        return jsonify({'ok': False, 'error': 'Entry not found.'}), 404
    approved.insert(0, approved_entry)
    _save_json_store('narrative_learning_pending.json', remaining)
    _save_json_store('narrative_learning_approved.json', approved[:200])
    return jsonify({'ok': True, 'entry': approved_entry})


@bp.post('/api/admin/counseling/generate')
@login_required
def generate_counseling():
    denied = _require_supervisor_json()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    text = _build_counseling_text(body)
    records = _load_json_store('counseling_records.json', [])
    record = {
        'id': f'counseling-{int(datetime.utcnow().timestamp())}-{len(records)+1}',
        'officerName': body.get('officer_name', ''),
        'type': body.get('counseling_type', ''),
        'category': body.get('category', ''),
        'generatedText': text,
        'createdBy': getattr(current_user, 'username', 'unknown'),
        'createdAt': datetime.utcnow().isoformat(),
    }
    records.insert(0, record)
    _save_json_store('counseling_records.json', records[:500])
    return jsonify({'ok': True, 'record': record, 'text': text})


@bp.post('/api/admin/awards/generate')
@login_required
def generate_award():
    denied = _require_supervisor_json()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    text = _build_award_text(body)
    records = _load_json_store('award_records.json', [])
    record = {
        'id': f'award-{int(datetime.utcnow().timestamp())}-{len(records)+1}',
        'officerName': body.get('officer_name', ''),
        'awardType': body.get('award_type', ''),
        'generatedText': text,
        'createdBy': getattr(current_user, 'username', 'unknown'),
        'createdAt': datetime.utcnow().isoformat(),
    }
    records.insert(0, record)
    _save_json_store('award_records.json', records[:500])
    return jsonify({'ok': True, 'record': record, 'text': text})
