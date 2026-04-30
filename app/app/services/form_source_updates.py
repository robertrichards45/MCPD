from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

import requests
from werkzeug.utils import secure_filename


ALLOWED_OFFICIAL_HOSTS = {
    'dso.dla.mil',
    'forms.documentservices.dla.mil',
    'www.dla.mil',
    'dla.mil',
    'www.secnav.navy.mil',
    'secnav.navy.mil',
    'www.esd.whs.mil',
    'esd.whs.mil',
}


@dataclass(frozen=True)
class FormSourceCheck:
    ok: bool
    status: str
    message: str
    downloaded: bool = False
    changed: bool = False
    new_path: str = ''
    sha256_hash: str = ''
    content_type: str = ''
    source_url: str = ''


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _safe_official_url(url: str) -> tuple[bool, str]:
    parsed = urlparse((url or '').strip())
    if parsed.scheme != 'https':
        return False, 'Official form source must be an HTTPS URL.'
    host = (parsed.hostname or '').lower()
    if host not in ALLOWED_OFFICIAL_HOSTS:
        return False, f'Host not on the official allow-list: {host or "missing"}'
    return True, ''


def _looks_like_pdf(payload: bytes, content_type: str) -> bool:
    if payload.startswith(b'%PDF-'):
        return True
    return 'application/pdf' in (content_type or '').lower() and b'<html' not in payload[:512].lower()


def check_and_update_form_source(form, storage_dir: str, *, apply_update: bool = False, timeout: int = 25) -> FormSourceCheck:
    source_url = (getattr(form, 'official_source_url', '') or '').strip()
    if not source_url:
        return FormSourceCheck(False, 'not_configured', 'No official source URL is configured for this form.')

    safe, reason = _safe_official_url(source_url)
    if not safe:
        return FormSourceCheck(False, 'blocked_url', reason, source_url=source_url)

    try:
        response = requests.get(
            source_url,
            timeout=timeout,
            allow_redirects=True,
            headers={'User-Agent': 'MCPD-Portal-FormUpdater/1.0'},
        )
    except requests.RequestException as exc:
        return FormSourceCheck(False, 'network_error', f'Could not reach official source: {exc}', source_url=source_url)

    content_type = response.headers.get('content-type', '')
    body = response.content or b''
    if response.status_code in {401, 403}:
        return FormSourceCheck(False, 'requires_login', 'Official source requires login or CAC/storefront access.', content_type=content_type, source_url=source_url)
    if response.status_code >= 400:
        return FormSourceCheck(False, 'http_error', f'Official source returned HTTP {response.status_code}.', content_type=content_type, source_url=source_url)
    if not _looks_like_pdf(body, content_type):
        marker = body[:256].decode('utf-8', errors='ignore').strip().replace('\n', ' ')
        if 'login' in marker.lower() or 'smartstore' in marker.lower() or '<html' in marker.lower():
            return FormSourceCheck(False, 'requires_login', 'Official source returned a storefront/login page instead of a PDF.', content_type=content_type, source_url=source_url)
        return FormSourceCheck(False, 'not_pdf', 'Official source did not return a PDF file.', content_type=content_type, source_url=source_url)

    digest = sha256(body).hexdigest()
    current_hash = ''
    current_path = Path(getattr(form, 'file_path', '') or '')
    if current_path.exists():
        current_hash = sha256(current_path.read_bytes()).hexdigest()
    if current_hash and current_hash == digest:
        return FormSourceCheck(True, 'current', 'The local form already matches the official source.', changed=False, sha256_hash=digest, content_type=content_type, source_url=source_url)

    if not apply_update:
        return FormSourceCheck(True, 'update_available', 'A different official PDF is available. Review/apply to replace the local form.', changed=True, sha256_hash=digest, content_type=content_type, source_url=source_url)

    target_dir = Path(storage_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    title = secure_filename(getattr(form, 'title', '') or 'official-form') or 'official-form'
    target = target_dir / f'{title}-official-{digest[:12]}.pdf'
    target.write_bytes(body)
    return FormSourceCheck(True, 'updated', 'Official PDF downloaded and applied to this form.', downloaded=True, changed=True, new_path=str(target), sha256_hash=digest, content_type=content_type, source_url=source_url)

