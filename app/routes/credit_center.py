from flask import Blueprint, render_template
from flask_login import current_user, login_required

bp = Blueprint('credit_center', __name__, url_prefix='/credit-center')


@bp.get('/')
@login_required
def dashboard():
    return render_template(
        'credit_center/dashboard.html',
        title='Credit Center',
        user=current_user,
    )
