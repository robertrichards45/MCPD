import csv
import io
import json
import re
from copy import deepcopy
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

bp = Blueprint('credit_simulator', __name__, url_prefix='/private/credit-simulator')

OWNER_EMAIL = 'robertrichards45@gmail.com'
ALLOWED_EXTENSIONS = {'json', 'csv', 'txt', 'pdf'}
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


def _authorized():
    email = (getattr(current_user, 'email', '') or '').strip().lower()
    username = (getattr(current_user, 'username', '') or '').strip().lower()
    return email == OWNER_EMAIL or username in {'robertrichards45', 'robert.richards'}


def _require_owner():
    if not _authorized():
        abort(403, description='This private credit simulator is restricted to the site owner.')


def _number(value, default=0.0):
    try:
        return float(str(value).replace('$', '').replace(',', '').strip())
    except (TypeError, ValueError):
        return default


def _normalize_account(row):
    kind = str(row.get('type') or row.get('account_type') or 'revolving').strip().lower()
    status = str(row.get('status') or 'open').strip().lower()
    return {
        'id': str(row.get('id') or row.get('account_number') or row.get('name') or f"acct-{abs(hash(json.dumps(row, sort_keys=True, default=str)))}")[-40:],
        'name': str(row.get('name') or row.get('creditor') or row.get('lender') or 'Account')[:120],
        'type': kind,
        'balance': max(0, _number(row.get('balance'))),
        'limit': max(0, _number(row.get('limit') or row.get('credit_limit'))),
        'original_balance': max(0, _number(row.get('original_balance') or row.get('high_balance'))),
        'monthly_payment': max(0, _number(row.get('monthly_payment') or row.get('payment'))),
        'age_months': max(0, int(_number(row.get('age_months'), 0))),
        'late30': max(0, int(_number(row.get('late30'), 0))),
        'late60': max(0, int(_number(row.get('late60'), 0))),
        'late90': max(0, int(_number(row.get('late90'), 0))),
        'collection': bool(row.get('collection', False)),
        'chargeoff': bool(row.get('chargeoff', False)),
        'authorized_user': bool(row.get('authorized_user', False)),
        'status': status,
        'opened_months_ago': max(0, int(_number(row.get('opened_months_ago') or row.get('age_months'), 0))),
    }


def _parse_json(raw):
    payload = json.loads(raw.decode('utf-8'))
    if isinstance(payload, list):
        accounts = payload
        meta = {}
    else:
        accounts = payload.get('accounts') or payload.get('tradelines') or []
        meta = payload
    return {
        'baseline_score': int(_number(meta.get('score') or meta.get('baseline_score'), 600)),
        'inquiries': int(_number(meta.get('inquiries'), 0)),
        'accounts': [_normalize_account(row) for row in accounts if isinstance(row, dict)],
    }


def _parse_csv(raw):
    text = raw.decode('utf-8-sig', errors='replace')
    rows = list(csv.DictReader(io.StringIO(text)))
    return {'baseline_score': 600, 'inquiries': 0, 'accounts': [_normalize_account(row) for row in rows]}


def _parse_text(raw):
    text = raw.decode('utf-8', errors='replace')
    accounts = []
    pattern = re.compile(r'(?P<name>[A-Za-z0-9 &.-]{3,80})\s+balance[:\s$]+(?P<balance>[\d,]+(?:\.\d{2})?)', re.I)
    for match in pattern.finditer(text):
        accounts.append(_normalize_account({'name': match.group('name').strip(), 'balance': match.group('balance')}))
    return {'baseline_score': 600, 'inquiries': 0, 'accounts': accounts}


def _parse_pdf(raw):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        text = '\n'.join((page.extract_text() or '') for page in reader.pages)
        return _parse_text(text.encode('utf-8'))
    except Exception as exc:
        raise ValueError('This PDF could not be read automatically. Export the report as JSON/CSV or use manual entry.') from exc


@bp.get('/')
@login_required
def index():
    _require_owner()
    return render_template('credit_simulator/index.html')


@bp.post('/api/import')
@login_required
def import_report():
    _require_owner()
    uploaded = request.files.get('report')
    if not uploaded or not uploaded.filename:
        return jsonify({'error': 'Choose a credit-report file.'}), 400
    filename = secure_filename(uploaded.filename)
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Use PDF, JSON, CSV, or TXT.'}), 400
    raw = uploaded.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        return jsonify({'error': 'File exceeds the 12 MB limit.'}), 413
    try:
        if extension == 'json':
            profile = _parse_json(raw)
        elif extension == 'csv':
            profile = _parse_csv(raw)
        elif extension == 'pdf':
            profile = _parse_pdf(raw)
        else:
            profile = _parse_text(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        return jsonify({'error': str(exc)}), 400
    profile['imported_at'] = datetime.now(timezone.utc).isoformat()
    profile['source_filename'] = filename
    return jsonify(profile)


@bp.post('/api/run')
@login_required
def run_scenarios():
    _require_owner()
    payload = request.get_json(silent=True) or {}
    baseline = payload.get('baseline') or {}
    scenarios = payload.get('scenarios') or []
    if not isinstance(scenarios, list) or len(scenarios) > 500:
        return jsonify({'error': 'Run between 1 and 500 scenarios per batch.'}), 400
    return jsonify({'baseline': baseline, 'scenarios': scenarios, 'engine': 'credit-sim-v1-transparent'})
