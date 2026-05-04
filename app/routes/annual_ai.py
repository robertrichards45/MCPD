from flask import Blueprint, render_template, request, current_app
from flask_login import login_required, current_user
from ..extensions import db
from ..models import AuditLog
import os

# Import OpenAI correctly
from openai import OpenAI

bp = Blueprint('annual_ai', __name__)

# Initialize client using Railway environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
            answer="No question provided.",
            question=question
        )

    try:
        # 🔥 ACTUAL AI CALL
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an MCPD law enforcement assistant helping with reports, training, and procedures."
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        answer = response.choices[0].message.content

    except Exception as e:
        answer = f"AI ERROR: {str(e)}"

    # Log usage
    try:
        db.session.add(
            AuditLog(
                actor_id=current_user.id,
                action='annual_ai',
                details=question[:200]
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    return render_template(
        'annual_ai.html',
        user=current_user,
        answer=answer,
        question=question
    )