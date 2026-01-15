import os
import json
import uuid
import requests
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)

# Configuration
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NOTES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'notes.json')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Ensure data directory exists
os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)

# HTML Templates
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Personal Chatbot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; min-height: 100vh; }
        .navbar { background: #2563eb; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .navbar a { color: white; text-decoration: none; margin-left: 1.5rem; opacity: 0.9; }
        .navbar a:hover { opacity: 1; }
        .container { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 2rem; margin-bottom: 1.5rem; }
        h1, h2, h3 { color: #1f2937; margin-bottom: 1rem; }
        input[type="text"], input[type="password"], textarea { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem; margin-bottom: 1rem; }
        textarea { min-height: 100px; resize: vertical; }
        button, .btn { padding: 0.75rem 1.5rem; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; text-decoration: none; display: inline-block; }
        button:hover, .btn:hover { background: #1d4ed8; }
        .btn-danger { background: #dc2626; }
        .btn-danger:hover { background: #b91c1c; }
        .btn-secondary { background: #6b7280; }
        .note-item { background: #f9fafb; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #2563eb; }
        .note-item h4 { margin-bottom: 0.5rem; }
        .note-item p { color: #4b5563; white-space: pre-wrap; margin-bottom: 0.5rem; }
        .chat-container { height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; background: #fafafa; }
        .message { max-width: 80%; padding: 0.75rem 1rem; border-radius: 12px; margin-bottom: 0.5rem; }
        .message.user { background: #2563eb; color: white; margin-left: auto; }
        .message.bot { background: #e5e7eb; }
        .message.error { background: #fef2f2; color: #dc2626; }
        .chat-form { display: flex; gap: 0.5rem; }
        .chat-form input { flex: 1; margin-bottom: 0; }
        .error { color: #dc2626; margin-bottom: 1rem; }
        .success { color: #059669; margin-bottom: 1rem; }
        .actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <nav class="navbar">
        <span style="font-weight: 600; font-size: 1.25rem;">Personal Chatbot</span>
        <div>
            <a href="/">Chat</a>
            <a href="/admin">Admin</a>
        </div>
    </nav>
    <div class="container">
        {{ content | safe }}
    </div>
</body>
</html>
'''

CHAT_TEMPLATE = '''
<div class="card">
    <h2>Chat with Me</h2>
    <div class="chat-container" id="chatContainer">
        <p style="color: #6b7280; text-align: center;">Start a conversation!</p>
    </div>
    <form class="chat-form" id="chatForm">
        <input type="text" id="messageInput" placeholder="Type your message..." autocomplete="off">
        <button type="submit">Send</button>
    </form>
</div>

<script>
const chatContainer = document.getElementById('chatContainer');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
let firstMessage = true;

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;

    if (firstMessage) {
        chatContainer.innerHTML = '';
        firstMessage = false;
    }

    // Add user message
    chatContainer.innerHTML += `<div class="message user">${escapeHtml(message)}</div>`;
    messageInput.value = '';
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Add loading message
    const loadingId = 'loading-' + Date.now();
    chatContainer.innerHTML += `<div class="message bot" id="${loadingId}">Thinking...</div>`;
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await response.json();

        document.getElementById(loadingId).remove();

        if (data.error) {
            chatContainer.innerHTML += `<div class="message error">${escapeHtml(data.error)}</div>`;
        } else {
            chatContainer.innerHTML += `<div class="message bot">${escapeHtml(data.response)}</div>`;
        }
    } catch (err) {
        document.getElementById(loadingId).remove();
        chatContainer.innerHTML += `<div class="message error">Failed to send message</div>`;
    }
    chatContainer.scrollTop = chatContainer.scrollHeight;
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
</script>
'''

LOGIN_TEMPLATE = '''
<div class="card" style="max-width: 400px; margin: 4rem auto;">
    <h2>Admin Login</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="POST">
        <input type="password" name="password" placeholder="Enter admin password" required>
        <button type="submit" style="width: 100%;">Login</button>
    </form>
</div>
'''

ADMIN_TEMPLATE = '''
<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h2>Manage Your Notes</h2>
        <a href="/logout" class="btn btn-secondary">Logout</a>
    </div>

    <h3>Add New Note</h3>
    <form method="POST" action="/admin/add">
        <input type="text" name="title" placeholder="Title (optional)">
        <textarea name="content" placeholder="Write your note here..." required></textarea>
        <button type="submit">Add Note</button>
    </form>
</div>

<div class="card">
    <h3>Your Notes ({{ notes|length }})</h3>
    {% if notes %}
        {% for note in notes %}
        <div class="note-item">
            <h4>{{ note.title }}</h4>
            <p>{{ note.content }}</p>
            <div class="actions">
                <form method="POST" action="/admin/delete/{{ note.id }}" style="display: inline;">
                    <button type="submit" class="btn-danger" onclick="return confirm('Delete this note?')">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #6b7280;">No notes yet. Add your first note above!</p>
    {% endif %}
</div>
'''

# Helper functions
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
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"

    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

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
        return data['candidates'][0]['content']['parts'][0]['text'], None
    except Exception as e:
        return None, str(e)

def render(title, content):
    from jinja2 import Template
    return Template(BASE_TEMPLATE).render(title=title, content=content)

# Routes
@app.route('/')
def chat_page():
    return render('Chat', CHAT_TEMPLATE)

@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('admin_page'))
        else:
            from jinja2 import Template
            content = Template(LOGIN_TEMPLATE).render(error='Invalid password')
            return render('Login', content)

    if not session.get('authenticated'):
        from jinja2 import Template
        content = Template(LOGIN_TEMPLATE).render(error=None)
        return render('Login', content)

    from jinja2 import Template
    notes = load_notes()
    content = Template(ADMIN_TEMPLATE).render(notes=notes)
    return render('Admin', content)

@app.route('/admin/add', methods=['POST'])
def add_note():
    if not session.get('authenticated'):
        return redirect(url_for('admin_page'))

    title = request.form.get('title', '').strip() or 'Untitled'
    content = request.form.get('content', '').strip()

    if content:
        notes = load_notes()
        notes.append({'id': str(uuid.uuid4()), 'title': title, 'content': content})
        save_notes(notes)

    return redirect(url_for('admin_page'))

@app.route('/admin/delete/<note_id>', methods=['POST'])
def delete_note(note_id):
    if not session.get('authenticated'):
        return redirect(url_for('admin_page'))

    notes = load_notes()
    notes = [n for n in notes if n['id'] != note_id]
    save_notes(notes)
    return redirect(url_for('admin_page'))

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('admin_page'))

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    notes = load_notes()
    notes_context = "\n\n".join([
        f"### {note.get('title', 'Note')}:\n{note['content']}"
        for note in notes
    ])

    full_prompt = f"""You are a helpful AI assistant. Answer questions naturally and accurately, just like a regular AI assistant would.

You also have access to some personal notes from your owner. When questions relate to this personal information, use it to personalize your responses. For general knowledge questions, answer normally using your training.

--- PERSONAL NOTES (use when relevant) ---
{notes_context if notes_context else "No personal notes available yet."}
--- END NOTES ---

Be helpful, friendly, and accurate. Answer all questions to the best of your ability.

User: {user_message}

Response:"""

    response_text, error = call_gemini(full_prompt)
    if error:
        return jsonify({'error': error}), 500
    return jsonify({'response': response_text})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'gemini_configured': GEMINI_API_KEY is not None})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
