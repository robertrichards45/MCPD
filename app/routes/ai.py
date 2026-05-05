from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

ai = Blueprint('ai', __name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@ai.route('/ai-chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    user_input = data.get("message")

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an MCPD law enforcement assistant."},
                {"role": "user", "content": user_input}
            ]
        )

        return jsonify({
            "response": response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500