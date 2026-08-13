# AI Voice Agent

Welcome to your **AI Voice Agent** application! This project establishes a real-time voice conversation between a user (via a React web app), an admin dashboard, and an AI voice agent (running on LiveKit Python SDK), backed by FastAPI for secure token exchange and Supabase for persistence.

---

## 📁 Project File Structure

Here are the files created and configured:
```
ai-voice-agent/
├── README.md
├── .env.example
├── .env
├── .gitignore
│
├── backend/                            # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── routes/
│       ├── token.py
│       └── rooms.py
│
├── agent/                              # LiveKit Python Voice Agent
│   ├── main.py
│   ├── requirements.txt
│   └── config/
│       └── settings.py
│
└── frontend/                           # React customer-facing UI
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.jsx
        ├── index.js
        ├── components/
        │   ├── JoinRoom.jsx
        │   ├── CallScreen.jsx
        │   └── MicButton.jsx
        └── utils/
            └── livekit_client.js
```

---

## 🔑 Required API Keys & Where to Get Them (Free Tiers)

To run the voice assistant, replace the placeholders in your root `.env` file with real API keys:

1. **LiveKit Cloud Credentials**:
   * Go to [LiveKit Cloud](https://cloud.livekit.io/) and sign up for a free account.
   * Create a new project.
   * Go to **Settings > Keys** to generate a new key pair.
   * Copy the **Project URL** (`wss://...`), **API Key**, and **API Secret**.

2. **Groq API Key** (LLM brain):
   * Sign up at [Groq Console](https://console.groq.com/).
   * Navigate to **API Keys** and generate a new key.
   * Groq provides a free tier with high rate limits for models like `llama3-8b`.

3. **Deepgram API Key** (Speech-to-Text):
   * Sign up at [Deepgram Console](https://console.deepgram.com/).
   * Create a new project (includes $200 free credit on signup, which lasts a long time).
   * Generate an **API Key** with at least `Member` role permissions.

4. **Cartesia API Key** (Text-to-Speech voice synthesis):
   * Sign up at [Cartesia Play](https://play.cartesia.ai/).
   * Click on your profile and generate a new **API Key** (includes free initial credits).

---

## ⚙️ Step-by-Step Installation & Run Instructions

For beginners, keep the backend and the agent in separate Python virtual environments to prevent package dependency conflicts. You will need **3 terminal windows** open.

### Terminal 1: FastAPI Backend
1. Navigate to the project folder.
2. Create and activate a Python virtual environment:
   ```bash
   # On macOS/Linux:
   python3 -m venv backend/venv
   source backend/venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   python backend/main.py
   ```
   *The backend will start on **`http://localhost:8000`**.*

---

### Terminal 2: LiveKit Voice Agent
1. Navigate to the project folder.
2. Create and activate a separate virtual environment:
   ```bash
   # On macOS/Linux:
   python3 -m venv agent/venv
   source agent/venv/bin/activate
   ```
3. Install agent dependencies:
   ```bash
   pip install -r agent/requirements.txt
   ```
4. Start the voice agent in development mode:
   ```bash
   cd agent
   python main.py dev
   ```
   *The agent worker will connect to your LiveKit Cloud project and wait for dispatch jobs.*

---

### Terminal 3: React Frontend
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the React app:
   ```bash
   npm start
   ```
   *The browser will open automatically to **`http://localhost:3000`**.*

---

## 🎙️ Testing your Voice Agent

1. Open `http://localhost:3000` in your web browser.
2. Enter your name (e.g., "Alice") and a support channel room name (e.g., "customer-support").
3. Click **Connect to Agent**.
4. Allow browser microphone permissions when prompted.
5. Once connected:
   * The visualizer orb will breathe slowly in **blue/violet** (listening state).
   * You will hear the agent speak a greeting: *"Hello, thank you for calling. How can I help you today?"*
   * While the agent speaks, the orb will glow **purple/pink** and pulse outward.
   * Speak into your microphone, and hear the voice agent reply in real-time!
