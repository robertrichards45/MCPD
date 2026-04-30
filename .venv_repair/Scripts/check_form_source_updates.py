"""Check official-source URLs for forms with auto-update enabled.

Run from the project root:
    .venv\\Scripts\\python.exe scripts\\check_form_source_updates.py --apply

Only direct HTTPS PDF URLs on the official allow-list are accepted. Gated DSO
storefront/login pages are reported and never applied as form replacements.
"""

from __future__ import annotations

import argparse

from app import create_app
from app.extensions import db
from app.models import AuditLog, Form
from app.routes.forms import _resolve_storage_path, _utcnow_naive
from app.services.form_source_updates import check_and_update_form_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply official PDF updates when a direct newer PDF is available.')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        storage_dir = _resolve_storage_path(app.config['FORMS_UPLOAD'])
        forms = (
            Form.query
            .filter(Form.source_auto_update_enabled.is_(True))
            .filter(Form.official_source_url.isnot(None))
            .order_by(Form.title.asc())
            .all()
        )
        for form in forms:
            result = check_and_update_form_source(form, storage_dir, apply_update=args.apply)
            form.official_source_last_checked_at = _utcnow_naive()
            form.official_source_last_status = f'{result.status}: {result.message}'
            if result.sha256_hash:
                form.official_source_hash = result.sha256_hash
            if result.downloaded and result.new_path:
                form.file_path = result.new_path
                form.uploaded_at = _utcnow_naive()
            db.session.add(AuditLog(actor_id=None, action='form_official_source_auto_update', details=f'{form.title}|{result.status}|{result.source_url}'))
            print(f'{form.id}: {form.title} - {result.status} - {result.message}')
        db.session.commit()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

