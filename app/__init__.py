from flask import Flask, Response, g, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user
from dotenv import dotenv_values
from datetime import datetime, timezone
import hmac
import logging
import os
import json
import secrets
import weakref
import warnings
from urllib.parse import urlparse
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    from cryptography.utils import CryptographyDeprecationWarning
except Exception:
    CryptographyDeprecationWarning = DeprecationWarning

warnings.filterwarnings(
    'ignore',
    message=r'ARC4 has been moved to cryptography\.hazmat\.decrepit\.ciphers\.algorithms\.ARC4',
    category=CryptographyDeprecationWarning,
)

# Let local shells use .env, but never let committed machine-local .env values
# override Railway service variables or accidentally point production at SQLite.
if not (os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID')):
    load_dotenv(override=False)

from .config import Config, _database_url_from_env, _normalize_database_uri
from .extensions import db, login_manager
from .models import ALL_PORTAL_ROLES, ROLE_LABELS, ROLE_WEBSITE_CONTROLLER, ROLE_WATCH_COMMANDER, Role, User

_CREATED_APPS = weakref.WeakSet()


def _database_uri_is_ephemeral(uri):
    raw = str(uri or '').strip()
    if not raw.startswith('sqlite:///'):
        return False
    if raw == 'sqlite:///:memory:':
        return True
    path = raw[len('sqlite:///'):]
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    persistent_roots = [
        os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', ''),
        os.environ.get('PERSISTENT_DATA_DIR', ''),
    ]
    persistent_roots = [os.path.abspath(root) for root in persistent_roots if root]
    if any(os.path.abspath(path).startswith(root + os.sep) or os.path.abspath(path) == root for root in persistent_roots):
        return False
    return True


def _enforce_persistent_database_config(app):
    if app.config.get('TESTING') or not app.config.get('REQUIRE_PERSISTENT_DATABASE'):
        return
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if not _database_uri_is_ephemeral(database_uri):
        return
    configured_db_vars = [
        key for key in (
            'MCPD_DATABASE_URL',
            'DATABASE_URL',
            'DATABASE_PRIVATE_URL',
            'POSTGRES_URL',
            'POSTGRES_PRIVATE_URL',
            'RAILWAY_DATABASE_URL',
        )
        if os.environ.get(key)
    ]
    configured_db_summaries = []
    for key in configured_db_vars:
        parsed_value = urlparse(_normalize_database_uri(os.environ.get(key)))
        summary = f"{key}:{parsed_value.scheme or 'none'}"
        if parsed_value.hostname:
            summary += f"@{parsed_value.hostname}"
        configured_db_summaries.append(summary)
    parsed_database_uri = urlparse(str(database_uri or ''))
    database_summary = f"active database scheme={parsed_database_uri.scheme or 'none'}"
    if parsed_database_uri.hostname:
        database_summary += f", host={parsed_database_uri.hostname}"
    if parsed_database_uri.path:
        database_summary += f", path={parsed_database_uri.path}"
    details = (
        f" Detected database environment variables: {', '.join(configured_db_vars) or 'none'}."
        f" Variable summaries: {', '.join(configured_db_summaries) or 'none'}."
        f" {database_summary}."
    )
    message = (
        'Unsafe production database configuration: this deployment is using SQLite on the app filesystem. '
        'That can wipe officer accounts on rebuild/update. Set DATABASE_URL to Railway Postgres, or mount a '
        'persistent volume and use sqlite:////data/app.db. Set REQUIRE_PERSISTENT_DATABASE=0 only for throwaway testing.'
        + details
    )
    logging.getLogger(__name__).critical(message)
    raise RuntimeError(message)


def _refresh_runtime_environment_config(app):
    database_url = _database_url_from_env()
    if database_url is not None:
        app.config['SQLALCHEMY_DATABASE_URI'] = _normalize_database_uri(database_url)
    require_persistent = os.environ.get('REQUIRE_PERSISTENT_DATABASE')
    if require_persistent is not None:
        app.config['REQUIRE_PERSISTENT_DATABASE'] = require_persistent.lower() in {'1', 'true', 'yes', 'on'}
    elif os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID'):
        app.config['REQUIRE_PERSISTENT_DATABASE'] = True


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def seed_admin():
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')
    if not username or not password:
        return
    if User.query.filter_by(username=username).first():
        return
    try:
        user = User(username=username, role=ROLE_WEBSITE_CONTROLLER, active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return


def seed_roles():
    existing = {role.key for role in Role.query.all()}
    changed = False
    for role_key in ALL_PORTAL_ROLES:
        if role_key in existing:
            continue
        db.session.add(Role(key=role_key, label=ROLE_LABELS.get(role_key, role_key.replace('_', ' ').title())))
        changed = True
    if changed:
        db.session.commit()


def _safe_schema_execute(statement, params=None):
    try:
        db.session.execute(text(statement), params or {})
        db.session.commit()
        return True
    except OperationalError:
        db.session.rollback()
        return False


def _quoted_identifier(name):
    return db.engine.dialect.identifier_preparer.quote(name)


def ensure_schema():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    user_columns = {column['name'] for column in inspector.get_columns('user')}
    user_indexes = {index['name'] for index in inspector.get_indexes('user')}
    user_table = _quoted_identifier('user')
    if 'edipi' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN edipi VARCHAR(20)')
    if 'first_name' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN first_name VARCHAR(80)')
    if 'last_name' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN last_name VARCHAR(80)')
    if 'officer_number' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN officer_number VARCHAR(30)')
    if 'display_name_override' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN display_name_override VARCHAR(120)')
    if 'email' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN email VARCHAR(120)')
    if 'phone_number' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN phone_number VARCHAR(30)')
    if 'badge_employee_id' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN badge_employee_id VARCHAR(40)')
    if 'section_unit' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN section_unit VARCHAR(120)')
    if 'profile_image_path' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN profile_image_path VARCHAR(255)')
    if 'address' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN address VARCHAR(255)')
    if 'cac_identifier' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN cac_identifier VARCHAR(255)')
    if 'cac_enabled' not in user_columns:
        if _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN cac_enabled BOOLEAN'):
            _safe_schema_execute(f'UPDATE {user_table} SET cac_enabled = 0 WHERE cac_enabled IS NULL')
    if 'cac_linked_at' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN cac_linked_at DATETIME')
    if 'pin_hash' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN pin_hash VARCHAR(255)')
    if 'can_grade_cleoc_reports' not in user_columns:
        if _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN can_grade_cleoc_reports BOOLEAN'):
            _safe_schema_execute(f'UPDATE {user_table} SET can_grade_cleoc_reports = 0 WHERE can_grade_cleoc_reports IS NULL')
    if 'supervisor_id' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN supervisor_id INTEGER')
    if 'pending_approval' not in user_columns:
        if _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN pending_approval BOOLEAN'):
            _safe_schema_execute(f'UPDATE {user_table} SET pending_approval = 0 WHERE pending_approval IS NULL')
    if 'installation' not in user_columns:
        _safe_schema_execute(f'ALTER TABLE {user_table} ADD COLUMN installation VARCHAR(100)')
    admin_count = db.session.execute(text(f"SELECT COUNT(*) FROM {user_table} WHERE role = 'ADMIN'")).scalar() or 0
    if admin_count:
        _safe_schema_execute(
            f"UPDATE {user_table} SET role = :controller WHERE role = 'ADMIN'",
            {'controller': ROLE_WEBSITE_CONTROLLER},
        )
    officer_count = db.session.execute(text(f"SELECT COUNT(*) FROM {user_table} WHERE role = 'OFFICER'")).scalar() or 0
    if officer_count:
        _safe_schema_execute(
            f"UPDATE {user_table} SET role = :patrol WHERE role = 'OFFICER'",
            {'patrol': 'PATROL_OFFICER'},
        )
    if 'ix_user_edipi_unique' not in user_indexes:
        _safe_schema_execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_edipi_unique ON {user_table} (edipi) WHERE edipi IS NOT NULL')
    if 'ix_user_officer_number_unique' not in user_indexes:
        _safe_schema_execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_officer_number_unique ON {user_table} (officer_number) WHERE officer_number IS NOT NULL')
    if 'ix_user_cac_identifier_unique' not in user_indexes:
        _safe_schema_execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_cac_identifier_unique ON {user_table} (cac_identifier) WHERE cac_identifier IS NOT NULL')
    if 'ix_user_email_unique' not in user_indexes:
        _safe_schema_execute(f'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email_unique ON {user_table} (email) WHERE email IS NOT NULL')

    if 'truck_gate_log' in table_names:
        truck_gate_log_columns = {column['name'] for column in inspector.get_columns('truck_gate_log')}
        if 'log_date' not in truck_gate_log_columns:
            if _safe_schema_execute("ALTER TABLE truck_gate_log ADD COLUMN log_date VARCHAR(10)"):
                _safe_schema_execute("UPDATE truck_gate_log SET log_date = substr(created_at, 1, 10) WHERE log_date IS NULL OR log_date = ''")
        if 'daily_file_name' not in truck_gate_log_columns:
            if _safe_schema_execute("ALTER TABLE truck_gate_log ADD COLUMN daily_file_name VARCHAR(255)"):
                _safe_schema_execute(
                    "UPDATE truck_gate_log SET daily_file_name = 'truck-gate-' || log_date || '.xlsx' "
                    "WHERE (daily_file_name IS NULL OR daily_file_name = '') AND log_date IS NOT NULL AND log_date != ''"
                )

    if 'order_document' in table_names:
        order_columns = {column['name'] for column in inspector.get_columns('order_document')}
        if 'source_type' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN source_type VARCHAR(40)")
        if 'source_group' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN source_group VARCHAR(80)")
        if 'order_number' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN order_number VARCHAR(80)")
        if 'memo_number' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN memo_number VARCHAR(80)")
        if 'issuing_authority' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN issuing_authority VARCHAR(120)")
        if 'issue_date' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN issue_date DATETIME")
        if 'revision_date' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN revision_date DATETIME")
        if 'source_version' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN source_version VARCHAR(80)")
        if 'audience_tags' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN audience_tags VARCHAR(255)")
        if 'topic_tags' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN topic_tags VARCHAR(255)")
        if 'extracted_text' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN extracted_text TEXT")
        if 'parser_confidence' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN parser_confidence FLOAT")
        if 'superseded_by_id' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN superseded_by_id INTEGER")
        if 'last_indexed_at' not in order_columns:
            _safe_schema_execute("ALTER TABLE order_document ADD COLUMN last_indexed_at DATETIME")

    if 'saved_form' in table_names:
        saved_form_columns = {column['name'] for column in inspector.get_columns('saved_form')}
        if 'title' not in saved_form_columns:
            _safe_schema_execute("ALTER TABLE saved_form ADD COLUMN title VARCHAR(200)")
        if 'access_scope' not in saved_form_columns:
            _safe_schema_execute("ALTER TABLE saved_form ADD COLUMN access_scope VARCHAR(40)")
        if 'rendered_output_path' not in saved_form_columns:
            _safe_schema_execute("ALTER TABLE saved_form ADD COLUMN rendered_output_path VARCHAR(255)")

    if 'form' in table_names:
        form_columns = {column['name'] for column in inspector.get_columns('form')}
        if 'contains_pii' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN contains_pii BOOLEAN"):
                _safe_schema_execute("UPDATE form SET contains_pii = 0 WHERE contains_pii IS NULL")
        if 'retention_mode' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN retention_mode VARCHAR(40)"):
                _safe_schema_execute("UPDATE form SET retention_mode = 'full_save_allowed' WHERE retention_mode IS NULL OR retention_mode = ''")
        if 'allow_email' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN allow_email BOOLEAN"):
                _safe_schema_execute("UPDATE form SET allow_email = 1 WHERE allow_email IS NULL")
        if 'allow_download' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN allow_download BOOLEAN"):
                _safe_schema_execute("UPDATE form SET allow_download = 1 WHERE allow_download IS NULL")
        if 'allow_completed_save' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN allow_completed_save BOOLEAN"):
                _safe_schema_execute("UPDATE form SET allow_completed_save = 1 WHERE allow_completed_save IS NULL")
        if 'allow_blank_print' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN allow_blank_print BOOLEAN"):
                _safe_schema_execute("UPDATE form SET allow_blank_print = 1 WHERE allow_blank_print IS NULL")
        if 'official_source_url' not in form_columns:
            _safe_schema_execute("ALTER TABLE form ADD COLUMN official_source_url VARCHAR(500)")
        if 'official_source_version' not in form_columns:
            _safe_schema_execute("ALTER TABLE form ADD COLUMN official_source_version VARCHAR(80)")
        if 'official_source_hash' not in form_columns:
            _safe_schema_execute("ALTER TABLE form ADD COLUMN official_source_hash VARCHAR(64)")
        if 'official_source_last_checked_at' not in form_columns:
            _safe_schema_execute("ALTER TABLE form ADD COLUMN official_source_last_checked_at DATETIME")
        if 'official_source_last_status' not in form_columns:
            _safe_schema_execute("ALTER TABLE form ADD COLUMN official_source_last_status TEXT")
        if 'source_auto_update_enabled' not in form_columns:
            if _safe_schema_execute("ALTER TABLE form ADD COLUMN source_auto_update_enabled BOOLEAN"):
                _safe_schema_execute("UPDATE form SET source_auto_update_enabled = 0 WHERE source_auto_update_enabled IS NULL")

    if 'vehicle_inspection' in table_names:
        vehicle_inspection_columns = {column['name'] for column in inspector.get_columns('vehicle_inspection')}
        if 'correction_reason' not in vehicle_inspection_columns:
            _safe_schema_execute("ALTER TABLE vehicle_inspection ADD COLUMN correction_reason VARCHAR(255)")
        if 'returned_at' not in vehicle_inspection_columns:
            _safe_schema_execute("ALTER TABLE vehicle_inspection ADD COLUMN returned_at DATETIME")

    if 'rfi_appointment_upload' in table_names:
        rfi_upload_columns = {column['name'] for column in inspector.get_columns('rfi_appointment_upload')}
        if 'committed_profile_id' not in rfi_upload_columns:
            _safe_schema_execute("ALTER TABLE rfi_appointment_upload ADD COLUMN committed_profile_id INTEGER")

    if 'cleo_report' in table_names:
        cleo_report_columns = {column['name'] for column in inspector.get_columns('cleo_report')}
        if 'submitted_at' not in cleo_report_columns:
            _safe_schema_execute("ALTER TABLE cleo_report ADD COLUMN submitted_at DATETIME")
        if 'submitted_by' not in cleo_report_columns:
            _safe_schema_execute("ALTER TABLE cleo_report ADD COLUMN submitted_by INTEGER")
        if 'returned_at' not in cleo_report_columns:
            _safe_schema_execute("ALTER TABLE cleo_report ADD COLUMN returned_at DATETIME")
        if 'returned_by' not in cleo_report_columns:
            _safe_schema_execute("ALTER TABLE cleo_report ADD COLUMN returned_by INTEGER")
        if 'graded_at' not in cleo_report_columns:
            _safe_schema_execute("ALTER TABLE cleo_report ADD COLUMN graded_at DATETIME")
        if 'graded_by' not in cleo_report_columns:
            _safe_schema_execute("ALTER TABLE cleo_report ADD COLUMN graded_by INTEGER")
        _safe_schema_execute(
            "UPDATE cleo_report SET status = 'DRAFT' WHERE status IS NULL OR status = '' OR status = 'LEVEL_1'"
        )
        _safe_schema_execute(
            "UPDATE cleo_report SET status = 'SUBMITTED' WHERE status = 'LEVEL_2'"
        )

    if 'accident_reconstruction' in table_names:
        accident_columns = {column['name'] for column in inspector.get_columns('accident_reconstruction')}
        if 'report_id' not in accident_columns:
            _safe_schema_execute("ALTER TABLE accident_reconstruction ADD COLUMN report_id INTEGER")
        if 'diagram_data_json' not in accident_columns:
            _safe_schema_execute("ALTER TABLE accident_reconstruction ADD COLUMN diagram_data_json TEXT")

    if 'reconstruction_vehicle' in table_names:
        recon_vehicle_columns = {column['name'] for column in inspector.get_columns('reconstruction_vehicle')}
        vehicle_additions = {
            'reconstruction_id': 'INTEGER',
            'label': 'VARCHAR(40)',
            'type': 'VARCHAR(80)',
            'pre_crash_speed': 'FLOAT',
            'impact_speed': 'FLOAT',
            'post_crash_speed': 'FLOAT',
            'x_position': 'FLOAT',
            'y_position': 'FLOAT',
            'rotation': 'FLOAT',
            'driver': 'VARCHAR(120)',
            'damage_notes': 'TEXT',
        }
        for column_name, column_type in vehicle_additions.items():
            if column_name not in recon_vehicle_columns:
                _safe_schema_execute(f"ALTER TABLE reconstruction_vehicle ADD COLUMN {column_name} {column_type}")

    if 'reconstruction_measurement' in table_names:
        recon_measurement_columns = {column['name'] for column in inspector.get_columns('reconstruction_measurement')}
        measurement_additions = {
            'reconstruction_id': 'INTEGER',
            'measurement_type': 'VARCHAR(60)',
            'start_x': 'FLOAT',
            'start_y': 'FLOAT',
            'end_x': 'FLOAT',
            'end_y': 'FLOAT',
        }
        for column_name, column_type in measurement_additions.items():
            if column_name not in recon_measurement_columns:
                _safe_schema_execute(f"ALTER TABLE reconstruction_measurement ADD COLUMN {column_name} {column_type}")


def create_app():
    app = Flask(__name__)
    _CREATED_APPS.add(app)
    app.config.from_object(Config)
    _refresh_runtime_environment_config(app)
    _enforce_persistent_database_config(app)
    # Respect environment/config-driven cookie and scheme settings so local
    # LAN access can use HTTP while production stays on secure cookies/HTTPS.
    app.config["PREFERRED_URL_SCHEME"] = app.config.get("PREFERRED_URL_SCHEME", "http")
    app.config["SESSION_COOKIE_SECURE"] = bool(app.config.get("SESSION_COOKIE_SECURE"))
    app.config["SESSION_COOKIE_SAMESITE"] = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SECURE"] = bool(app.config.get("REMEMBER_COOKIE_SECURE"))
    app.config["REMEMBER_COOKIE_SAMESITE"] = app.config.get("REMEMBER_COOKIE_SAMESITE", "Lax")
    app.config['PROCESS_STARTED_AT_UTC'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    app.config['PROCESS_PID'] = os.getpid()
    app.config['LEGAL_AI_EXPANSION_ENABLED'] = str(os.environ.get('LEGAL_AI_EXPANSION_ENABLED', '1')).strip().lower() in {
        '1', 'true', 'yes', 'on'
    }
    app.config['ORDERS_AI_ASSIST_ENABLED'] = str(os.environ.get('ORDERS_AI_ASSIST_ENABLED', '1')).strip().lower() in {
        '1', 'true', 'yes', 'on'
    }
    app.config['LEGAL_QUERY_LOG_ENABLED'] = str(os.environ.get('LEGAL_QUERY_LOG_ENABLED', '1')).strip().lower() in {
        '1', 'true', 'yes', 'on'
    }

    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=int(app.config.get("PROXY_FIX_X_FOR", 1) or 1),
            x_proto=int(app.config.get("PROXY_FIX_X_PROTO", 1) or 1),
            x_host=int(app.config.get("PROXY_FIX_X_HOST", 1) or 1),
        )

    if app.config.get('APP_ENV') == 'prod' and app.config.get('SECRET_KEY') == 'change-me':
        logging.getLogger(__name__).critical(
            'SECURITY: SECRET_KEY is set to the default value "change-me" in production. '
            'Set a strong random SECRET_KEY environment variable before going live.'
        )

    @app.before_request
    def _csrf_token_setup():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        g.csrf_token = session['_csrf_token']

    @app.get("/favicon.ico")
    def favicon():
        return send_file(
            os.path.join(app.static_folder, "img", "usmc_emblem.png"),
            mimetype="image/svg+xml",
        )

    @app.get("/apple-touch-icon.png")
    def apple_touch_icon():
        return send_file(
            os.path.join(app.static_folder, "img", "usmc_emblem.png"),
            mimetype="image/svg+xml",
        )

    @app.get("/apple-touch-icon-precomposed.png")
    def apple_touch_icon_precomposed():
        return send_file(
            os.path.join(app.static_folder, "img", "usmc_emblem.png"),
            mimetype="image/svg+xml",
        )

    @app.get("/assets/usmc-emblem.svg")
    def usmc_emblem():
        return send_file(
            os.path.join(app.static_folder, "img", "usmc_emblem.png"),
            mimetype="image/svg+xml",
        )

    @app.get("/robots.txt")
    def robots():
        host = (request.host or "mclbpd.com").split(":", 1)[0]
        lines = [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: https://{host}/sitemap.xml",
        ]
        return Response("\n".join(lines) + "\n", mimetype="text/plain")

    @app.get("/sitemap.xml")
    def sitemap():
        base = f"https://{(request.host or 'mclbpd.com').split(':', 1)[0]}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        urls = [
            (url_for('auth.landing', _external=False), "1.0"),
            (url_for('auth.login', _external=False), "0.9"),
            (url_for('auth.login_by_name', _external=False), "0.8"),
            (url_for('auth.register', _external=False), "0.7"),
            (url_for('auth.cac_login', _external=False), "0.8"),
            ("/healthz", "0.3"),
        ]
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for path, priority in urls:
            xml_parts.extend(
                [
                    "  <url>",
                    f"    <loc>{base}{path}</loc>",
                    f"    <lastmod>{now}</lastmod>",
                    f"    <priority>{priority}</priority>",
                    "  </url>",
                ]
            )
        xml_parts.append("</urlset>")
        response = Response("\n".join(xml_parts) + "\n", mimetype="application/xml")
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response

    @app.get("/healthz")
    def healthz():
        return Response("ok\n", mimetype="text/plain")

    @app.get("/status.json")
    def status_json():
        return {
            "app_env": app.config.get('APP_ENV'),
            "force_https": bool(app.config.get('FORCE_HTTPS')),
            "cac_auth_enabled": bool(app.config.get('CAC_AUTH_ENABLED')),
            "public_self_register_enabled": bool(app.config.get('PUBLIC_SELF_REGISTER_ENABLED')),
            "request_host": request.host,
            "request_scheme": request.scheme,
        }

    @app.get("/tls-check")
    def tls_check():
        forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
        cf_visitor_raw = (request.headers.get('Cf-Visitor') or '').strip()
        cf_visitor_scheme = ''
        if cf_visitor_raw:
            try:
                parsed = json.loads(cf_visitor_raw)
                cf_visitor_scheme = (parsed.get('scheme') or '').strip().lower()
            except Exception:
                cf_visitor_scheme = ''
        payload = {
            "host": request.host,
            "url": request.url,
            "request_scheme": request.scheme,
            "request_is_secure": bool(request.is_secure),
            "x_forwarded_proto": forwarded_proto,
            "cf_visitor_scheme": cf_visitor_scheme,
            "cf_ray": request.headers.get('Cf-Ray', ''),
            "force_https": bool(app.config.get('FORCE_HTTPS', True)),
            "hsts_enabled": bool(app.config.get('HSTS_ENABLED', True)),
            "expected_public_url": f"https://{(request.host or 'mclbpd.com').split(':', 1)[0]}",
        }
        response = app.response_class(
            response=app.json.dumps(payload, indent=2),
            status=200,
            mimetype='application/json',
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.get("/reachability.txt")
    def reachability_txt():
        build_label = "ops-live"
        lines = [
            "mclbpd portal reachable",
            f"build={build_label}",
            f"pid={app.config.get('PROCESS_PID')}",
            f"started_at_utc={app.config.get('PROCESS_STARTED_AT_UTC')}",
            f"host={request.host}",
            f"scheme={request.scheme}",
        ]
        response = Response("\n".join(lines) + "\n", mimetype="text/plain")
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-MCLBPD-Build'] = build_label
        response.headers['X-MCLBPD-PID'] = str(app.config.get('PROCESS_PID'))
        response.headers['X-MCLBPD-Started-At-UTC'] = str(app.config.get('PROCESS_STARTED_AT_UTC'))
        return response

    @app.get("/reachability")
    def reachability_html():
        build_label = "ops-live"
        response = Response(
            (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<title>Reachability</title></head><body>"
                "<h1>MCLBPD Reachability OK</h1>"
                f"<p>Build: {build_label}</p>"
                f"<p>PID: {app.config.get('PROCESS_PID')}</p>"
                f"<p>Started: {app.config.get('PROCESS_STARTED_AT_UTC')}</p>"
                f"<p>Host: {request.host}</p>"
                f"<p>Scheme: {request.scheme}</p>"
                "</body></html>"
            ),
            mimetype="text/html",
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-MCLBPD-Build'] = build_label
        response.headers['X-MCLBPD-PID'] = str(app.config.get('PROCESS_PID'))
        response.headers['X-MCLBPD-Started-At-UTC'] = str(app.config.get('PROCESS_STARTED_AT_UTC'))
        return response

    @app.get("/probe.json")
    def probe_json():
        response = {
            "ok": True,
            "build": "ops-live",
            "pid": app.config.get('PROCESS_PID'),
            "started_at_utc": app.config.get('PROCESS_STARTED_AT_UTC'),
            "host": request.host,
            "scheme": request.scheme,
            "app_env": app.config.get('APP_ENV'),
        }
        flask_response = app.response_class(
            response=app.json.dumps(response),
            status=200,
            mimetype='application/json',
        )
        flask_response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        flask_response.headers['Pragma'] = 'no-cache'
        flask_response.headers['Expires'] = '0'
        flask_response.headers['X-MCLBPD-Build'] = 'ops-live'
        return flask_response

    @app.get("/version.json")
    def version_json():
        return {
            "pid": app.config.get('PROCESS_PID'),
            "started_at_utc": app.config.get('PROCESS_STARTED_AT_UTC'),
            "app_env": app.config.get('APP_ENV'),
            "request_host": request.host,
        }

    @app.before_request
    def enforce_https():
        forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()

        request_host = (request.host or '').split(':', 1)[0].strip().lower()
        if request_host == 'www.mclbpd.com':
            query = request.query_string.decode('utf-8', errors='ignore')
            target = f"https://mclbpd.com{request.path}"
            if query:
                target = f"{target}?{query}"
            if target == request.url:
                return None
            return redirect(target, code=301)

        if app.config.get('APP_ENV') != 'prod':
            return None
        if not app.config.get('FORCE_HTTPS', True):
            return None
        # Only enforce when a proxy explicitly reports original scheme as HTTP.
        # This avoids forcing local direct HTTP (127.0.0.1) into invalid HTTPS on Flask dev server.
        if forwarded_proto != 'http':
            return None
        host = (request.host or '').strip()
        if not host:
            return None
        query = request.query_string.decode('utf-8', errors='ignore')
        target = f"https://{host}{request.path}"
        if query:
            target = f"{target}?{query}"
        if target == request.url:
            return None
        return redirect(target, code=301)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault(
            'Permissions-Policy',
            'camera=(self), microphone=(), geolocation=(), payment=(), usb=()',
        )
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        if app.config.get('HSTS_ENABLED') and (request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https'):
            response.headers.setdefault(
                'Strict-Transport-Security',
                'max-age={}; includeSubDomains'.format(app.config.get('HSTS_MAX_AGE', 31536000)),
            )
        response.headers.setdefault('X-Robots-Tag', 'index, follow')
        return response

    @app.errorhandler(403)
    def forbidden(error):
        message = getattr(error, 'description', None) or 'You do not have access to this section.'
        return render_template('forbidden.html', error_message=message), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        logging.getLogger(__name__).error('Internal server error: %s', error, exc_info=True)
        return render_template('500.html'), 500

    @app.context_processor
    def inject_portal_context():
        host_display = (request.host or '').strip()
        port_display = ''
        if ':' in host_display:
            _, port_display = host_display.rsplit(':', 1)
        show_origin_banner = port_display not in {'', '80', '443', '5055'}

        if not getattr(current_user, 'is_authenticated', False):
            return {
                'role_labels': ROLE_LABELS,
                'portal_origin_label': host_display,
                'portal_show_origin_banner': show_origin_banner,
                'portal_write_limited_notice': 'Running in limited write mode' if app.config.get('APP_ENV') == 'prod' else '',
            }

        from .permissions import (
            can_access_armory,
            can_access_rfi,
            can_access_truck_gate,
            effective_role,
            is_site_controller,
            watch_commander_scope_id,
        )
        from .models import INSTALLATION_LABELS

        watch_commanders = (
            [
                user
                for user in User.query.filter(User.active.is_(True)).order_by(User.first_name, User.last_name, User.username).all()
                if user.has_role(ROLE_WATCH_COMMANDER)
            ]
        )
        active_role = effective_role(current_user)

        # Pending approval count — scoped by installation for non-site-controllers
        pending_approvals_count = 0
        if current_user.can_manage_team():
            try:
                q = User.query.filter_by(pending_approval=True, active=False)
                if not is_site_controller(current_user) and current_user.installation:
                    q = q.filter_by(installation=current_user.installation)
                pending_approvals_count = q.count()
            except Exception:
                pending_approvals_count = 0

        return {
            'role_labels': ROLE_LABELS,
            'portal_origin_label': host_display,
            'portal_show_origin_banner': show_origin_banner,
            'portal_write_limited_notice': 'Running in limited write mode' if app.config.get('APP_ENV') == 'prod' else '',
            'portal_effective_role': active_role,
            'portal_effective_role_label': ROLE_LABELS.get(active_role, current_user.role_label),
            'portal_is_site_controller': current_user.normalized_role == ROLE_WEBSITE_CONTROLLER,
            'portal_is_watch_commander_view': active_role == ROLE_WATCH_COMMANDER,
            'portal_watch_commanders': watch_commanders,
            'portal_watch_commander_scope_id': watch_commander_scope_id(current_user),
            'portal_role_keys': sorted(current_user.role_keys),
            'portal_can_access_armory': can_access_armory(current_user),
            'portal_can_access_truck_gate': can_access_truck_gate(current_user),
            'portal_can_access_rfi': can_access_rfi(current_user),
            'portal_pending_approvals': pending_approvals_count,
        }

    db.init_app(app)
    login_manager.init_app(app)

    from .routes import auth, assistant, bolo, dashboard, forms, training, qual_tracker, performance, stats, annual_ai, admin, cleo_api, reports, reconstruction, officers, ops_modules, legal, orders, reference, announcements, mobile
    app.register_blueprint(auth.bp)
    app.register_blueprint(assistant.bp)
    app.register_blueprint(bolo.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(forms.bp)
    app.register_blueprint(training.bp)
    app.register_blueprint(qual_tracker.bp)
    app.register_blueprint(performance.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(annual_ai.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(cleo_api.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(reconstruction.bp)
    app.register_blueprint(officers.bp)
    app.register_blueprint(ops_modules.bp)
    app.register_blueprint(legal.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(reference.bp)
    app.register_blueprint(announcements.bp)
    app.register_blueprint(mobile.bp)

    @app.get('/manifest.webmanifest')
    def pwa_manifest():
        return send_file(
            os.path.join(app.static_folder, 'manifest.webmanifest'),
            mimetype='application/manifest+json',
            max_age=3600,
        )

    @app.get('/service-worker.js')
    def service_worker():
        response = send_file(
            os.path.join(app.static_folder, 'service-worker.js'),
            mimetype='application/javascript',
            max_age=0,
        )
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control'] = 'no-cache'
        return response

    with app.app_context():
        try:
            db.create_all()
            ensure_schema()
            seed_roles()
            seed_admin()
        except OperationalError as exc:
            if 'readonly database' not in str(exc).lower():
                raise

    return app

