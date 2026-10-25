# Phase A: Repository Audit & Engineering Baseline
**Project Name:** Epoxa — Voice AI Agent  
**Audit Date:** October 2026  
**Status:** Audit Completed  

---

## 1. Executive Summary

This repository contains a full-stack, real-time AI Voice Customer Support application connecting callers via browser WebRTC to a LiveKit Python Voice Agent powered by Groq LLM (`llama-3.1-8b-instant`), Deepgram STT/TTS, Silero VAD, LangGraph, ChromaDB, and FastAPI, with a React customer interface and an admin supervisor dashboard.

The application functions end-to-end for basic demonstration, but currently operates with severe technical debt, zero automated tests, architectural anti-patterns (such as cross-boundary `sys.path` injection), critical security flaws (unauthenticated role escalation in token minting), and persistence inconsistencies between local SQLite and cloud Supabase.

This document establishes the verified baseline for the refactoring and engineering transformation.

---

## 2. Repository Inventory

| Path | Primary Language / Framework | Purpose | Status / Integrity |
| :--- | :--- | :--- | :--- |
| `backend/main.py` | Python 3.12+ / FastAPI | Backend HTTP server, CORS, SQLite DB initialization | Compiles cleanly. Lacks lifespan handler; invokes DB init at module level. |
| `backend/routes.py` | Python 3.12+ / FastAPI | REST endpoints for tokens, rooms, customers, tickets | Compiles cleanly. Contains unauthenticated role escalation & unbounded queries. |
| `backend/database.py` | Python 3.12+ / sqlite3 + Supabase | Database access layer (SQLite local + Supabase cloud) | Compiles cleanly. Asymmetric sync: customers/tickets only saved locally. |
| `backend/schema.sql` | PostgreSQL DDL | Supabase cloud schema definition | Covers only call sessions, transcripts, latency logs. Missing customers and tickets. |
| `backend/utils.py` | Python 3.12+ | Logging and LatencyTracker utilities | 100% duplicate of `agent/utils.py`. |
| `agent/main.py` | Python 3.12+ / LiveKit Agents 0.12+ | LiveKit voice agent worker & event orchestration | Compiles cleanly. Direct import of `backend/database.py` via `sys.path.insert`. |
| `agent/graph_builder.py` | Python 3.12+ / LangGraph 1.2+ | StateGraph, intent router, custom LiveKit LLM wrapper | Compiles cleanly. In-memory checkpointer only (`MemorySaver`). |
| `agent/nodes.py` | Python 3.12+ / LangChain Core | Graph dialogue nodes, prompt templates, backend HTTP calls | Compiles cleanly. Hybrid communication: talks to backend via HTTP while main.py uses DB. |
| `agent/state.py` | Python 3.12+ / TypedDict | Schema for LangGraph conversation state | Compiles cleanly. Well-structured. |
| `agent/handoff.py` | Python 3.12+ | Escalation state management | Volatile in-memory dictionary; only updates Supabase, ignores SQLite. |
| `agent/chroma_client.py` | Python 3.12+ / ChromaDB | Local ChromaDB vector storage client | Compiles cleanly. Pre-warms SentenceTransformers. |
| `agent/embed_documents.py` | Python 3.12+ | FAQ document embedding ingestion script | Standalone script. Ingests `faq_docs/` into ChromaDB. |
| `agent/config.py` | Python 3.12+ | Environment configuration & validation | Compiles cleanly. Hard exits with `sys.exit(1)` on missing keys. |
| `agent/utils.py` | Python 3.12+ | Logging and LatencyTracker utilities | 100% duplicate of `backend/utils.py`. |
| `frontend/` | React 18 / LiveKit Client 2.5+ | Customer web app with glowing voice orb & call controls | Compiles & builds production bundle cleanly (181.96 kB). 0 tests. |
| `dashboard/` | React 18 / LiveKit Client 2.5+ | Supervisor dashboard for active call monitoring & takeover | Compiles & builds production bundle cleanly (184.43 kB). 0 tests. |
| `start.sh` | Bash | Multi-service startup script with tmux support | Operational. Spawns 4 processes. |
| `PROJECT_CONTEXT.md` | Markdown | Comprehensive architecture & specification context | Comprehensive and up-to-date. |

---

## 3. Current Architecture & Data Flow Diagram

```
                               ┌────────────────────────────────┐
                               │       LiveKit Cloud RTC        │
                               │   (WebRTC Audio, Tracks, Data) │
                               └───────┬──────────────┬─────────┘
                                       │              │
                ┌──────────────────────┘              └─────────────────────┐
                ▼                                                           ▼
    ┌────────────────────────┐                                  ┌────────────────────────┐
    │   Customer Web App     │                                  │  Supervisor Dashboard  │
    │   (React.js @ :3000)   │                                  │   (React.js @ :3001)   │
    │ ────────────────────── │                                  │ ────────────────────── │
    │ • Audio Track & Orb UI │                                  │ • Polls Active Calls   │
    │ • Mic toggle & Timer   │                                  │ • Polls Transcripts    │
    │ • POST /api/token      │                                  │ • Live Takeover / Mic  │
    └───────────┬────────────┘                                  └───────────┬────────────┘
                │                                                           │
                │ Token & Customer Requests                                 │ Token, Transcripts & Takeover
                ▼                                                           ▼
    ┌────────────────────────────────────────────────────────────────────────────────────┐
    │                             FastAPI Backend (@ :8000)                              │
    │ ────────────────────────────────────────────────────────────────────────────────── │
    │ • Routes in single `routes.py` (Unauthenticated, unbounded queries)                │
    │ • Mutating state during GET requests (auto-healing stale rooms)                    │
    │ • Dual DB logic in single `database.py` (SQLite primary + Supabase background)     │
    └────────────────────────────────────────┬───────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │ (sys.path hack)
                       ▼ (HTTP over network)                       ▼
    ┌────────────────────────────────────────────────────────────────────────────────────┐
    │                         LiveKit Voice Agent Worker (Python)                        │
    │ ────────────────────────────────────────────────────────────────────────────────── │
    │ • Silero VAD -> Deepgram STT -> LangGraph (Groq Llama 3.1) -> Deepgram TTS         │
    │ • Directly imports `backend/database.py` for call session creation & transcripts   │
    │ • Separately calls FastAPI over HTTP for customer verification & tickets          │
    │ • Maintains volatile in-memory dictionary `_active_handoffs` for supervisor takeover│
    └────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Baseline Test and Build Results

| Component | Target Command | Result | Details |
| :--- | :--- | :--- | :--- |
| **Python Backend** | `py_compile backend/*.py` | **PASS** | Syntax validation succeeded for all files. |
| **Python Agent** | `py_compile agent/*.py` | **PASS** | Syntax validation succeeded for all files. |
| **Backend Unit Tests** | `pytest tests/` | **FAIL (Missing)** | 0 test files exist in repository. Pytest not installed in venv. |
| **Agent Unit Tests** | `pytest agent/tests/` | **FAIL (Missing)** | 0 test files exist in repository. Pytest not installed in venv. |
| **Frontend Tests** | `cd frontend && npm test` | **FAIL (Missing)** | Exited code 1: 0 test files matched. |
| **Dashboard Tests** | `cd dashboard && npm test` | **FAIL (Missing)** | Exited code 1: 0 test files matched. |
| **Frontend Production Build** | `cd frontend && npm run build` | **PASS** | Compiled successfully: 181.96 kB gzip JS, 1.96 kB CSS. |
| **Dashboard Production Build** | `cd dashboard && npm run build` | **PASS** | Compiled successfully: 184.43 kB gzip JS, 986 B CSS. |

---

## 5. Prioritized Technical-Debt Register

### Priority 0 (Critical — Immediate Threat to Reliability / Security)
1. **Critical Privilege Escalation in `POST /api/token`**:
   - `backend/routes.py` accepts `{ "role": "agent" }` without any authentication or authorization token. Any user can generate a privileged supervisor token with a 2-hour TTL and join any call with supervisor privileges.
2. **Missing `.gitignore` File in Repository Root**:
   - The repository root lacks `.gitignore`. Uncommitted secrets (`.env`), local databases (`voice_support.db`), compiled python caches (`__pycache__`), and application logs (`logs/app.log`) risk accidental commits to version control.
3. **Zero Test Coverage**:
   - There are zero automated tests across backend, agent, frontend, and dashboard. No test runner, no fixtures, and no regression guards exist.

### Priority 1 (High — Structural & Data Integrity Flaws)
4. **Architectural Coupling & Inverted Dependencies**:
   - `agent/main.py` manipulates `sys.path` to import `backend/database.py`. The agent worker directly manipulates backend storage tables.
   - Meanwhile, `agent/nodes.py` calls the backend over HTTP (`httpx.get`/`post`) for customer verification and tickets. This creates an uncoordinated hybrid dependency where the agent worker relies on both direct database file access and HTTP network reachability.
5. **Code Duplication**:
   - `backend/utils.py` and `agent/utils.py` are identical ~180-line files copied across directories.
6. **Asymmetric & Fragile Dual Persistence**:
   - `customers` and `tickets` only exist in SQLite; Supabase has no corresponding tables or sync.
   - `latency_logs` only exist in Supabase; SQLite has no latency table.
   - For `call_sessions` and `call_transcripts`, Supabase writes are fire-and-forget in background threads. If Supabase fails or has network latency, writes are dropped with no retry queue, no error log table, and no recovery mechanism.
   - `agent/handoff.py` updates call status to `"escalated"` in Supabase only, completely skipping SQLite.
7. **Unbounded Queries & Unindexed Tables**:
   - `GET /api/rooms/active-sessions` performs an unbounded `SELECT * FROM call_sessions ORDER BY started_at DESC` and is polled every 3 seconds by the dashboard. As historical calls accumulate, performance will degrade severely.
   - SQLite tables have no indexes on foreign keys or lookup columns (`tickets.customer_id`, `call_transcripts.session_id`, `call_sessions.room_name`).

### Priority 2 (Medium — Code Quality & Maintainability Debt)
8. **HTTP GET Side-Effects (Anti-Pattern)**:
   - `GET /api/rooms/active-sessions` iterates through sessions and mutates their status to `"completed"` in the database. HTTP GET must be idempotent and safe.
9. **Volatile In-Memory Handoff State**:
   - `agent/handoff.py` stores active handoffs in `_active_handoffs = {}`. Process restarts wipe out all takeover states.
10. **Scattered & Untyped Configuration**:
    - Backend accesses `os.getenv()` haphazardly across `routes.py`, `database.py`, and `main.py` without Pydantic validation or central typed settings.
    - `agent/config.py` uses raw `print` statements and `sys.exit(1)`.
11. **Simulated Appointment Scheduling**:
    - `agent/nodes.py` conversationally collects appointment date/time and creates an `APT-XXXX` code, but no database table or persistence layer stores appointments.

---

## 6. Security Audit Findings

| Vulnerability / Risk | Severity | Affected Component | Impact | Remediation Plan |
| :--- | :--- | :--- | :--- | :--- |
| **Unauthenticated Token Role Escalation** | **CRITICAL** | `backend/routes.py` (`POST /api/token`) | Public callers can request `role: "agent"` and gain supervisor takeover capabilities. | Require supervisor API key / secret bearer token to mint `agent` tokens. |
| **Lack of `.gitignore`** | **CRITICAL** | Root repository | Real credentials in `.env`, SQLite DB files, and logs can be committed. | Create comprehensive `.gitignore` immediately. |
| **Public Unauthenticated APIs** | **HIGH** | `backend/routes.py` (`/api/customers`, `/api/tickets`, `/api/rooms`) | Anyone can enumerate all customer personal data, phone numbers, emails, and tickets. | Protect administrative endpoints with bearer authentication or internal API keys. |
| **Unrestricted Input Payloads** | **MEDIUM** | `backend/routes.py` (`POST /api/tickets`) | No character length constraints on ticket description or category. Vulnerable to resource exhaustion. | Enforce Pydantic validation: `Field(max_length=...)`, sanitize strings. |
| **Sensitive Diagnostic Data in Health Check** | **LOW** | `backend/routes.py` (`GET /health`) | Exposes customer database count and detailed configuration state. | Separate health into `/health/live` and `/health/ready` with sanitized public outputs. |

---

## 7. Known Behavioral Limitations

1. **Appointment Booking Storage**: The appointment flow confirms appointments conversationally, but no `appointments` table exists in SQLite or PostgreSQL.
2. **Conversation State Persistence**: LangGraph uses `MemorySaver`. While state persists across turns within a single worker process session, worker restart or horizontal scaling terminates active graph states.
3. **Database Dual-Persistence Split**: Customer profiles created via `POST /api/customers` are saved only to SQLite. If the dashboard or cloud analytics queries Supabase, new customer records are absent.

---

## 8. Target Architecture & Next Steps (Phase B)

Phase B will establish:
1. **Clean Architecture Boundaries**:
   - Unified core package structure (`epoxa_core` / `epoxa_api` / `epoxa_agent`).
   - Domain layer (models, business exceptions, validation).
   - Infrastructure layer (shared repositories, typed configuration, structured logging).
2. **Security Hardening**:
   - Supervisor authentication middleware.
   - Pydantic schema validation with strict bounds.
   - Root `.gitignore`.
3. **Testing Suite**:
   - Automated Pytest suite with mock fixtures for LiveKit, Groq, Deepgram, and ChromaDB.
   - Integration tests for all FastAPI endpoints.
   - Frontend mock unit tests.
