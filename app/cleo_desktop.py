import os
import threading
import webbrowser

from dotenv import load_dotenv

load_dotenv(override=True)


def _desktop_defaults():
    data_root = os.path.join(
        os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'),
        'MCPD-CLEOC-Desktop',
    )
    os.makedirs(data_root, exist_ok=True)
    os.makedirs(os.path.join(data_root, 'uploads'), exist_ok=True)

    os.environ.setdefault('APP_ENV', 'dev')
    os.environ.setdefault('TRUST_PROXY', '0')
    os.environ.setdefault('FORCE_HTTPS', '0')
    os.environ.setdefault('HSTS_ENABLED', '0')
    os.environ.setdefault('CAC_AUTH_ENABLED', '0')
    os.environ.setdefault('CAC_AUTO_REGISTER', '0')
    os.environ.setdefault('PUBLIC_SELF_REGISTER_ENABLED', '0')
    os.environ.setdefault('PREFERRED_URL_SCHEME', 'http')
    os.environ.setdefault('PORT', '8092')
    os.environ.setdefault('CLEOC_BIND', '127.0.0.1')
    os.environ.setdefault('CLEOC_OPEN_BROWSER', '1')
    os.environ.setdefault('CLEOC_START_PATH', '/cleo/reports')
    os.environ.setdefault('UPLOAD_ROOT', os.path.join(data_root, 'uploads'))
    os.environ.setdefault('DATABASE_URL', f"sqlite:///{os.path.join(data_root, 'cleo-desktop.db').replace(os.sep, '/')}")
    os.environ.setdefault('SECRET_KEY', 'cleo-desktop-local')
    os.environ.setdefault('ADMIN_USERNAME', 'admin')
    os.environ.setdefault('ADMIN_PASSWORD', 'ChangeMe123!')


_desktop_defaults()

from app import create_app


def _launch_url(port):
    start_path = os.environ.get('CLEOC_START_PATH', '/cleo/reports').strip() or '/cleo/reports'
    if not start_path.startswith('/'):
        start_path = '/' + start_path
    return f"http://127.0.0.1:{port}{start_path}"


def _open_browser_later(port):
    if os.environ.get('CLEOC_OPEN_BROWSER', '1').strip().lower() not in {'1', 'true', 'yes', 'on'}:
        return

    def _open():
        webbrowser.open(_launch_url(port), new=1)

    timer = threading.Timer(1.5, _open)
    timer.daemon = True
    timer.start()


app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8092'))
    bind_host = os.environ.get('CLEOC_BIND', '127.0.0.1').strip() or '127.0.0.1'
    _open_browser_later(port)

    try:
        from waitress import serve
        serve(app, host=bind_host, port=port, threads=8)
    except Exception:
        app.run(host=bind_host, port=port, debug=False, threaded=True)
