import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import MODEL_NAME, SYSTEM_PROMPT

load_dotenv()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def build_contents(messages):
    contents = []
    for message in messages[-20:]:
        role = message.get("role")
        text = str(message.get("content", "")).strip()
        if not text or role not in {"user", "model"}:
            continue
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=text)],
            )
        )
    return contents


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])

    if not isinstance(messages, list):
        return jsonify({"error": "Invalid message format."}), 400

    contents = build_contents(messages)
    if not contents:
        return jsonify({"error": "Please enter a cybersecurity question."}), 400

    if client is None:
        return jsonify({"error": "GEMINI_API_KEY is not configured."}), 500

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=1200,
            ),
        )

        answer = (response.text or "").strip()
        if not answer:
            answer = "I could not generate a response. Please try a different cybersecurity question."

        return jsonify({"answer": answer})
    except Exception:
        app.logger.exception("Gemini API request failed")
        return jsonify({"error": "The AI service is temporarily unavailable. Please try again."}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
