import hmac
import os

from flask import Blueprint, Response, g, jsonify, request, session
from flask_login import login_required

from ..services.ai_client import ask_openai_with_system, openai_tts

bp = Blueprint('assistant', __name__)

_SYSTEM_PROMPT = (
    "You are MCPD Assistant, a knowledgeable and professional AI assistant built into the Marine Corps "
    "Police Department field portal. You help officers with questions about law, policy, report writing, "
    "incident procedures, UCMJ, use of force, traffic enforcement, and general police work. "
    "Be concise, direct, and professional. When you don't know something with confidence, say so clearly. "
    "Avoid unnecessary filler phrases. Speak plainly as if briefing another officer."
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

    if not message:
        return jsonify({'ok': False, 'error': 'No message provided.'}), 400

    api_key = os.environ.get('OPENAI_API_KEY', '')
    answer = ask_openai_with_system(message, _SYSTEM_PROMPT, api_key, history=history)
    return jsonify({'ok': True, 'reply': answer})


@bp.post('/api/assistant/speak')
@login_required
def assistant_speak():
    if not _check_csrf():
        return jsonify({'ok': False, 'error': 'Invalid request.'}), 403

    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()

    if not text:
        return jsonify({'ok': False, 'error': 'No text provided.'}), 400

    api_key = os.environ.get('OPENAI_API_KEY', '')
    audio = openai_tts(text, api_key, voice='nova')
    if audio:
        return Response(audio, mimetype='audio/mpeg')

    return jsonify({'ok': False, 'error': 'TTS unavailable.'}), 503
