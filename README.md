# Gemini AI Chatbot

A conversational AI chatbot powered by Google's Gemini API, built using Python and Streamlit. It provides an interactive chat experience with user authentication, persistent conversation history, and profile management.

## Features

- **Gemini AI Integration** – Generate intelligent responses using Google's Gemini API.
- **Interactive Chat Interface** – Chat through a clean, ChatGPT-style Streamlit interface.
- **User Authentication** – Signup and login functionality.
- **Secure Password Storage** – Password hashing using PBKDF2.
- **Chat History** – Save and access previous conversations.
- **Multiple Conversations** – Create and manage separate chats.
- **SQLite Database** – Persist user accounts and conversations.
- **Profile Management** – Update username and password.
- **Dark and Light Themes** – Switch between display themes.
- **Chat Management** – Delete individual conversations or clear chat history.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Streamlit | Web application interface |
| Google Gemini API | AI-powered responses |
| SQLite | Database management |
| python-dotenv | Environment variable management |
| Google Gen AI SDK | Gemini API integration |

## Project Structure

```text
gemini-ai-chatbot/
│
├── app.py             # Streamlit web application
├── chatbot.py         # Terminal-based chatbot
├── requirements.txt   # Python dependencies
├── .gitignore         # Excluded files
├── .env               # API key configuration (not committed)
└── chat_history.db    # SQLite database (generated locally)
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/bhavyabapanapalli/chatbot.py.git
cd chatbot.py
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Gemini API Key

Create a `.env` file in the project directory:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

**Important:** Never share your API key or upload your `.env` file to GitHub.

### 5. Run the Application

```bash
python -m streamlit run app.py
```

Open the local URL displayed in your terminal, usually:

```text
http://localhost:8501
```

## Usage

1. Create an account using the signup option.
2. Log in to access the chatbot.
3. Start a new conversation.
4. Ask questions and receive AI-generated responses.
5. Access previous conversations from chat history.
6. Manage your profile and account settings.

## Security

- Passwords are stored using PBKDF2 hashing with individual salts.
- API credentials are managed through environment variables.
- User conversations are associated with individual accounts.
- Local database and secret configuration files are excluded from Git tracking.

## Future Enhancements

- Chat export functionality.
- File upload and document-based question answering.
- Voice input and text-to-speech.
- Improved conversation search.
- Deployment to a cloud hosting platform.

## Author

GitHub: [bhavyabapanapalli](https://github.com/bhavyabapanapalli)

---

*Built with Python, Streamlit, and Google Gemini API.*
