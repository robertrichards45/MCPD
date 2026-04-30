import os
from dotenv import load_dotenv

load_dotenv(override=False)

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8091'))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes', 'on'}
    ssl_mode = os.environ.get('SSL_MODE', '').strip().lower()
    ssl_context = 'adhoc' if ssl_mode == 'adhoc' else None
    app.run(debug=debug, host='0.0.0.0', port=port, use_reloader=debug, ssl_context=ssl_context)
