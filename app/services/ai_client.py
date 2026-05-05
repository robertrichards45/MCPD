import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

_log = logging.getLogger(__name__)

_AI_DISABLED_MESSAGE = ''
_AI_DISABLED_UNTIL = None


def configured_openai_api_key(api_key=None):
    """Return the configured OpenAI API key without exposing it to callers."""
    return (
        (api_key or '').strip()
        or os.environ.get('OPENAI_API_KEY', '').strip()
        or os.environ.get('MCPD_OPENAI_API_KEY', '').strip()
        or os.environ.get('OPENAI_KEY', '').strip()
    )


def configured_openai_model():
    """Allow Railway to override the chat model without a code deploy."""
    return (
        os.environ.get('OPENAI_MODEL', '').strip()
        or os.environ.get('MCPD_OPENAI_MODEL', '').strip()
        or 'gpt-4.1-mini'
    )


def configured_openai_tts_model():
    """Default to the broadly available, faster TTS model unless overridden."""
    return (
        os.environ.get('OPENAI_TTS_MODEL', '').strip()
        or os.environ.get('MCPD_OPENAI_TTS_MODEL', '').strip()
        or 'tts-1'
    )


def reset_openai_cooldown():
    global _AI_DISABLED_MESSAGE, _AI_DISABLED_UNTIL
    _AI_DISABLED_MESSAGE = ''
    _AI_DISABLED_UNTIL = None


def _extract_response_text(payload):
    if not isinstance(payload, dict):
        return ''

    output_items = payload.get('output') or []
    for item in output_items:
        content_items = item.get('content') or []
        for content in content_items:
            text = (content.get('text') or '').strip()
            if text:
                return text

    output_text = (payload.get('output_text') or '').strip()
    if output_text:
        return output_text

    return ''


def _extract_error_details(payload):
    if not isinstance(payload, dict):
        return None, None, None
    error = payload.get('error') or {}
    if not isinstance(error, dict):
        return None, None, None
    return (
        str(error.get('type') or '').strip() or None,
        str(error.get('code') or '').strip() or None,
        str(error.get('message') or '').strip() or None,
    )


def _friendly_error_message(status_code, payload):
    error_type, error_code, error_message = _extract_error_details(payload)

    if status_code == 401 or error_code == 'invalid_api_key':
        return 'AI authentication failed. OpenAI rejected the configured OPENAI_API_KEY. Verify the exact key value in Railway Variables or local .env, then redeploy/restart the portal.'

    if status_code == 429 and error_code == 'insufficient_quota':
        return 'AI quota has been exhausted for the configured OpenAI account. Add billing or switch to a funded API key.'

    if status_code == 429:
        return 'AI rate limit reached. Try again in a moment.'

    if status_code == 404 or error_code == 'model_not_found':
        return 'AI model access is unavailable for the configured OpenAI account. Verify the model name and account access.'

    if status_code == 403:
        return 'AI access is forbidden for the configured OpenAI account. Verify project permissions and model access.'

    if status_code:
        if error_type or error_code or error_message:
            return f'AI request failed ({status_code}). Check the server OpenAI configuration.'
        return f'AI error: {status_code}.'

    return 'AI request failed.'


def is_ai_unavailable_message(text):
    message = (text or '').strip().lower()
    if not message:
        return False
    return message.startswith(
        (
            'ai is not configured',
            'ai request failed',
            'ai error:',
            'ai request timed out',
            'ai returned',
            'ai authentication failed',
            'ai quota has been exhausted',
            'ai rate limit reached',
            'ai model access is unavailable',
            'ai access is forbidden',
            'ai search assist is temporarily disabled',
        )
    )


def openai_key_status(api_key=None):
    """Return a safe diagnostic summary for the configured OpenAI key."""
    key = configured_openai_api_key(api_key)
    model = configured_openai_model()
    if not key:
        return {
            'configured': False,
            'keyPrefix': '',
            'keyLength': 0,
            'model': model,
            'ttsModel': configured_openai_tts_model(),
            'ok': False,
            'statusCode': None,
            'errorCode': 'missing_key',
            'message': 'OPENAI_API_KEY is not visible to the running app.',
        }

    summary = {
        'configured': True,
        'keyPrefix': key[:7],
        'keyLength': len(key),
        'model': model,
        'ttsModel': configured_openai_tts_model(),
        'ok': False,
        'statusCode': None,
        'errorCode': None,
        'message': '',
    }
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'input': 'Reply with exactly: ok',
        'max_output_tokens': 8,
    }
    try:
        response = requests.post(
            'https://api.openai.com/v1/responses',
            headers=headers,
            data=json.dumps(payload),
            timeout=15,
        )
    except requests.Timeout:
        summary['message'] = 'OpenAI diagnostic request timed out.'
        return summary
    except requests.RequestException as exc:
        summary['message'] = f'OpenAI diagnostic request failed: {exc.__class__.__name__}.'
        return summary

    summary['statusCode'] = response.status_code
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code < 400:
        reset_openai_cooldown()
        summary['ok'] = True
        summary['message'] = 'OpenAI accepted the configured key.'
        return summary

    _error_type, error_code, error_message = _extract_error_details(data)
    summary['errorCode'] = error_code
    summary['message'] = error_message or _friendly_error_message(response.status_code, data)
    return summary


def _disable_ai_temporarily(message, minutes=1):
    global _AI_DISABLED_MESSAGE, _AI_DISABLED_UNTIL
    _AI_DISABLED_MESSAGE = message
    _AI_DISABLED_UNTIL = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return message


def ask_openai(prompt, api_key):
    global _AI_DISABLED_MESSAGE, _AI_DISABLED_UNTIL
    api_key = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
    prompt = (prompt or '').strip()

    if not prompt:
        return 'Enter a question before using the AI assistant.'
    if not api_key:
        return 'AI is not configured. In Railway, add OPENAI_API_KEY to the service Variables tab (not Shared Variables), then redeploy.'
    if _AI_DISABLED_MESSAGE and _AI_DISABLED_UNTIL and datetime.now(timezone.utc) < _AI_DISABLED_UNTIL:
        return f'{_AI_DISABLED_MESSAGE} AI search assist is temporarily disabled until the portal is restarted or the cooldown expires.'
    if _AI_DISABLED_UNTIL and datetime.now(timezone.utc) >= _AI_DISABLED_UNTIL:
        _AI_DISABLED_MESSAGE = ''
        _AI_DISABLED_UNTIL = None

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'gpt-4.1-mini',
        'input': [
            {
                'role': 'system',
                'content': 'You are a professional training assistant for MCPD. Answer clearly and concisely. If you are unsure, say so.',
            },
            {
                'role': 'user',
                'content': prompt,
            },
        ],
    }

    try:
        response = requests.post(
            'https://api.openai.com/v1/responses',
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
    except requests.Timeout:
        return 'AI request timed out. Try again.'
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status_code:
            payload = {}
            try:
                payload = exc.response.json() if exc.response is not None else {}
            except ValueError:
                payload = {}
            message = _friendly_error_message(status_code, payload)
            error_type, error_code, _ = _extract_error_details(payload)
            if status_code in {401, 403, 404} or error_code in {'invalid_api_key', 'model_not_found', 'insufficient_quota'} or error_type in {'invalid_request_error'}:
                return _disable_ai_temporarily(message)
            return message
        return 'AI request failed.'

    try:
        data = response.json()
    except ValueError:
        return 'AI returned an invalid response.'

    if response.status_code >= 400:
        message = _friendly_error_message(response.status_code, data)
        error_type, error_code, _ = _extract_error_details(data)
        if response.status_code in {401, 403, 404} or error_code in {'invalid_api_key', 'model_not_found', 'insufficient_quota'} or error_type in {'invalid_request_error'}:
            return _disable_ai_temporarily(message)
        return message

    answer = _extract_response_text(data)
    if answer:
        return answer
    return 'AI returned no answer.'


def ask_openai_with_system(prompt, system_prompt, api_key, history=None):
    """Like ask_openai but accepts a custom system prompt and conversation history.

    history is a list of {"role": "user"|"assistant", "content": "..."} dicts.
    Returns the assistant's reply string (may be an error message).
    """
    global _AI_DISABLED_MESSAGE, _AI_DISABLED_UNTIL
    api_key = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
    prompt = (prompt or '').strip()

    if not prompt:
        return 'Enter a question before using the AI assistant.'
    if not api_key:
        return 'AI is not configured. In Railway, add OPENAI_API_KEY to the service Variables tab (not Shared Variables), then redeploy.'
    if _AI_DISABLED_MESSAGE and _AI_DISABLED_UNTIL and datetime.now(timezone.utc) < _AI_DISABLED_UNTIL:
        return f'{_AI_DISABLED_MESSAGE} AI search assist is temporarily disabled until the portal is restarted or the cooldown expires.'
    if _AI_DISABLED_UNTIL and datetime.now(timezone.utc) >= _AI_DISABLED_UNTIL:
        _AI_DISABLED_MESSAGE = ''
        _AI_DISABLED_UNTIL = None

    input_messages = [{'role': 'system', 'content': system_prompt or 'You are a helpful assistant.'}]
    for msg in (history or []):
        role = msg.get('role', '')
        content = (msg.get('content') or '').strip()
        if role in ('user', 'assistant') and content:
            input_messages.append({'role': role, 'content': content})
    input_messages.append({'role': 'user', 'content': prompt})

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'gpt-4.1-mini',
        'input': input_messages,
    }

    try:
        response = requests.post(
            'https://api.openai.com/v1/responses',
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
    except requests.Timeout:
        return 'AI request timed out. Try again.'
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status_code:
            resp_payload = {}
            try:
                resp_payload = exc.response.json() if exc.response is not None else {}
            except ValueError:
                pass
            message = _friendly_error_message(status_code, resp_payload)
            error_type, error_code, _ = _extract_error_details(resp_payload)
            if status_code in {401, 403, 404} or error_code in {'invalid_api_key', 'model_not_found', 'insufficient_quota'} or error_type in {'invalid_request_error'}:
                return _disable_ai_temporarily(message)
            return message
        return 'AI request failed.'

    try:
        data = response.json()
    except ValueError:
        return 'AI returned an invalid response.'

    if response.status_code >= 400:
        message = _friendly_error_message(response.status_code, data)
        error_type, error_code, _ = _extract_error_details(data)
        if response.status_code in {401, 403, 404} or error_code in {'invalid_api_key', 'model_not_found', 'insufficient_quota'} or error_type in {'invalid_request_error'}:
            return _disable_ai_temporarily(message)
        return message

    answer = _extract_response_text(data)
    if answer:
        return answer
    return 'AI returned no answer.'


_ALLOWED_VOICES = {'alloy', 'ash', 'coral', 'echo', 'fable', 'nova', 'onyx', 'shimmer', 'verse'}


def openai_tts(text, api_key, voice='coral'):
    """Call OpenAI TTS (tts-1-hd for higher quality) and return raw audio bytes (MP3), or None on failure."""
    api_key = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
    text = (text or '').strip()
    if not text or not api_key:
        return None

    # Sanitise voice — fall back to coral if caller passes an unknown value
    if voice not in _ALLOWED_VOICES:
        voice = 'coral'

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'tts-1-hd',   # higher-quality model — noticeably more natural
        'input': text[:4096],
        'voice': voice,
    }

    try:
        response = requests.post(
            'https://api.openai.com/v1/audio/speech',
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        if response.status_code == 200:
            return response.content
        _log.warning('TTS request failed: HTTP %s', response.status_code)
    except Exception as exc:
        _log.warning('TTS request error: %s', exc)
    return None
