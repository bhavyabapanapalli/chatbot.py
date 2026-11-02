
import os
import time
import uuid
import hmac
import hashlib
import secrets
import sqlite3
import streamlit as st

from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# 1. CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Gemini AI Assistant",
    page_icon="🤖",
    layout="wide"
)

DB_NAME = "chat_history.db"
PBKDF2_ITERATIONS = 310000

load_dotenv(override=True)
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("Gemini API key not found. Check your .env file.")
    st.stop()

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(timeout=120000)
)


# ==========================================
# 2. DATABASE
# ==========================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        columns = [
            row[1] for row in
            conn.execute("PRAGMA table_info(conversations)")
        ]

        if "user_id" not in columns:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN user_id INTEGER"
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE
            )
        """)


initialize_database()


# ==========================================
# 3. PASSWORD SECURITY
# ==========================================

def hash_password(password, salt):

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    )

    return hashed.hex()


def register_user(username, password):

    username = username.strip().lower()

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if not username.replace("_", "").isalnum():
        return False, "Use letters, numbers and underscores only."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    salt = secrets.token_bytes(16).hex()
    password_hash = hash_password(password, salt)

    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO users
                (username, password_hash, salt, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                username,
                password_hash,
                salt,
                datetime.now().isoformat()
            ))

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "Username already exists."

    except sqlite3.Error:
        return False, "Database error. Please try again."


def authenticate_user(username, password):

    username = username.strip().lower()

    with get_connection() as conn:
        user = conn.execute("""
            SELECT id, username, password_hash, salt
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

    if not user:
        return None

    user_id, stored_username, stored_hash, salt = user
    entered_hash = hash_password(password, salt)

    if hmac.compare_digest(entered_hash, stored_hash):
        return {
            "id": user_id,
            "username": stored_username
        }

    return None


# ==========================================
# 4. PROFILE DATABASE FUNCTIONS
# ==========================================

def get_user_details(user_id):

    with get_connection() as conn:
        return conn.execute("""
            SELECT username, created_at
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()


def change_username(user_id, new_username):

    new_username = new_username.strip().lower()

    if len(new_username) < 3:
        return False, "Username must contain at least 3 characters."

    if not new_username.replace("_", "").isalnum():
        return False, "Use letters, numbers and underscores only."

    try:
        with get_connection() as conn:
            conn.execute("""
                UPDATE users
                SET username = ?
                WHERE id = ?
            """, (new_username, user_id))

        return True, "Username updated successfully."

    except sqlite3.IntegrityError:
        return False, "This username is already taken."

    except sqlite3.Error:
        return False, "Database error. Please try again."


def change_password(user_id, current_password, new_password):

    with get_connection() as conn:
        user = conn.execute("""
            SELECT password_hash, salt
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

    if not user:
        return False, "Account not found."

    stored_hash, salt = user
    entered_hash = hash_password(current_password, salt)

    if not hmac.compare_digest(entered_hash, stored_hash):
        return False, "Current password is incorrect."

    if len(new_password) < 8:
        return False, "New password must contain at least 8 characters."

    new_salt = secrets.token_bytes(16).hex()
    new_hash = hash_password(new_password, new_salt)

    with get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET password_hash = ?, salt = ?
            WHERE id = ?
        """, (new_hash, new_salt, user_id))

    return True, "Password changed successfully."


# ==========================================
# 5. CHAT DATABASE FUNCTIONS
# ==========================================

def create_chat(user_id):

    chat_id = str(uuid.uuid4())

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO conversations
            (id, title, created_at, user_id)
            VALUES (?, ?, ?, ?)
        """, (
            chat_id,
            "New Conversation",
            datetime.now().isoformat(),
            user_id
        ))

    return chat_id


def get_all_chats(user_id):

    with get_connection() as conn:
        return conn.execute("""
            SELECT id, title
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()


def get_messages(chat_id, user_id):

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT m.role, m.content
            FROM messages m
            JOIN conversations c ON c.id = m.chat_id
            WHERE c.id = ? AND c.user_id = ?
            ORDER BY m.id ASC
        """, (chat_id, user_id)).fetchall()

    return [
        {"role": role, "content": content}
        for role, content in rows
    ]


def save_message(chat_id, user_id, role, content):

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO messages
            (chat_id, role, content, created_at)
            SELECT id, ?, ?, ?
            FROM conversations
            WHERE id = ? AND user_id = ?
        """, (
            role,
            content,
            datetime.now().isoformat(),
            chat_id,
            user_id
        ))


def update_chat_title(chat_id, user_id, title):

    with get_connection() as conn:
        conn.execute("""
            UPDATE conversations
            SET title = ?
            WHERE id = ? AND user_id = ?
        """, (title[:40], chat_id, user_id))


def delete_chat(chat_id, user_id):

    with get_connection() as conn:
        conn.execute("""
            DELETE FROM conversations
            WHERE id = ? AND user_id = ?
        """, (chat_id, user_id))


def clear_user_chats(user_id):

    with get_connection() as conn:
        conn.execute("""
            DELETE FROM messages
            WHERE chat_id IN (
                SELECT id FROM conversations
                WHERE user_id = ?
            )
        """, (user_id,))

        conn.execute("""
            DELETE FROM conversations
            WHERE user_id = ?
        """, (user_id,))


# ==========================================
# 6. GEMINI RESPONSE
# ==========================================

def get_response(messages):

    contents = []

    for message in messages:

        role = (
            "user"
            if message["role"] == "user"
            else "model"
        )

        contents.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })

    for attempt in range(2):

        try:

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a helpful AI assistant. "
                        "Give accurate and clear answers. "
                        "Explain concepts simply with examples."
                    ),
                    temperature=0.7,
                    max_output_tokens=1500
                )
            )

            return response.text or "No response generated."

        except Exception as error:

            error_message = str(error)

            if attempt == 0 and any(
                code in error_message
                for code in ["503", "504"]
            ):
                time.sleep(3)
                continue

            return f"Gemini API Error: {error_message}"

    return "Please try again later."


# ==========================================
# 7. SESSION STATE
# ==========================================

if "user" not in st.session_state:
    st.session_state.user = None

if "active_chat" not in st.session_state:
    st.session_state.active_chat = None

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if "page" not in st.session_state:
    st.session_state.page = "Chat"


# ==========================================
# 8. LOGIN AND SIGNUP
# ==========================================

if st.session_state.user is None:

    st.title("Gemini AI Assistant")
    st.caption("Sign in to access your personal AI chatbot.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:

        with st.form("login_form"):

            st.subheader("Welcome Back")

            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password"
            )

            login_button = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if login_button:

            user = authenticate_user(username, password)

            if user:
                st.session_state.user = user
                st.session_state.active_chat = None
                st.session_state.page = "Chat"
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with signup_tab:

        with st.form("signup_form"):

            st.subheader("Create Account")

            new_username = st.text_input("Choose Username")
            new_password = st.text_input(
                "Choose Password",
                type="password"
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            signup_button = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if signup_button:

            if new_password != confirm_password:
                st.error("Passwords do not match.")

            else:

                success, message = register_user(
                    new_username,
                    new_password
                )

                if success:
                    st.success(message + " Please login.")
                else:
                    st.error(message)

    st.stop()


# ==========================================
# 9. AUTHENTICATED USER
# ==========================================

user = st.session_state.user
user_id = user["id"]

if st.session_state.active_chat is None:

    chats = get_all_chats(user_id)

    if chats:
        st.session_state.active_chat = chats[0][0]
    else:
        st.session_state.active_chat = create_chat(user_id)


# ==========================================
# 10. THEME
# ==========================================

if st.session_state.dark_mode:

    bg = "#0f172a"
    sidebar_bg = "#111827"
    text_color = "#f8fafc"
    border_color = "#334155"
    muted = "#94a3b8"

else:

    bg = "#ffffff"
    sidebar_bg = "#f5f6fa"
    text_color = "#1e293b"
    border_color = "#e2e8f0"
    muted = "#64748b"


st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {bg};
        color: {text_color};
    }}

    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
        border-right: 1px solid {border_color};
    }}

    [data-testid="stChatMessage"] {{
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 12px;
    }}

    .main-title {{
        color: {text_color};
        font-size: 36px;
        font-weight: 750;
    }}

    .subtitle {{
        color: {muted};
        margin-bottom: 25px;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================
# 11. SIDEBAR NAVIGATION
# ==========================================

with st.sidebar:

    st.title("Gemini AI")
    st.write(f"Logged in as **{user['username']}**")

    st.divider()

    st.subheader("Navigation")

    if st.button("Chat", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()

    if st.button("My Profile", use_container_width=True):
        st.session_state.page = "Profile"
        st.rerun()

    st.divider()

    if st.session_state.page == "Chat":

        if st.button("+ New Chat", use_container_width=True):
            st.session_state.active_chat = create_chat(user_id)
            st.rerun()

        st.subheader("Chat History")

        chats = get_all_chats(user_id)

        for chat_id, title in chats:

            col1, col2 = st.columns([5, 1])

            with col1:

                if st.button(
                    title,
                    key=f"chat_{chat_id}",
                    use_container_width=True,
                    type=(
                        "primary"
                        if chat_id == st.session_state.active_chat
                        else "secondary"
                    )
                ):
                    st.session_state.active_chat = chat_id
                    st.rerun()

            with col2:

                if st.button(
                    "🗑️",
                    key=f"delete_{chat_id}",
                    help="Delete conversation"
                ):

                    delete_chat(chat_id, user_id)

                    if st.session_state.active_chat == chat_id:

                        remaining = get_all_chats(user_id)

                        if remaining:
                            st.session_state.active_chat = remaining[0][0]
                        else:
                            st.session_state.active_chat = create_chat(user_id)

                    st.rerun()

    st.divider()

    theme_label = (
        "Switch to Light Mode"
        if st.session_state.dark_mode
        else "Switch to Dark Mode"
    )

    if st.button(theme_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    if st.session_state.page == "Chat":

        if st.button("Clear My Chats", use_container_width=True):
            clear_user_chats(user_id)
            st.session_state.active_chat = create_chat(user_id)
            st.rerun()

    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.active_chat = None
        st.session_state.page = "Chat"
        st.rerun()

    st.divider()
    st.caption("Powered by Google Gemini")
    st.caption("Storage: SQLite Database")


# ==========================================
# 12. PROFILE MANAGEMENT
# ==========================================

if st.session_state.page == "Profile":

    st.markdown(
        '<div class="main-title">My Profile</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Manage your account details and security.</div>',
        unsafe_allow_html=True
    )

    details = get_user_details(user_id)

    if details:

        current_username, created_at = details

        st.subheader("Account Information")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Username", current_username)

        with col2:
            formatted_date = datetime.fromisoformat(
                created_at
            ).strftime("%d %b %Y")

            st.metric("Member Since", formatted_date)

        st.divider()

        # Change username
        st.subheader("Change Username")

        with st.form("username_form"):

            new_username = st.text_input(
                "New Username",
                value=current_username
            )

            username_submit = st.form_submit_button(
                "Update Username"
            )

        if username_submit:

            success, message = change_username(
                user_id,
                new_username
            )

            if success:

                st.session_state.user["username"] = (
                    new_username.strip().lower()
                )

                st.success(message)
                st.rerun()

            else:
                st.error(message)

        st.divider()

        # Change password
        st.subheader("Change Password")

        with st.form("password_form"):

            current_password = st.text_input(
                "Current Password",
                type="password"
            )

            new_password = st.text_input(
                "New Password",
                type="password"
            )

            confirm_new_password = st.text_input(
                "Confirm New Password",
                type="password"
            )

            password_submit = st.form_submit_button(
                "Change Password"
            )

        if password_submit:

            if new_password != confirm_new_password:

                st.error("New passwords do not match.")

            elif not new_password:

                st.error("Enter a new password.")

            else:

                success, message = change_password(
                    user_id,
                    current_password,
                    new_password
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

        st.divider()

        st.info(
            "Your chat history and account details are stored "
            "in the local SQLite database."
        )


# ==========================================
# 13. MAIN CHAT PAGE
# ==========================================

if st.session_state.page == "Chat":

    st.markdown(
        '<div class="main-title">Gemini AI Assistant</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Your personal intelligent AI assistant.'
        '</div>',
        unsafe_allow_html=True
    )

    active_id = st.session_state.active_chat

    messages = get_messages(active_id, user_id)

    if not messages:

        st.info(
            f"Welcome {user['username']}! "
            "Ask me anything to start a conversation."
        )

    for message in messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Message Gemini AI..."):

        save_message(active_id, user_id, "user", prompt)

        if not messages:
            update_chat_title(active_id, user_id, prompt)

        with st.chat_message("user"):
            st.markdown(prompt)

        updated_messages = get_messages(active_id, user_id)

        with st.chat_message("assistant"):

            with st.spinner("Gemini is thinking..."):
                answer = get_response(updated_messages)

            st.markdown(answer)

        save_message(active_id, user_id, "assistant", answer)


# ==========================================
# 14. FOOTER
# ==========================================

st.caption(
    "Gemini AI Assistant | Python | Streamlit | SQLite"
)
