from flask import Blueprint, render_template, request, current_app
from flask_login import login_required, current_user
from ..services.ai_client import ask_openai
from ..extensions import db
from ..models import AuditLog

bp = Blueprint('annual_ai', __name__)

@bp.route('/annual-training-ai', methods=['GET'])
@login_required
def page():
    return render_template('annual_ai.html', user=current_user, answer=None, question=None)

@bp.route('/annual-training-ai/ask', methods=['POST'])
@login_required
def ask():
    question = request.form.get('question', '')
    answer = ask_openai(question, current_app.config['OPENAI_API_KEY'])
    db.session.add(AuditLog(actor_id=current_user.id, action='annual_ai', details=question[:200]))
    db.session.commit()
    return render_template('annual_ai.html', user=current_user, answer=answer, question=question)
