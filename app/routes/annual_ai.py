from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import AuditLog
from ..services.ai_client import ask_openai_with_system, is_ai_unavailable_message


bp = Blueprint('annual_ai', __name__)


@bp.route('/annual-training-ai', methods=['GET'])
@login_required
def page():
    return render_template('annual_ai.html', user=current_user, answer=None, question=None)


@bp.route('/annual-training-ai/ask', methods=['POST'])
@login_required
def ask():
    question = request.form.get('question', '').strip()

    if not question:
        return render_template(
            'annual_ai.html',
            user=current_user,
            answer='No question provided.',
            question=question,
        )

    answer = ask_openai_with_system(
        question,
        'You are an MCPD law enforcement assistant helping with reports, training, and procedures.',
        api_key=current_app.config.get('OPENAI_API_KEY', ''),
    )
    if is_ai_unavailable_message(answer):
        answer = (
            'AI assist is not configured right now. You can still use Law Lookup, Orders, Forms, '
            'and the Paperwork Navigator from the command sidebar.'
        )

    try:
        db.session.add(
            AuditLog(
                actor_id=current_user.id,
                action='annual_ai',
                details=question[:200],
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    return render_template(
        'annual_ai.html',
        user=current_user,
        answer=answer,
        question=question,
    )
