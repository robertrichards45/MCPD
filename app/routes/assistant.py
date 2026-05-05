import hmac
import os

from flask import Blueprint, Response, g, jsonify, request, session, url_for
from flask_login import current_user, login_required

from ..permissions import can_manage_site
from ..services.ai_client import _ALLOWED_VOICES, ask_openai_with_system, is_ai_unavailable_message, openai_key_status, openai_tts

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
        (('dashboard', 'home screen', 'main menu'), 'Dashboard', url_for('dashboard.dashboard')),
        (('law lookup', 'legal lookup', 'look up law', 'search law', 'charges'), 'Law Lookup', url_for('legal.legal_lookup')),
        (('start report', 'new report', 'incident report', 'write report'), 'Start Report', url_for('reports.new_report')),
        (('reports center', 'all reports', 'reports page'), 'Reports Center', url_for('reports.list_reports')),
        (('forms library', 'forms page', 'open forms', 'find form'), 'Forms Library', url_for('forms.list_forms')),
        (('saved forms', 'saved work'), 'Saved Work', url_for('forms.saved_forms')),
        (('orders', 'memos', 'orders and memos', 'orders & memos'), 'Orders & Memos', url_for('orders.library')),
        (('training', 'roster', 'training roster'), 'Training', url_for('training.training_menu')),
        (('personnel', 'officers', 'manage users', 'officer profiles'), 'Personnel', url_for('auth.manage_users')),
        (('accident tools', 'crash tools', 'accident diagram'), 'Accident Tools', url_for('reports.accidents')),
        (('mobile home', 'phone home', 'mobile page'), 'Mobile Home', url_for('mobile.home')),
    ]
    if _message_has_any(text, ('open ', 'go to ', 'take me to ', 'navigate', 'show me ', 'pull up ', 'launch ')):
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
    api_key = os.environ.get('OPENAI_API_KEY', '')
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
