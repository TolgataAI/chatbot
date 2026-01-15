import streamlit as st
import json
import os
import uuid
import requests

# Configuration
NOTES_FILE = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'notes.json')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"

# Get secrets from Streamlit secrets or environment
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)

ADMIN_PASSWORD = get_secret('ADMIN_PASSWORD', 'admin123')
GEMINI_API_KEY = get_secret('GEMINI_API_KEY')

# Helper functions for JSON storage
def load_notes():
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_notes(notes):
    os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

def call_gemini(prompt):
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
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

def get_chat_response(user_message):
    notes = load_notes()
    notes_context = "\n\n".join([
        f"### {note.get('title', 'Note')}:\n{note['content']}"
        for note in notes
    ])

    full_prompt = f"""You are a friendly AI chatbot that represents a person. You should respond as if you ARE this person, using first person ("I", "my", "me").

Use the following personal information and knowledge to inform your responses. If asked about something not covered in these notes, you can say you're not sure or don't have that information.

--- PERSONAL NOTES ---
{notes_context if notes_context else "No personal notes available yet."}
--- END NOTES ---

Respond in a conversational, friendly manner. Keep responses concise but helpful.

User: {user_message}

Response:"""

    return call_gemini(full_prompt)

# Page config
st.set_page_config(
    page_title="Personal Chatbot",
    page_icon="💬",
    layout="centered"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["Chat", "Admin"])

if page == "Chat":
    st.title("💬 Chat with Me")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response, error = get_chat_response(prompt)
                if error:
                    st.error(error)
                    reply = f"Error: {error}"
                else:
                    st.write(response)
                    reply = response

        st.session_state.messages.append({"role": "assistant", "content": reply})

elif page == "Admin":
    st.title("🔐 Admin Panel")

    if not st.session_state.authenticated:
        st.subheader("Login")
        password = st.text_input("Enter admin password", type="password")
        if st.button("Login"):
            if password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid password")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Manage Your Notes")
        with col2:
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.rerun()

        # Add new note
        st.markdown("### Add New Note")
        with st.form("new_note_form"):
            new_title = st.text_input("Title (optional)")
            new_content = st.text_area("Content", placeholder="Write your note here...")
            submitted = st.form_submit_button("Add Note")

            if submitted and new_content.strip():
                notes = load_notes()
                notes.append({
                    'id': str(uuid.uuid4()),
                    'title': new_title.strip() or 'Untitled',
                    'content': new_content.strip()
                })
                save_notes(notes)
                st.success("Note added!")
                st.rerun()

        # Display existing notes
        st.markdown("### Your Notes")
        notes = load_notes()

        if not notes:
            st.info("No notes yet. Add your first note above!")
        else:
            for i, note in enumerate(notes):
                with st.expander(f"📝 {note['title']}", expanded=False):
                    st.write(note['content'])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Delete", key=f"del_{note['id']}"):
                            notes = [n for n in notes if n['id'] != note['id']]
                            save_notes(notes)
                            st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Personal Chatbot powered by Gemini")
