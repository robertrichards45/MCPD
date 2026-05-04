import secrets
import re
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    AuditLog,
    EnrollmentCode,
    INSTALLATION_LABELS,
    ROLE_LABELS,
    ROLE_DESK_SGT,
    ROLE_FIELD_TRAINING,
    ROLE_PATROL_OFFICER,
    ROLE_WEBSITE_CONTROLLER,
    ROLE_WATCH_COMMANDER,
    USMC_INSTALLATIONS,
    User,
)
from ..permissions import (
    assignable_roles,
    can_manage_site,
    can_manage_team,
    can_manage_user,
    can_view_user,
    effective_role,
    is_site_controller,
    is_watch_commander,
    watch_commander_scope_id,
)

bp = Blueprint('auth', __name__)

_login_attempts = {}


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _request_prefers_mobile_home() -> bool:
    user_agent = str(getattr(request, 'user_agent', '') or '')
    blob = ' '.join(
        [
            user_agent,
            str(request.headers.get('User-Agent', '') or ''),
            str(request.headers.get('Sec-CH-UA-Mobile', '') or ''),
        ]
    ).lower()
    return any(token in blob for token in ('iphone', 'android', 'mobile', 'ipad'))


def _safe_audit(actor_id=None, action='', details=None):
    try:
        db.session.add(AuditLog(actor_id=actor_id, action=action, details=details))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _commit_or_rollback():
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def _extract_cac_common_name(raw_value):
    value = (raw_value or '').strip()
    if not value:
        return ''
    if '=' in value and ',' in value:
        for part in [item.strip() for item in value.split(',')]:
            if part.upper().startswith('CN='):
                return part.split('=', 1)[1].strip()
    return value


def _normalize_cac_identity(raw_value):
    value = _extract_cac_common_name(raw_value)
    if not value:
        return ''
    if '\\' in value:
        value = value.split('\\')[-1]
    if '@' in value:
        value = value.split('@')[0]
    return value.strip()


def _display_name_from_cac(raw_name, raw_username):
    explicit_name = (raw_name or '').strip()
    if explicit_name:
        return explicit_name

    common_name = _extract_cac_common_name(raw_username)
    if not common_name:
        return None

    parts = [part for part in common_name.split('.') if part]
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    if not parts:
        return common_name
    return ' '.join(parts)


def _first_header_value(header_names):
    for header_name in header_names:
        value = request.headers.get(header_name, '')
        if value and value.strip():
            return header_name, value.strip()
    return '', ''


def _cac_header_snapshot():
    username_headers = current_app.config.get('CAC_USERNAME_HEADERS') or [
        current_app.config.get('CAC_USERNAME_HEADER', 'X-Authenticated-User')
    ]
    name_headers = current_app.config.get('CAC_NAME_HEADERS') or [
        current_app.config.get('CAC_NAME_HEADER', 'X-Authenticated-Name')
    ]
    matched_username_header, raw_username = _first_header_value(username_headers)
    matched_name_header, raw_name = _first_header_value(name_headers)
    return {
        'username_headers_checked': username_headers,
        'name_headers_checked': name_headers,
        'matched_username_header': matched_username_header or None,
        'matched_name_header': matched_name_header or None,
        'raw_username': raw_username or None,
        'raw_name': raw_name or None,
        'normalized_username': _normalize_cac_identity(raw_username) or None,
        'available_candidate_headers': {
            key: value
            for key, value in request.headers.items()
            if key in set(username_headers + name_headers)
        },
    }


def _resolve_post_login_redirect():
    candidate = (request.form.get('next') or request.args.get('next') or '').strip()
    if not candidate:
        return url_for('mobile.home') if _request_prefers_mobile_home() else url_for('dashboard.dashboard')

    target = urlsplit(candidate)
    if target.scheme or target.netloc:
        return url_for('mobile.home') if _request_prefers_mobile_home() else url_for('dashboard.dashboard')
    if not candidate.startswith('/'):
        return url_for('mobile.home') if _request_prefers_mobile_home() else url_for('dashboard.dashboard')
    return candidate


def _render_landing(**context):
    context.setdefault('next_url', (request.form.get('next') or request.args.get('next') or '').strip())
    if current_app.config.get('CAC_AUTH_ENABLED'):
        context.setdefault('cac_portal_url', _preferred_cac_portal_url())
    return render_template('landing.html', **context)


def _render_register_page(**context):
    context.setdefault('next_url', (request.form.get('next') or request.args.get('next') or '').strip())
    context.setdefault('installations', USMC_INSTALLATIONS)
    return render_template('register.html', **context)


def _render_name_login_page(**context):
    context.setdefault('next_url', (request.form.get('next') or request.args.get('next') or '').strip())
    return render_template('login_name.html', **context)


def _render_cac_start_page(**context):
    context.setdefault('next_url', (request.form.get('next') or request.args.get('next') or '').strip())
    context.setdefault('cac_context', _cac_request_identity_context())
    return render_template('cac_start.html', **context)


def _render_account_create_page(**context):
    context.setdefault('next_url', (request.form.get('next') or request.args.get('next') or '').strip())
    context.setdefault('cac_context', _cac_request_identity_context())
    return render_template('account_create_cac.html', **context)


def _render_account_link_cac_page(**context):
    context.setdefault('next_url', (request.form.get('next') or request.args.get('next') or '').strip())
    context.setdefault('cac_context', _cac_request_identity_context())
    return render_template('account_link_cac.html', **context)


def _normalize_edipi(value):
    return re.sub(r'\D+', '', (value or '').strip())


def _normalize_officer_number(value):
    return (value or '').strip().upper()


def _normalize_username(value):
    return (value or '').strip().lower()


def _user_by_username(username, *, active_only=False):
    normalized = _normalize_username(username)
    if not normalized:
        return None
    query = User.query.filter(func.lower(User.username) == normalized)
    if active_only:
        query = query.filter(User.active.is_(True))
    return query.first()


def _username_exists(username, *, exclude_user_id=None):
    normalized = _normalize_username(username)
    if not normalized:
        return False
    query = User.query.filter(func.lower(User.username) == normalized)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def _sync_user_name_fields(user, first_name, last_name):
    user.first_name = first_name or None
    user.last_name = last_name or None
    full_name = ' '.join(part for part in [user.first_name, user.last_name] if part)
    user.name = full_name or None


def _available_supervisors():
    query = User.query.filter(User.active.is_(True))
    if is_site_controller(current_user):
        query = query.filter(User.role == ROLE_WATCH_COMMANDER)
    elif is_watch_commander(current_user):
        query = query.filter(User.id == current_user.id)
    else:
        query = query.filter(User.id == current_user.id)
    return query.order_by(User.first_name, User.last_name, User.username).all()


def _visible_users_query():
    query = User.query.filter_by(active=True)
    if is_site_controller(current_user):
        return query
    if is_watch_commander(current_user):
        scope_id = watch_commander_scope_id(current_user)
        return query.filter((User.supervisor_id == scope_id) | (User.id == scope_id))
    return query.filter_by(id=current_user.id)


def _supervisor_from_form():
    supervisor_id = request.form.get('supervisor_id', '').strip()
    if is_watch_commander(current_user):
        return db.session.get(User, watch_commander_scope_id(current_user))
    if not supervisor_id:
        return None
    try:
        supervisor_id_int = int(supervisor_id)
    except ValueError:
        raise ValueError('Supervisor selection is invalid.')
    supervisor = db.session.get(User, supervisor_id_int)
    if supervisor and not can_view_user(current_user, supervisor):
        raise ValueError('Supervisor selection is outside your command scope.')
    return supervisor


def _installation_from_form(target=None, *, allow_no_change=False):
    raw = request.form.get('installation', '').strip()
    if allow_no_change and not raw:
        return None
    valid_keys = {key for key, _ in USMC_INSTALLATIONS}
    if is_watch_commander(current_user):
        return current_user.installation
    if raw and raw in valid_keys:
        return raw
    return target.installation if target else None


def _apply_personnel_edit(target):
    role = request.form.get('role', '').strip() or target.normalized_role
    if role not in assignable_roles(current_user):
        raise ValueError('You cannot assign that role.')
    supervisor = _supervisor_from_form()
    installation = _installation_from_form(target, allow_no_change=True)

    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    if first_name or last_name:
        _sync_user_name_fields(target, first_name, last_name)
    target.display_name_override = request.form.get('display_name', '').strip() or None
    target.email = request.form.get('email', '').strip().lower() or None
    target.phone_number = request.form.get('phone_number', '').strip() or None
    target.address = request.form.get('address', '').strip() or None
    target.officer_number = _normalize_officer_number(request.form.get('officer_number', '')) or None
    target.badge_employee_id = request.form.get('badge_employee_id', '').strip() or None
    target.section_unit = request.form.get('section_unit', '').strip() or None
    target.role = role
    target.supervisor_id = supervisor.id if supervisor else None
    target.can_grade_cleoc_reports = request.form.get('can_grade_cleoc_reports') == '1'
    if 'active' in request.form:
        target.active = request.form.get('active') == '1'
    if installation:
        target.installation = installation

    if can_manage_site(current_user):
        edipi = _normalize_edipi(request.form.get('edipi', '')) or None
        if edipi and len(edipi) != 10:
            raise ValueError('EDIPI must be a 10-digit number.')
        if edipi and User.query.filter(User.edipi == edipi, User.id != target.id).first():
            raise ValueError('EDIPI is already assigned to another user.')
        target.edipi = edipi

    if target.email and User.query.filter(User.email == target.email, User.id != target.id).first():
        raise ValueError('Email is already assigned to another user.')
    if target.officer_number and User.query.filter(User.officer_number == target.officer_number, User.id != target.id).first():
        raise ValueError('Officer number is already assigned to another user.')


def _pending_accounts_query():
    query = User.query.filter_by(pending_approval=True, active=False)
    if is_site_controller(current_user):
        return query
    # Watch Commanders only see pending accounts from their own installation
    return query.filter_by(installation=current_user.installation)


def _cac_request_debug_context():
    forwarded_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower().startswith('x-forwarded-')
    }


def _cac_request_identity_context():
    verify_header = current_app.config.get('CAC_VERIFY_HEADER', 'X-CAC-VERIFY')
    identifier_header = current_app.config.get('CAC_IDENTIFIER_HEADER', 'X-CAC-IDENTIFIER')
    subject_header = current_app.config.get('CAC_SUBJECT_DN_HEADER', 'X-CAC-SUBJECT-DN')
    issuer_header = current_app.config.get('CAC_ISSUER_DN_HEADER', 'X-CAC-ISSUER-DN')
    serial_header = current_app.config.get('CAC_SERIAL_HEADER', 'X-CAC-SERIAL')
    cn_header = current_app.config.get('CAC_CN_HEADER', 'X-CAC-CN')

    verify_value = (request.headers.get(verify_header, '') or '').strip()
    raw_identifier = (request.headers.get(identifier_header, '') or '').strip()
    common_name = (request.headers.get(cn_header, '') or '').strip()
    if not common_name:
        common_name = _extract_cac_common_name(request.headers.get(subject_header, ''))
    normalized_identifier = _normalize_cac_identity(raw_identifier or common_name)

    return {
        'verify_header': verify_header,
        'verify_value': verify_value,
        'identifier_header': identifier_header,
        'identifier_value': normalized_identifier,
        'subject_dn': (request.headers.get(subject_header, '') or '').strip(),
        'issuer_dn': (request.headers.get(issuer_header, '') or '').strip(),
        'serial_number': (request.headers.get(serial_header, '') or '').strip(),
        'common_name': common_name,
    }


def _cac_headers_are_usable():
    context = _cac_request_identity_context()
    return (
        context['verify_value'].upper() == 'SUCCESS'
        and bool(context['identifier_value'])
        and _request_is_via_secure_proxy()
    )


def _require_verified_cac_response():
    if not current_app.config.get('CAC_AUTH_ENABLED'):
        return None, _render_landing(error='CAC access is disabled.')
    if not _request_is_via_secure_proxy():
        return None, _cac_proxy_required_response()
    context = _cac_request_identity_context()
    if context['verify_value'].upper() != 'SUCCESS' or not context['identifier_value']:
        return None, _render_landing(error='CAC required to access this section.')
    return context, None
    return {
        'request_url': request.url,
        'request_host': request.host,
        'request_scheme': request.scheme,
        'remote_addr': request.remote_addr,
        'forwarded_headers': forwarded_headers,
        'is_secure': request.is_secure,
    }


def _preferred_cac_portal_url():
    if current_app.config.get('APP_ENV') != 'prod':
        return 'https://localhost'

    external_host = (current_app.config.get('APP_DOMAIN') or '').strip()
    if external_host:
        return f"{current_app.config.get('PREFERRED_URL_SCHEME', 'https')}://{external_host}"

    forwarded_host = (request.headers.get('X-Forwarded-Host') or '').strip()
    if forwarded_host:
        scheme = (request.headers.get('X-Forwarded-Proto') or current_app.config.get('PREFERRED_URL_SCHEME') or 'https').strip()
        return f"{scheme}://{forwarded_host}"

    host = request.host.split(':', 1)[0]
    return f"https://{host}"


def _request_is_via_secure_proxy():
    forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').strip().lower()
    forwarded_host = (request.headers.get('X-Forwarded-Host') or '').strip()
    return request.is_secure or forwarded_proto == 'https' or bool(forwarded_host)


def _cac_proxy_required_response():
    portal_url = _preferred_cac_portal_url()
    context = {
        'error': f'CAC requires the HTTPS proxy in front of Flask. Use the CAC portal at {portal_url} instead of direct port 5055.',
    }
    if current_app.config.get('CAC_DEBUG_ENABLED'):
        context['cac_debug'] = _cac_request_debug_context()
    return _render_landing(**context)


def _cac_header_missing_response(username_headers):
    proxy_hint = ''
    if request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https':
        proxy_hint = ' HTTPS reached the app, but no upstream identity header was added. Configure Cloudflare Access or an origin CAC proxy to inject the authenticated user header.'
    context = {
        'error': (
            f'CAC identity header was not provided by the upstream server. Checked: {", ".join(username_headers)}.'
            f'{proxy_hint}'
        ),
    }
    if current_app.config.get('CAC_DEBUG_ENABLED'):
        context['cac_debug'] = _cac_request_debug_context()
    return _render_landing(**context)


def _resolve_cac_identity():
    snapshot = _cac_header_snapshot()
    matched_username_header = snapshot['matched_username_header'] or ''
    username = snapshot['normalized_username'] or ''
    display_name = _display_name_from_cac(snapshot['raw_name'], snapshot['raw_username'])

    return {
        'snapshot': snapshot,
        'username': username,
        'display_name': display_name,
        'matched_username_header': matched_username_header,
    }


@bp.route('/', methods=['GET'])
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('public_landing.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return _render_landing()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    key = request.remote_addr
    now = _utcnow_naive()

    attempts = _login_attempts.get(key, [])
    attempts = [t for t in attempts if now - t < timedelta(minutes=10)]
    if len(attempts) >= 10:
        return _render_landing(error='Too many attempts. Try again later.')

    user = _user_by_username(username, active_only=True)
    if not user or not user.check_password(password):
        attempts.append(now)
        _login_attempts[key] = attempts
        return _render_landing(error='Invalid credentials.')

    from flask_login import login_user

    login_user(user)
    session.pop('acting_role', None)
    session.pop('acting_watch_commander_id', None)
    _safe_audit(actor_id=user.id, action='login', details='User login')
    return redirect(_resolve_post_login_redirect())


@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return _render_landing()
    return login()


@bp.route('/login/name', methods=['GET', 'POST'])
def login_by_name():
    if request.method == 'GET':
        return _render_name_login_page()

    name = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()
    if not name or not password:
        return _render_name_login_page(error='Name and password required.')

    matches = User.query.filter_by(name=name, active=True).all()
    if not matches:
        return _render_name_login_page(error='No active user was found with that name.')
    if len(matches) > 1:
        return _render_name_login_page(error='Multiple users share that name. Use your username instead.')

    user = matches[0]
    if not user.check_password(password):
        return _render_name_login_page(error='Invalid credentials.')

    from flask_login import login_user

    login_user(user)
    session.pop('acting_role', None)
    session.pop('acting_watch_commander_id', None)
    _safe_audit(actor_id=user.id, action='login_name', details='User login by name')
    return redirect(_resolve_post_login_redirect())


@bp.route('/role/switch/<role_key>', methods=['POST'])
@login_required
def switch_role(role_key):
    if not current_user.can_manage_site():
        abort(403)
    if role_key not in {ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER}:
        abort(400)
    session['acting_role'] = role_key
    if role_key == ROLE_WEBSITE_CONTROLLER:
        session.pop('acting_watch_commander_id', None)
    return redirect(request.form.get('next') or url_for('dashboard.dashboard'))


@bp.route('/role/scope', methods=['POST'])
@login_required
def switch_role_scope():
    if not current_user.can_manage_site():
        abort(403)
    supervisor_id = (request.form.get('watch_commander_id') or '').strip()
    if not supervisor_id:
        session.pop('acting_watch_commander_id', None)
        return redirect(request.form.get('next') or url_for('dashboard.dashboard'))

    try:
        supervisor_id_int = int(supervisor_id)
    except ValueError:
        abort(400)
    supervisor = User.query.filter_by(id=supervisor_id_int, active=True).first()
    if not supervisor or supervisor.normalized_role != ROLE_WATCH_COMMANDER:
        abort(400)
    session['acting_watch_commander_id'] = supervisor.id
    session['acting_role'] = ROLE_WATCH_COMMANDER
    return redirect(request.form.get('next') or url_for('dashboard.dashboard'))


def _require_cac_onboarding_context():
    if not current_app.config.get('CAC_AUTH_ENABLED'):
        return None, _render_landing(error='CAC login is disabled.')
    if not _cac_headers_are_usable():
        if not _request_is_via_secure_proxy():
            return None, _cac_proxy_required_response()
        return None, _render_landing(error='CAC identity was not provided by the trusted proxy.')
    return _cac_request_identity_context(), None


@bp.route('/cac/login', methods=['GET', 'POST'])
def cac_login():
    context, failure = _require_cac_onboarding_context()
    if failure:
        return failure

    user = User.query.filter_by(cac_identifier=context['identifier_value'], active=True).first()
    if not user or not (user.cac_enabled or user.cac_identifier):
        _safe_audit(action='login_cac_unlinked', details=context['identifier_value'])
        return redirect(url_for('auth.cac_account_start', next=request.args.get('next') or request.form.get('next') or ''))

    from flask_login import login_user

    login_user(user)
    session.pop('acting_role', None)
    session.pop('acting_watch_commander_id', None)
    _safe_audit(actor_id=user.id, action='login_cac', details=context['identifier_value'])
    return redirect(_resolve_post_login_redirect())


@bp.route('/account/cac/start', methods=['GET', 'POST'])
def cac_account_start():
    context, failure = _require_cac_onboarding_context()
    if failure:
        return failure

    if request.method == 'GET':
        return _render_cac_start_page()

    action = (request.form.get('action') or '').strip().lower()
    identifier = context['identifier_value']

    if User.query.filter(User.cac_identifier == identifier, User.active.is_(True)).first():
        return _render_cac_start_page(error='This CAC is already linked to an active account.')

    if action == 'create':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        officer_number = _normalize_officer_number(request.form.get('officer_number', ''))
        if not first_name or not last_name or not officer_number:
            return _render_cac_start_page(error='First name, last name, and officer number are required.')
        if User.query.filter_by(officer_number=officer_number).first():
            return _render_cac_start_page(error='Officer number already exists.')

        base_username = re.sub(r'[^A-Za-z0-9._-]+', '', f'{first_name}.{last_name}'.lower()) or f'officer{secrets.randbelow(9999)}'
        username = base_username
        suffix = 1
        while _username_exists(username):
            suffix += 1
            username = f'{base_username}{suffix}'

        user = User(
            username=username,
            officer_number=officer_number,
            cac_identifier=identifier,
            cac_enabled=True,
            role=ROLE_PATROL_OFFICER,
            active=True,
        )
        _sync_user_name_fields(user, first_name, last_name)
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.flush()
        from flask_login import login_user
        login_user(user)
        if not _commit_or_rollback():
            return _render_cac_start_page(error='Unable to create the CAC account right now. Try again later.')
        _safe_audit(actor_id=user.id, action='cac_account_create', details=identifier)
        return redirect(_resolve_post_login_redirect())

    if action == 'link':
        officer_number = _normalize_officer_number(request.form.get('officer_number', ''))
        code_value = (request.form.get('enrollment_code') or '').strip().upper()
        if not officer_number or not code_value:
            return _render_cac_start_page(error='Officer number and enrollment code are required.')

        user = User.query.filter_by(officer_number=officer_number, active=True).first()
        if not user:
            return _render_cac_start_page(error='No active account was found for that officer number.')
        if user.cac_identifier and user.cac_identifier != identifier:
            return _render_cac_start_page(error='That account is already linked to a different CAC.')

        enrollment = (
            EnrollmentCode.query.filter_by(code=code_value, user_id=user.id)
            .filter(EnrollmentCode.used_at.is_(None))
            .filter(EnrollmentCode.expires_at >= _utcnow_naive())
            .order_by(EnrollmentCode.created_at.desc())
            .first()
        )
        if not enrollment:
            return _render_cac_start_page(error='Enrollment code is invalid or expired.')

        enrollment.used_at = _utcnow_naive()
        user.cac_identifier = identifier
        user.cac_enabled = True
        from flask_login import login_user
        login_user(user)
        if not _commit_or_rollback():
            return _render_cac_start_page(error='Unable to link this CAC right now. Try again later.')
        _safe_audit(actor_id=user.id, action='cac_account_link', details=identifier)
        return redirect(_resolve_post_login_redirect())

    return _render_cac_start_page(error='Choose whether to create a new CAC account or link an existing one.')


@bp.route('/account/create', methods=['GET', 'POST'])
def account_create_cac():
    context, failure = _require_verified_cac_response()
    if failure:
        return failure

    if request.method == 'GET':
        return _render_account_create_page()

    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    officer_number = _normalize_officer_number(request.form.get('officer_number', ''))
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    identifier = context['identifier_value']

    if not first_name or not last_name or not officer_number or not username or not password:
        return _render_account_create_page(error='First name, last name, officer number, username, and password are required.')
    if _username_exists(username):
        return _render_account_create_page(error='Username already exists.')
    if User.query.filter_by(officer_number=officer_number).first():
        return _render_account_create_page(error='Officer number already exists.')
    if User.query.filter(User.cac_identifier == identifier, User.active.is_(True)).first():
        return _render_account_create_page(error='This CAC is already linked to an active account.')

    user = User(
        username=username,
        officer_number=officer_number,
        cac_identifier=identifier,
        cac_enabled=True,
        cac_linked_at=_utcnow_naive(),
        role=ROLE_PATROL_OFFICER,
        active=True,
    )
    _sync_user_name_fields(user, first_name, last_name)
    user.set_password(password)
    db.session.add(user)
    if not _commit_or_rollback():
        return _render_account_create_page(error='Unable to create the account right now. Try again later.')

    from flask_login import login_user

    login_user(user)
    _safe_audit(actor_id=user.id, action='account_create_cac', details=identifier)
    return redirect(_resolve_post_login_redirect())


@bp.route('/account/link-cac', methods=['GET', 'POST'])
@login_required
def account_link_cac():
    context, failure = _require_verified_cac_response()
    if failure:
        return failure

    if request.method == 'GET':
        return _render_account_link_cac_page()

    identifier = context['identifier_value']
    if User.query.filter(User.cac_identifier == identifier, User.id != current_user.id, User.active.is_(True)).first():
        return _render_account_link_cac_page(error='This CAC is already linked to another active account.')

    current_user.cac_identifier = identifier
    current_user.cac_enabled = True
    current_user.cac_linked_at = _utcnow_naive()
    if not _commit_or_rollback():
        return _render_account_link_cac_page(error='Unable to link CAC right now. Try again later.')

    _safe_audit(actor_id=current_user.id, action='account_link_cac_self', details=identifier)
    return redirect(_resolve_post_login_redirect())


@bp.route('/login/cac', methods=['GET', 'POST'])
def login_cac():
    return cac_login()


@bp.route('/register/cac', methods=['GET', 'POST'])
def register_cac():
    return cac_account_start()


@bp.route('/login/cac/debug', methods=['GET', 'POST'])
def login_cac_debug():
    if not current_app.config.get('CAC_DEBUG_ENABLED'):
        return _render_landing(error='CAC debug is not enabled.')
    return jsonify(_cac_header_snapshot())


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_app.config.get('CAC_AUTH_ENABLED'):
        return redirect(url_for('auth.account_create_cac', next=(request.form.get('next') or request.args.get('next') or '').strip()))
    if request.method == 'GET':
        return _render_register_page()

    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone_number = request.form.get('phone_number', '').strip() or None
    address = request.form.get('address', '').strip() or None
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    installation = request.form.get('installation', '').strip() or None

    valid_installation_keys = {k for k, _ in USMC_INSTALLATIONS}
    if installation and installation not in valid_installation_keys:
        installation = None

    if not first_name or not last_name:
        return _render_register_page(register_error='First and last name are required.')
    if not username:
        return _render_register_page(register_error='Username is required.')
    if not password:
        return _render_register_page(register_error='Password is required.')
    if not phone_number:
        return _render_register_page(register_error='Contact number is required.')
    if not address:
        return _render_register_page(register_error='Home address is required.')
    if not installation:
        return _render_register_page(register_error='Installation is required. Select your Marine Corps installation.')
    if _username_exists(username):
        return _render_register_page(register_error='That username is already taken. Choose another.')

    user = User(
        username=username,
        phone_number=phone_number,
        address=address,
        installation=installation,
        role=ROLE_PATROL_OFFICER,
        active=False,
        pending_approval=True,
    )
    _sync_user_name_fields(user, first_name, last_name)
    user.set_password(password)
    db.session.add(user)
    if not _commit_or_rollback():
        return _render_register_page(register_error='Unable to create the account right now. Try again later.')
    _safe_audit(actor_id=user.id, action='user_register', details=username)

    installation_label = INSTALLATION_LABELS.get(installation, installation)
    return _render_register_page(
        register_success=(
            f'Account request submitted for {installation_label}. '
            'A Watch Commander or higher at your installation will review and activate your account. '
            'You will be able to log in once approved.'
        )
    )


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    from flask_login import logout_user

    logout_user()
    return redirect(url_for('auth.landing'))


def require_admin():
    if not can_manage_team(current_user):
        abort(403)


@bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    require_admin()
    context_kwargs = lambda **extra: {
        'users': _visible_users_query().order_by(User.first_name, User.last_name, User.username).all(),
        'pending_accounts': _pending_accounts_query().order_by(User.created_at).all(),
        'user': current_user,
        'role_options': assignable_roles(current_user),
        'supervisors': _available_supervisors(),
        'role_labels': ROLE_LABELS,
        'installation_labels': INSTALLATION_LABELS,
        'installations': USMC_INSTALLATIONS,
        'database_write_notice': 'This server is currently running with limited database write capability. Some save actions may be blocked until the primary app process is restarted.' if current_app.config.get('APP_ENV') == 'prod' else '',
        **extra,
    }
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username', '').strip()
        if action == 'create':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            officer_number = _normalize_officer_number(request.form.get('officer_number', '')) or None
            edipi = _normalize_edipi(request.form.get('edipi', '')) or None
            role = request.form.get('role', ROLE_PATROL_OFFICER).strip() or ROLE_PATROL_OFFICER
            password = request.form.get('password')
            phone_number = request.form.get('phone_number', '').strip() or None
            address = request.form.get('address', '').strip() or None
            installation = _installation_from_form()
            can_grade_reports = request.form.get('can_grade_cleoc_reports') == '1'
            if not first_name or not last_name:
                return render_template('admin_users.html', **context_kwargs(error='First name and last name are required.'))
            if not username or not password or not phone_number or not address:
                return render_template('admin_users.html', **context_kwargs(error='Username, password, phone number, and address are required.'))
            if _username_exists(username):
                return render_template('admin_users.html', **context_kwargs(error='Username exists.'))
            if officer_number and User.query.filter_by(officer_number=officer_number).first():
                return render_template('admin_users.html', **context_kwargs(error='Officer number already exists.'))
            if edipi and len(edipi) != 10:
                return render_template('admin_users.html', **context_kwargs(error='EDIPI must be a 10-digit number.'))
            if edipi and User.query.filter_by(edipi=edipi).first():
                return render_template('admin_users.html', **context_kwargs(error='EDIPI already exists.'))
            if role not in assignable_roles(current_user):
                return render_template('admin_users.html', **context_kwargs(error='You cannot assign that role.'))
            try:
                supervisor = _supervisor_from_form()
            except ValueError as exc:
                return render_template('admin_users.html', **context_kwargs(error=str(exc)))
            user = User(
                username=username,
                officer_number=officer_number,
                edipi=edipi,
                phone_number=phone_number,
                address=address,
                installation=installation,
                supervisor_id=supervisor.id if supervisor else None,
                role=role,
                can_grade_cleoc_reports=can_grade_reports,
                active=True,
            )
            _sync_user_name_fields(user, first_name, last_name)
            user.set_password(password)
            db.session.add(user)
            if not _commit_or_rollback():
                return render_template('admin_users.html', **context_kwargs(error='Unable to create that user right now. Try again later.'))
            _safe_audit(actor_id=current_user.id, action='user_create', details=username)
        elif action == 'update':
            target = _user_by_username(username)
            if not target or not can_manage_user(current_user, target):
                abort(403)
            try:
                _apply_personnel_edit(target)
            except ValueError as exc:
                return render_template('admin_users.html', **context_kwargs(error=str(exc)))
            if not _commit_or_rollback():
                return render_template('admin_users.html', **context_kwargs(error='Unable to update that user right now. Try again later.'))
            _safe_audit(actor_id=current_user.id, action='user_update_role', details=f'{username}:{target.role}')
        elif action == 'delete':
            target = _user_by_username(username)
            if not target:
                return render_template('admin_users.html', **context_kwargs(error='User not found.'))
            if not can_manage_user(current_user, target):
                abort(403)
            # Site controllers cannot be deleted by non-site-controllers (enforced by can_manage_user),
            # but also prevent deleting yourself
            if target.id == current_user.id:
                return render_template('admin_users.html', **context_kwargs(error='You cannot delete your own account.'))
            deleted_name = target.display_name
            db.session.delete(target)
            if not _commit_or_rollback():
                return render_template('admin_users.html', **context_kwargs(error='Unable to delete that user right now. Try again later.'))
            _safe_audit(actor_id=current_user.id, action='user_delete', details=f'{username} ({deleted_name})')
        elif action == 'approve':
            pending_id = request.form.get('pending_id', '').strip()
            if not pending_id:
                return render_template('admin_users.html', **context_kwargs(error='No account selected for approval.'))
            try:
                target = db.session.get(User, int(pending_id))
            except (ValueError, TypeError):
                target = None
            if not target or not target.pending_approval:
                return render_template('admin_users.html', **context_kwargs(error='Account not found or not pending approval.'))
            # Enforce installation scope for non-site-controllers
            if not is_site_controller(current_user) and target.installation != current_user.installation:
                return render_template('admin_users.html', **context_kwargs(error='You can only approve accounts from your installation.'))
            role = request.form.get('role', ROLE_PATROL_OFFICER).strip() or ROLE_PATROL_OFFICER
            if role not in assignable_roles(current_user):
                return render_template('admin_users.html', **context_kwargs(error='You cannot assign that role.'))
            supervisor_id = request.form.get('supervisor_id', '').strip()
            supervisor = None
            if supervisor_id:
                try:
                    supervisor = db.session.get(User, int(supervisor_id))
                except (ValueError, TypeError):
                    pass
            if is_watch_commander(current_user):
                supervisor = db.session.get(User, watch_commander_scope_id(current_user))
            section_unit = request.form.get('section_unit', '').strip() or None
            target.role = role
            target.supervisor_id = supervisor.id if supervisor else None
            target.section_unit = section_unit or target.section_unit
            target.active = True
            target.pending_approval = False
            if not _commit_or_rollback():
                return render_template('admin_users.html', **context_kwargs(error='Unable to approve that account right now.'))
            _safe_audit(actor_id=current_user.id, action='user_approve', details=f'{target.username}:{role}')
        elif action == 'reject':
            pending_id = request.form.get('pending_id', '').strip()
            if not pending_id:
                return render_template('admin_users.html', **context_kwargs(error='No account selected for rejection.'))
            try:
                target = db.session.get(User, int(pending_id))
            except (ValueError, TypeError):
                target = None
            if not target or not target.pending_approval:
                return render_template('admin_users.html', **context_kwargs(error='Account not found or not pending approval.'))
            if not is_site_controller(current_user) and target.installation != current_user.installation:
                return render_template('admin_users.html', **context_kwargs(error='You can only reject accounts from your installation.'))
            rejected_name = target.display_name
            db.session.delete(target)
            if not _commit_or_rollback():
                return render_template('admin_users.html', **context_kwargs(error='Unable to reject that account right now.'))
            _safe_audit(actor_id=current_user.id, action='user_reject', details=rejected_name)
        elif action == 'issue_code':
            target = _user_by_username(username, active_only=True)
            if not target or not can_manage_user(current_user, target):
                abort(403)
            raw_hours = (request.form.get('hours') or '24').strip() or '24'
            try:
                hours = int(raw_hours)
            except ValueError:
                return render_template('admin_users.html', **context_kwargs(error='Enrollment hours must be a whole number.'))
            hours = max(1, min(72, hours))
            code_value = secrets.token_urlsafe(8).replace('-', '').replace('_', '').upper()[:12]
            enrollment = EnrollmentCode(
                code=code_value,
                user_id=target.id,
                expires_at=_utcnow_naive() + timedelta(hours=hours),
                created_by=current_user.id,
            )
            db.session.add(enrollment)
            if not _commit_or_rollback():
                return render_template('admin_users.html', **context_kwargs(error='Unable to issue an enrollment code right now. Try again later.'))
            _safe_audit(actor_id=current_user.id, action='enrollment_code_issue', details=f'{target.username}:{code_value}')
            return render_template(
                'admin_users.html',
                **context_kwargs(success=f'Enrollment code issued for {target.display_name}.', issued_code=code_value),
            )
        elif action == 'disable':
            user = _user_by_username(username)
            if user and can_manage_user(current_user, user):
                user.active = False
                if not _commit_or_rollback():
                    return render_template('admin_users.html', **context_kwargs(error='Unable to disable that user right now. Try again later.'))
                _safe_audit(actor_id=current_user.id, action='user_disable', details=username)
        elif action == 'reset':
            user = _user_by_username(username)
            new_pw = request.form.get('password')
            if user and new_pw and can_manage_user(current_user, user):
                user.set_password(new_pw)
                if not _commit_or_rollback():
                    return render_template('admin_users.html', **context_kwargs(error='Unable to reset that password right now. Try again later.'))
                _safe_audit(actor_id=current_user.id, action='user_reset', details=username)
        return redirect(url_for('auth.manage_users'))

    return render_template('admin_users.html', **context_kwargs())


@bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    require_admin()
    target = db.session.get(User, user_id)
    if not target or not can_manage_user(current_user, target):
        abort(403)

    context = {
        'target_user': target,
        'user': current_user,
        'role_options': assignable_roles(current_user),
        'supervisors': _available_supervisors(),
        'role_labels': ROLE_LABELS,
        'installation_labels': INSTALLATION_LABELS,
        'installations': USMC_INSTALLATIONS,
    }
    if request.method == 'POST':
        try:
            _apply_personnel_edit(target)
        except ValueError as exc:
            return render_template('admin_user_edit.html', **context, error=str(exc))
        if not _commit_or_rollback():
            return render_template('admin_user_edit.html', **context, error='Unable to save that officer right now. Try again later.')
        _safe_audit(actor_id=current_user.id, action='user_profile_admin_edit', details=f'{target.username}:{target.role}')
        return redirect(url_for('auth.manage_users'))

    return render_template('admin_user_edit.html', **context)
