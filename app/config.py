import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
UPLOAD_ROOT = os.environ.get('UPLOAD_ROOT', os.path.join(DATA_DIR, 'uploads'))
DEFAULT_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'app.db').replace(os.sep, '/')}"
RAILWAY_VOLUME_MOUNT_PATH = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '/data')


def _database_url_from_env():
    keys = (
        'MCPD_DATABASE_URL',
        'DATABASE_URL',
        'DATABASE_PRIVATE_URL',
        'POSTGRES_URL',
        'POSTGRES_PRIVATE_URL',
        'RAILWAY_DATABASE_URL',
    )
    candidates = [
        (key, os.environ.get(key).strip())
        for key in keys
        if os.environ.get(key) and os.environ.get(key).strip()
    ]
    if not candidates:
        return ''

    # Railway can sometimes keep a stale DATABASE_URL around. In production,
    # a Postgres URL is always safer than an app-filesystem SQLite URL, so
    # prefer any Postgres candidate before falling back to declaration order.
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID'):
        for _key, value in candidates:
            normalized = _normalize_database_uri(value)
            if normalized.startswith('postgresql://'):
                return value

    return candidates[0][1]
    return ''


def _header_list(value):
    return [item.strip() for item in (value or '').split(',') if item.strip()]


def _merged_header_list(value, default_value):
    merged = []
    for item in _header_list(value) + _header_list(default_value):
        if item not in merged:
            merged.append(item)
    return merged


def _normalize_database_uri(value):
    raw = str(value or '').strip()
    if not raw:
        return DEFAULT_DATABASE_URI
    if raw.startswith('postgres://'):
        return 'postgresql://' + raw[len('postgres://'):]
    if not raw.startswith('sqlite:///') or raw.startswith('sqlite:////'):
        return raw

    path_part = raw[len('sqlite:///'):]
    if not path_part or path_part == ':memory:' or path_part.startswith('/'):
        return raw
    if len(path_part) >= 3 and path_part[1] == ':' and path_part[2] in {'/', '\\'}:
        return raw.replace('\\', '/')

    absolute_path = os.path.abspath(os.path.join(ROOT_DIR, path_part))
    return f"sqlite:///{absolute_path.replace(os.sep, '/')}"

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')
    SQLALCHEMY_DATABASE_URI = _normalize_database_uri(_database_url_from_env())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    UPLOAD_ROOT = UPLOAD_ROOT
    FORMS_UPLOAD = os.path.join(UPLOAD_ROOT, 'forms')
    TRAINING_UPLOAD = os.path.join(UPLOAD_ROOT, 'training')
    STATS_UPLOAD = os.path.join(UPLOAD_ROOT, 'stats')
    SIGNATURES_DIR = os.path.join(DATA_DIR, 'signatures')
    APP_ENV = os.environ.get('APP_ENV', 'dev')
    APP_DOMAIN = os.environ.get('APP_DOMAIN', '')
    SERVER_NAME = None
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'https' if APP_ENV == 'prod' else 'http')
    TRUST_PROXY = os.environ.get('TRUST_PROXY', '1' if APP_ENV == 'prod' else '0').lower() in {'1', 'true', 'yes', 'on'}
    PROXY_FIX_X_FOR = int(os.environ.get('PROXY_FIX_X_FOR', '1'))
    PROXY_FIX_X_PROTO = int(os.environ.get('PROXY_FIX_X_PROTO', '1'))
    PROXY_FIX_X_HOST = int(os.environ.get('PROXY_FIX_X_HOST', '1'))
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '1' if APP_ENV == 'prod' else '0').lower() in {'1', 'true', 'yes', 'on'}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.environ.get('REMEMBER_COOKIE_SAMESITE', 'Lax')
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', '1' if APP_ENV == 'prod' else '0').lower() in {'1', 'true', 'yes', 'on'}
    HSTS_ENABLED = os.environ.get('HSTS_ENABLED', '1' if APP_ENV == 'prod' else '0').lower() in {'1', 'true', 'yes', 'on'}
    HSTS_MAX_AGE = int(os.environ.get('HSTS_MAX_AGE', '31536000'))
    GOOGLE_SITE_VERIFICATION = os.environ.get('GOOGLE_SITE_VERIFICATION', '')
    CAC_AUTH_ENABLED = os.environ.get('CAC_AUTH_ENABLED', '0').lower() in {'1', 'true', 'yes', 'on'}
    CAC_AUTO_REGISTER = os.environ.get('CAC_AUTO_REGISTER', '0').lower() in {'1', 'true', 'yes', 'on'}
    CAC_DEBUG_ENABLED = os.environ.get('CAC_DEBUG_ENABLED', '0').lower() in {'1', 'true', 'yes', 'on'}
    PUBLIC_SELF_REGISTER_ENABLED = os.environ.get(
        'PUBLIC_SELF_REGISTER_ENABLED',
        '1',
    ).lower() in {'1', 'true', 'yes', 'on'}
    CAC_USERNAME_HEADER = os.environ.get('CAC_USERNAME_HEADER', 'X-Authenticated-User')
    CAC_NAME_HEADER = os.environ.get('CAC_NAME_HEADER', 'X-Authenticated-Name')
    CAC_USERNAME_HEADERS = _merged_header_list(
        os.environ.get('CAC_USERNAME_HEADERS', ''),
        (
            f"{CAC_USERNAME_HEADER},"
            "X-Authenticated-User,"
            "X-Client-Cert-Subject,"
            "X-SSL-Client-S-DN,"
            "X-ARR-ClientCert-Subject,"
            "Cf-Access-Authenticated-User-Email,"
            "Cf-Access-Email"
        ),
    )
    CAC_NAME_HEADERS = _merged_header_list(
        os.environ.get('CAC_NAME_HEADERS', ''),
        (
            f"{CAC_NAME_HEADER},"
            "X-Authenticated-Name,"
            "X-Client-Cert-Subject,"
            "X-SSL-Client-S-DN,"
            "X-ARR-ClientCert-Subject,"
            "Cf-Access-Authenticated-User-Name,"
            "Cf-Access-Name"
        ),
    )
    CAC_VERIFY_HEADER = os.environ.get('CAC_VERIFY_HEADER', 'X-CAC-VERIFY')
    CAC_IDENTIFIER_HEADER = os.environ.get('CAC_IDENTIFIER_HEADER', 'X-CAC-IDENTIFIER')
    CAC_SUBJECT_DN_HEADER = os.environ.get('CAC_SUBJECT_DN_HEADER', 'X-CAC-SUBJECT-DN')
    CAC_ISSUER_DN_HEADER = os.environ.get('CAC_ISSUER_DN_HEADER', 'X-CAC-ISSUER-DN')
    CAC_SERIAL_HEADER = os.environ.get('CAC_SERIAL_HEADER', 'X-CAC-SERIAL')
    CAC_CN_HEADER = os.environ.get('CAC_CN_HEADER', 'X-CAC-CN')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    CLEO_URL = os.environ.get('CLEO_URL', '')
    REQUIRE_PERSISTENT_DATABASE = os.environ.get(
        'REQUIRE_PERSISTENT_DATABASE', '0',
    ).lower() in {'1', 'true', 'yes', 'on'}
