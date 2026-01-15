import os
import json
import uuid
import requests
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NOTES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'notes.json')

# Gemini API endpoint
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"

# Helper functions for JSON storage
def load_notes():
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_notes(notes):
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

def call_gemini(prompt):
    """Call Gemini API directly via HTTP"""
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            return None, f"API error: {response.status_code} - {response.text}"

        data = response.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        return text, None
    except Exception as e:
        return None, str(e)

# Simple token-based auth decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {ADMIN_PASSWORD}':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# Auth endpoint
@app.route('/api/auth', methods=['POST'])
def authenticate():
    data = request.get_json()
    password = data.get('password', '')

    if password == ADMIN_PASSWORD:
        return jsonify({'success': True, 'token': ADMIN_PASSWORD})
    return jsonify({'success': False, 'error': 'Invalid password'}), 401

# Notes CRUD endpoints
@app.route('/api/notes', methods=['GET'])
@require_auth
def get_notes():
    notes = load_notes()
    return jsonify(notes)

@app.route('/api/notes', methods=['POST'])
@require_auth
def create_note():
    data = request.get_json()
    content = data.get('content', '').strip()
    title = data.get('title', '').strip()

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    notes = load_notes()
    new_note = {
        'id': str(uuid.uuid4()),
        'title': title or 'Untitled',
        'content': content
    }
    notes.append(new_note)
    save_notes(notes)

    return jsonify(new_note), 201

@app.route('/api/notes/<note_id>', methods=['PUT'])
@require_auth
def update_note(note_id):
    data = request.get_json()
    content = data.get('content', '').strip()
    title = data.get('title', '').strip()

    if not content:
        return jsonify({'error': 'Content is required'}), 400

    notes = load_notes()
    for note in notes:
        if note['id'] == note_id:
            note['content'] = content
            note['title'] = title or note.get('title', 'Untitled')
            save_notes(notes)
            return jsonify(note)

    return jsonify({'error': 'Note not found'}), 404

@app.route('/api/notes/<note_id>', methods=['DELETE'])
@require_auth
def delete_note(note_id):
    notes = load_notes()
    original_length = len(notes)
    notes = [n for n in notes if n['id'] != note_id]

    if len(notes) == original_length:
        return jsonify({'error': 'Note not found'}), 404

    save_notes(notes)
    return jsonify({'success': True})

# Chat endpoint (public)
@app.route('/api/chat', methods=['POST'])
def chat():
    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API key not configured'}), 500

    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    # Load notes to build context
    notes = load_notes()
    notes_context = "\n\n".join([
        f"### {note.get('title', 'Note')}:\n{note['content']}"
        for note in notes
    ])

    # Build the prompt
    full_prompt = f"""You are a friendly AI chatbot that represents a person. You should respond as if you ARE this person, using first person ("I", "my", "me").

Use the following personal information and knowledge to inform your responses. If asked about something not covered in these notes, you can say you're not sure or don't have that information.

--- PERSONAL NOTES ---
{notes_context if notes_context else "No personal notes available yet."}
--- END NOTES ---

Respond in a conversational, friendly manner. Keep responses concise but helpful.

User: {user_message}

Response:"""

    response_text, error = call_gemini(full_prompt)

    if error:
        return jsonify({'error': error}), 500

    return jsonify({'response': response_text})

# Health check
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'gemini_configured': GEMINI_API_KEY is not None
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
