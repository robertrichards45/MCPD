import logging
import os
from datetime import datetime, timezone

from sqlalchemy import func, text

# Prevent create_app() from resetting an existing controller password from the
# Railway ADMIN_PASSWORD variable on every deployment.
os.environ.pop('ADMIN_PASSWORD', None)

from app import create_app
from app.extensions import db
from app.models import ROLE_WEBSITE_CONTROLLER, User

app = create_app()


def _apply_one_time_controller_recovery():
    """Restore the controller password once and record completion in the DB."""
    migration_key = 'controller-password-recovery-2026-07-19'
    target_username = 'robertrichards45'
    temporary_password_hash = (
        'pbkdf2:sha256:600000$1e65789878e2f220$'
        'a2ded501041f847d1fe9d16ce5df164edf8d923df3c8899861f97ed7da022d57'
    )

    with app.app_context():
        try:
            db.session.execute(text(
                'CREATE TABLE IF NOT EXISTS bootstrap_migration ('
                'migration_key VARCHAR(120) PRIMARY KEY, '
                'applied_at VARCHAR(40) NOT NULL)'
            ))
            already_applied = db.session.execute(
                text('SELECT migration_key FROM bootstrap_migration WHERE migration_key = :key'),
                {'key': migration_key},
            ).first()
            if already_applied:
                db.session.commit()
                return

            user = User.query.filter(func.lower(User.username) == target_username.lower()).first()
            if user is None:
                user = User(
                    username=target_username,
                    role=ROLE_WEBSITE_CONTROLLER,
                    active=True,
                    pending_approval=False,
                    password_hash=temporary_password_hash,
                )
                db.session.add(user)
            else:
                user.role = ROLE_WEBSITE_CONTROLLER
                user.active = True
                user.pending_approval = False
                user.password_hash = temporary_password_hash

            db.session.flush()
            db.session.execute(
                text(
                    'INSERT INTO bootstrap_migration (migration_key, applied_at) '
                    'VALUES (:key, :applied_at)'
                ),
                {
                    'key': migration_key,
                    'applied_at': datetime.now(timezone.utc).isoformat(),
                },
            )
            db.session.commit()
            logging.getLogger(__name__).warning(
                'Applied one-time Website Controller account recovery for %s.',
                target_username,
            )
        except Exception:
            db.session.rollback()
            logging.getLogger(__name__).exception(
                'One-time Website Controller account recovery failed.'
            )


_apply_one_time_controller_recovery()
