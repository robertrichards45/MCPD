import json
import os
from datetime import datetime, timedelta, timezone

import requests

_AI_DISABLED_MESSAGE = ''
_AI_DISABLED_UNTIL = None
_ALLOWED_VOICES = {'alloy', 'ash', 'coral', 'echo', 'fable', 'nova', 'onyx', 'shimmer', 'verse'}


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
        return 'AI authentication failed. The configured OPENAI_API_KEY is invalid. Update it in .env and restart the portal.'

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


def _disable_ai_temporarily(message, minutes=20):
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
        return 'AI is not configured. Contact admin to set OPENAI_API_KEY.'
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
    global _AI_DISABLED_MESSAGE, _AI_DISABLED_UNTIL
    api_key = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
    prompt = (prompt or '').strip()
    if not prompt:
        return 'Enter a question before using the AI assistant.'
    if not api_key:
        return 'AI is not configured. Contact admin to set OPENAI_API_KEY.'
    if _AI_DISABLED_MESSAGE and _AI_DISABLED_UNTIL and datetime.now(timezone.utc) < _AI_DISABLED_UNTIL:
        return f'{_AI_DISABLED_MESSAGE} AI search assist is temporarily disabled until the portal is restarted or the cooldown expires.'
    if _AI_DISABLED_UNTIL and datetime.now(timezone.utc) >= _AI_DISABLED_UNTIL:
        _AI_DISABLED_MESSAGE = ''
        _AI_DISABLED_UNTIL = None

    input_items = [{'role': 'system', 'content': system_prompt or 'You are MCPD Assistant.'}]
    for item in (history or [])[-10:]:
        role = str(item.get('role') or '').strip()
        content = str(item.get('content') or '').strip()
        if role in {'user', 'assistant'} and content:
            input_items.append({'role': role, 'content': content[:4000]})
    input_items.append({'role': 'user', 'content': prompt})

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {'model': os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'), 'input': input_items}
    try:
        response = requests.post('https://api.openai.com/v1/responses', headers=headers, data=json.dumps(payload), timeout=30)
    except requests.Timeout:
        return 'AI request timed out. Try again.'
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
        payload = {}
        if getattr(exc, 'response', None) is not None:
            try:
                payload = exc.response.json()
            except ValueError:
                payload = {}
        return _friendly_error_message(status_code, payload)

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
    return _extract_response_text(data) or 'AI returned no answer.'


def openai_key_status(api_key):
    value = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
    if not value:
        return {'configured': False, 'message': 'OPENAI_API_KEY is not set.'}
    return {'configured': True, 'prefix': value[:7], 'message': 'OPENAI_API_KEY is configured.'}


def openai_tts(text, api_key, voice='coral'):
    api_key = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
    text = (text or '').strip()
    voice = (voice or 'coral').strip().lower()
    if voice not in _ALLOWED_VOICES:
        voice = 'coral'
    if not api_key or not text:
        return None
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {'model': os.environ.get('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts'), 'voice': voice, 'input': text[:4000]}
    try:
        response = requests.post('https://api.openai.com/v1/audio/speech', headers=headers, data=json.dumps(payload), timeout=30)
    except requests.RequestException:
        return None
    if response.status_code >= 400:
        return None
    return response.content
