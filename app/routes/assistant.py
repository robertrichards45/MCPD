import hmac
import os
import re

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
    """Build a small, non-sensitive context block from the logged-in portal user."""
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
    """Detect simple spoken unit labels such as Unit 2, Unit 12, Desk, or Watch Commander."""
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
