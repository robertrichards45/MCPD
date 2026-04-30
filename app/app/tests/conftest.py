import gc

import pytest

from app import _CREATED_APPS
from app.extensions import db


@pytest.fixture(autouse=True)
def cleanup_created_apps():
    yield
    for flask_app in list(_CREATED_APPS):
        try:
            with flask_app.app_context():
                db.session.remove()
                db.engine.dispose()
        except Exception:
            pass
    gc.collect()
