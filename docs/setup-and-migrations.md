# Epoxa Setup, Migration & Operations Runbook

## 1. Prerequisites
- **Python**: 3.11+ (Python 3.14 compatible)
- **Node.js**: v20+ / v22+
- **Database**: Dedicated Supabase PostgreSQL project
- **Realtime**: LiveKit Cloud / Server
- **Speech**: Deepgram (Nova-2 / Aura)
- **LLM**: Groq (Llama-3.3-70b-versatile) or OpenAI

---

## 2. Local Environment Setup

### 2.1. Environment Variables Configuration
Copy the template and configure your keys in `.env`:
```bash
cp .env.example .env
```
Ensure secrets are kept in `.env` and never committed (enforced by `.gitignore`).

### 2.2. Backend Dependency Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
uv --no-config pip install --python ./.venv/bin/python -r pyproject.toml
```

### 2.3. Frontend Dependency Installation
```bash
npm install --prefix frontend
```

---

## 3. Database Migrations Workflow

### Step 1: Safe Target Inspection (Migration Gate)
Before applying migrations to any database, run the target verification script to inspect non-secret database identity:
```bash
PYTHONPATH=backend ./.venv/bin/python backend/app/scripts/verify_db_target.py
```
This inspects the database name, current user, PostgreSQL version, and lists existing tables without printing passwords or credentials.

### Step 2: Apply Version-Controlled Alembic Migrations
```bash
PYTHONPATH=backend ./.venv/bin/alembic -c backend/alembic.ini upgrade head
```

### Step 3: Seed Synthetic Demo Data
Seed the default demo organization, business, demo supervisor (`supervisor@epoxa.demo`), synthetic customer profiles, FAQ policies, and sample tickets:
```bash
PYTHONPATH=backend ./.venv/bin/python backend/app/scripts/seed_demo.py
```

---

## 4. Running the Application Locally

### Starting the FastAPI Backend
```bash
PYTHONPATH=backend ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Starting the React Frontend
```bash
npm run dev --prefix frontend
```
The application will launch at: `http://localhost:5173`

---

## 5. Automated 30-Day Transcript Retention Cleanup
To execute the automated transcript retention purge job:
```bash
PYTHONPATH=backend ./.venv/bin/python backend/app/scripts/cleanup_retention.py
```
This permanently redacts conversational text for transcripts older than 30 days while preserving non-sensitive call metadata and objective summaries.
