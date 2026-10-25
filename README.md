# Epoxa — Production-Grade AI Voice Customer Support Platform

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61dafb.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178c6.svg)](https://www.typescriptlang.org)
[![Alembic](https://img.shields.io/badge/Alembic-1.13+-red.svg)](https://alembic.sqlalchemy.org)
[![Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)]()

Epoxa is a production-grade, web-based AI voice customer support platform. It enables customers to engage in natural, low-latency spoken conversations directly from their web browser with no customer login or telephony infrastructure required. Epoxa grounds answers in verified company guidelines, automatically logs sessions, generates objective AI summaries, captures customer details, and facilitates live human supervisor takeover with clean handback to the AI.

---

## Key Features

- **Real-Time Voice Support**: WebRTC audio transport powered by LiveKit with Deepgram speech-to-text (Nova-2), text-to-speech (Aura), and ultra-fast LLM inference (Groq / OpenAI).
- **Grounded Knowledge Retrieval**: Answers strictly grounded in approved organization FAQ/policy chunks with safe "I don't know" escalation fallback.
- **Supervisor Dashboard**: Authenticated interface for monitoring live calls, taking over ongoing customer calls, handing back control to AI, inspecting transcripts, and managing support tickets.
- **Support Ticket Lifecycle**: Automated ticket creation during or after calls with priority tags, status transitions, and supervisor assignments.
- **30-Day Transcript Data Retention**: Automatic, testable cleanup job enforcing data privacy regulations by purging expired speech content while preserving audit records.
- **Multi-Tenant Aware Architecture**: Tenant-isolated data schema (`organizations` -> `businesses` -> `locations`) with composite foreign keys and server-side authorization enforcement.
- **Supervisor Authentication**: Integration with Supabase Auth with server-side JWKS signature, audience, and issuer validation.

---

## Architecture Overview

```
epoxa/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Versioned REST endpoints (health, voice, calls, tickets, customers)
│   │   ├── core/            # Typed Pydantic settings, logging, security, error handling
│   │   ├── db/              # SQLAlchemy 2.0 async engine and declarative base
│   │   ├── models/          # Normalized domain models with cross-platform GUID and UTC timestamps
│   │   ├── schemas/         # Pydantic request & response schemas
│   │   ├── repositories/    # Tenant-scoped data access repositories
│   │   ├── services/        # Domain use-cases (handoff state machine, voice, tickets)
│   │   ├── agents/          # LangGraph orchestrator, tool definitions, prompts
│   │   ├── integrations/    # LiveKit, Deepgram, Groq, Supabase Auth adapters
│   │   └── scripts/         # Seed script, retention cleanup, target verifier
│   ├── alembic/             # Version-controlled database migrations
│   └── tests/               # 11 unit and integration tests (zero cross-tenant leaks)
├── frontend/                # React 18 + TypeScript + Vite app
│   ├── src/
│   │   ├── api/             # Typed API client
│   │   ├── components/      # VoiceVisualizer, Navbar, Badges, Modals
│   │   ├── views/           # CustomerVoiceView & SupervisorDashboard
│   │   └── types/           # TypeScript contracts matching backend schemas
├── docs/                    # PRD, Architecture, ERD, Data Dictionary, Tenant Isolation, API
├── .env.example             # Safe template with redacted placeholders
├── Makefile                 # Automation shortcuts
└── README.md
```

---

## Quickstart

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Install Dependencies
```bash
make install
```

### 3. Run Automated Tests
```bash
make test
```
All 11 tests pass with 100% tenant isolation, state machine validation, and retention verification.

### 4. Build Frontend Production Bundle
```bash
make build-frontend
```

### 5. Inspect Migration Target & Migrate
```bash
make migration-target
make migrate
make seed
```

### 6. Start Development Servers
- Backend: `make run-backend` (Runs on `http://localhost:8000`)
- Frontend: `make run-frontend` (Runs on `http://localhost:5173`)

---

## Security & Compliance
- **Zero Frontend Secrets**: Only public keys are used in the browser. Service role keys and provider API secrets are never exposed.
- **Defense in Depth**: Strict tenant isolation enforced at repository, service, and database schema levels.
- **30-Day Retention**: Scheduled purge script ensures expired customer conversation text is permanently redacted.
