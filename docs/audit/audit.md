# Comprehensive Architectural, Security, and Codebase Audit

**Project:** Epoxa — Real-Time Voice AI Agent  
**Audit Date:** October 25, 2026  
**Auditor:** Principal Software Engineer, Database Architect, and Security Reviewer  
**Phase:** Phase 0 (Read-Only Baseline & Diagnostic Audit)  
**Status:** Audit Completed — Awaiting Gate 0 Explicit Approval  

---

## 1. Executive Summary

A comprehensive architectural, security, and operational audit of the Epoxa repository was conducted against the physical codebase, git object history, and `PROJECT_CONTEXT.md`. 

Epoxa implements a real-time conversational voice agent ("Epixa") serving "Epoxcel", powered by browser WebRTC via LiveKit Cloud, Silero VAD, Deepgram Nova-2 STT, Groq Llama 3.1 LLM, Deepgram Aura TTS, LangGraph conversational state machines, and ChromaDB vector search. The frontends include a customer voice lobby with a WebGL/CSS glowing orb visualizer and a supervisor control dashboard.

While the core voice pipeline demonstrates proof-of-concept viability, the system is burdened by critical security vulnerabilities, tight coupling, duplicated logic, unpersisted business data, broken virtual environment paths, and zero automated test coverage. 

This document establishes the empirical baseline of the repository, highlighting discrepancies between the documented intent and actual behavior.

---

## 2. Real vs. Documented Structure

In accordance with Operating Rule 1 (*"The actual code is the truth for current behavior. The document is the truth for intent"*), the following discrepancies were identified:

| Component / Feature | Documented Intent (`PROJECT_CONTEXT.md`) | Actual Current Behavior in Code | Architectural Impact |
| :--- | :--- | :--- | :--- |
| **Appointment Booking** | Appointments are scheduled with date, time, and confirmation code, then stored in an `appointments` table. | `agent/nodes.py` (lines 564–574) generates a pseudo-random code `APT-{random.randint(1000, 9999)}` in memory and sets `appt_details["booked"] = True`. **No database write occurs anywhere.** | **Critical functional gap:** Customer appointments vanish upon call termination. Customers believe they are booked, but the business has no record. |
| **Takeover & Handoff State** | Handoff state is authoritative in `call_sessions.handoff_state` and coordinated via the backend. | `agent/handoff.py` stores state in a module-level dictionary `_active_handoffs = {}`. It attempts a fire-and-forget Supabase update to set `status = "escalated"`. The dashboard uses WebRTC `publishData({ action: "resume" })` directly to the agent. | **Split-brain vulnerability:** If an agent process restarts or drops, handoff state is lost, leaving callers either muted or having the AI talk over the supervisor. |
| **Customer & Room Access** | Customers connect to pre-provisioned rooms without room name knowledge; room access is mediated securely. | `frontend/src/components/JoinRoom.jsx` (lines 20–26) generates `support-user-${Math.floor(10000 + Math.random() * 90000)}` in browser JS and invokes public `POST /api/token`. | **Public exposure:** Any client can mint tokens for arbitrary room names with arbitrary identities. |
| **Supervisor Takeover Token** | Supervisors authenticate via Supabase Auth; token generation requires authenticated supervisor credentials. | `dashboard/src/components/JoinCallButton.jsx` (lines 45–53) invokes public `POST /api/token` with `{ "role": "agent" }`. The backend mints a privileged 2-hour LiveKit token without authentication or authorization. | **Critical Security Flaw:** Anyone who discovers the backend URL can join any room as a supervisor and eavesdrop on or hijack customer calls. |
| **Database Persistence** | Unified Supabase PostgreSQL schema with 8 normalized tables. | Asymmetric split: SQLite (`voice_support.db`) contains `customers`, `tickets`, `call_sessions`, `call_transcripts`. Supabase has only 3 tables (`call_sessions`, `call_transcripts`, `latency_logs`) created via raw SQL script. | **Data Desynchronization:** SQLite contains customer profiles and tickets; Supabase contains latency metrics. Neither database has a complete picture. |
| **Call Session Reconciliation** | Stale calls are auto-healed after a 60-second grace period via background processing. | `backend/routes.py` executes mutation inside `GET /api/rooms/active-sessions`. Polling the endpoint mutates rows from `active` to `completed`. | **HTTP Anti-Pattern:** GET requests violate HTTP idempotency and safety specifications. Multiple concurrent pollers trigger race conditions on database writes. |
| **Supervisor End Session Route** | Dashboard ends sessions by notifying the backend. | `dashboard/src/components/JoinCallButton.jsx` calls `POST /api/rooms/end-session`. **This route does not exist in `backend/routes.py`**, resulting in silent 404 errors. | Broken client functionality masked by silent error handling. |
| **Repository Layout** | `PROJECT_CONTEXT.md` describes a unified project with core abstractions. | Code is split into four disjoint subdirectories (`agent/`, `backend/`, `frontend/`, `dashboard/`), each with independent `requirements.txt` or `package.json`, isolated venvs, and `sys.path` hacks. | Inhibits unified linting, type-checking, sharing of models, and deterministic builds. |

---

## 3. Dead, Redundant, & Duplicated Code Analysis

1. **Exact Logging & Latency Duplication (`backend/utils.py` vs. `agent/utils.py`):**
   - Both files implement identical 180-line modules configuring `setup_logging()`, `get_logger()`, `get_latency_logger()`, and `LatencyTracker`.
   - `agent/utils.py` even includes a lazy-import hack:
     ```python
     backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
     if backend_dir not in sys.path:
         sys.path.insert(0, backend_dir)
     from database import save_latency_log
     ```
2. **Duplicate Environment Keys:**
   - In `.env` / `agent/config.py`: `DEEPGRAM_API_KEY`, `DEEPGRAM_STT_API_KEY`, and `DEEPGRAM_TTS_API_KEY` all hold the exact same token value.
   - `backend/routes.py` checks both `DEEPGRAM_API_KEY` and `DEEPGRAM_STT_API_KEY`.
3. **Dead Database File:**
   - `backend/voice_support.db` (45 KB SQLite binary) contains legacy mock records. In the target state, SQLite is eliminated in favor of Supabase PostgreSQL.
4. **Duplicate Design Systems:**
   - `frontend/src/design-system.css` (8 KB) and `dashboard/src/design-system.css` (3.6 KB) contain duplicate color palettes, glassmorphism variables, typography, and button classes with slight divergence.
5. **Redundant Startup Logic:**
   - `start.sh` attempts to launch tmux panes pointing to `backend/venv/bin/python` and `agent/venv/bin/python`. Both virtual environments are invalid due to hardcoded absolute paths from an earlier directory rename (`livekit-voice-ai-support` -> `voice-ai-agent`).

---

## 4. Coupling, Dependency Inversion, & Anti-Pattern Analysis

```
Current Coupling (Anti-Pattern):
┌──────────────────────────────┐          ┌──────────────────────────────┐
│        agent/main.py         │          │     agent/nodes.py           │
└──────────────┬───────────────┘          └──────────────┬───────────────┘
               │ sys.path.insert                         │ HTTP (httpx.get/post)
               ▼                                         ▼
┌──────────────────────────────┐          ┌──────────────────────────────┐
│     backend/database.py      │◄─────────┤     backend/routes.py        │
└──────────────────────────────┘          └──────────────────────────────┘
```

1. **Cross-Boundary `sys.path` Injection:**
   `agent/main.py` lines 48–50 and `agent/handoff.py` lines 18–20 inject `../backend` into `sys.path`. This creates a runtime dependency where the agent directly accesses backend internal modules.
2. **Hybrid Incoherent Coupling:**
   While `agent/main.py` accesses `database.py` via python imports, `agent/nodes.py` makes external HTTP requests over `httpx` to `http://127.0.0.1:8000/api/customers/verify` and `POST /api/tickets`. The agent simultaneously acts as an in-process library consumer and an out-of-process REST client.
3. **Global Mutable State in `agent/handoff.py`:**
   Takeover state is held in `_active_handoffs = {}`. If the agent worker handles multiple calls or crashes, in-memory state is lost or leaked across sessions.
4. **Hardcoded Model Names and Config in Code:**
   `llama-3.1-8b-instant`, `aura-asteria-en`, `all-MiniLM-L6-v2`, and timeouts are hardcoded directly inside `agent/nodes.py`, `agent/main.py`, and `agent/chroma_client.py`.

---

## 5. Comprehensive Security Findings & Secret Forensics

### 5.1 Git History Forensic Secret Scan
A deep inspection of the Git object store was conducted on commit `c82760f48a267c397a669ec6a9e50a38f9baf494` (Initial Commit: AI Voice Agent) and reflogs:
- **Result:** **CLEAN.**
  - `.env` was **never committed** to git. It was properly excluded by `.gitignore` in the initial commit.
  - No secret tokens, API keys, or JWTs are present in any historical git blob.
  - The only matched regex was a placeholder string (`wss://your-project.livekit.cloud`) in `frontend/src/App.jsx`.
- **Working Tree Warning:**
  - The working directory contains a live `.env` file with active third-party credentials (LiveKit, Groq, Deepgram, Cartesia, Supabase).
  - `.gitignore` currently protects `.env`, but team members must never execute commands that stage untracked files (`git add .` or `git add -A`) without verifying `.gitignore` coverage.

### 5.2 Vulnerability & Risk Matrix

| ID | Vulnerability / Threat | CVSS Severity | Location | Technical Vector & Impact |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | **Unauthenticated Role Escalation to Supervisor** | **9.8 (CRITICAL)** | `backend/routes.py` (`POST /api/token`) | Public clients can pass `{"role": "agent"}`. The backend generates an unrestricted LiveKit token with a 2-hour TTL, allowing unauthorized users to join any room and take over calls. |
| **SEC-02** | **Public Customer Data & Ticket Enumeration** | **7.5 (HIGH)** | `backend/routes.py` (`/api/customers`, `/api/tickets`, `/api/customers/verify`) | Endpoints are completely unauthenticated. An attacker can scrape all customer names, phone numbers, email addresses, and support complaints. |
| **SEC-03** | **Unbounded Public Call Generation (Denial of Wallet / Abuse)** | **8.2 (HIGH)** | `POST /api/token` | There is no IP rate limiting, concurrency cap, or bot verification (Cloudflare Turnstile). An attacker can generate hundreds of concurrent LiveKit calls, rapidly exhausting paid Deepgram, Groq, and LiveKit credits. |
| **SEC-04** | **Unauthenticated WebRTC Client Signal Injection** | **6.5 (MEDIUM)** | `agent/main.py` (`data_received`) | Any participant in a LiveKit room can send a WebRTC data packet `{"action": "resume"}` or `{"action": "handoff"}` without signature verification, forcing the AI to mute or resume unpredictably. |
| **SEC-05** | **Sensitive Diagnostic Exposure in Health Check** | **5.3 (MEDIUM)** | `backend/routes.py` (`GET /health`) | Returns internal configuration state, database sizes, and connectivity details to unauthenticated public requests. |
| **SEC-06** | **Supabase Public Schema Exposure via Anon Key** | **7.4 (HIGH)** | Supabase PostgreSQL Configuration | Without Row Level Security (RLS) forced and public permissions revoked, Supabase PostgREST exposes all tables directly to the public internet via the anon key embedded in frontend bundles. |
| **SEC-07** | **Prompt Injection via Voice Utterance** | **6.1 (MEDIUM)** | `agent/nodes.py` | Spoken customer text is concatenated directly into LLM prompts without explicit delimiter fencing or system instruction defense. |

---

## 6. Dependency Inventory, Toolchains & Deprecation Risks

### 6.1 Python Dependencies & Deprecation Risks
- **`livekit-agents` (`0.12.21`):**
  - LiveKit Agents has released `1.x`, introducing breaking changes (`AgentSession` replaces `VoicePipelineAgent`, new worker job lifecycle).
  - *Risk:* 0.12.x is stable for our current implementation, but upstream community documentation focuses on 1.x.
  - *Decision:* Per D11, keep `0.12.21` pinned behind strict interfaces during Phases 1–7. Isolate the 1.x upgrade to Phase 8.
- **Groq Llama 3.1 Model (`llama-3.1-8b-instant`):**
  - Groq actively manages hardware and deprecates older model checkpoints.
  - *Mitigation:* Abstract the model identifier into typed settings (`config.llm_model`).
- **Deepgram Aura TTS (`aura-asteria-en`):**
  - Deepgram Aura v1 models are supported, but Deepgram regularly updates voice names and streaming endpoints.
  - *Mitigation:* Move TTS voice and model names to configuration.
- **Sentence-Transformers & ChromaDB:**
  - `chromadb` 1.5.9 and `sentence-transformers` 5.6.0 require local PyTorch (`torch-2.12.1`) which adds ~1.5 GB to the container image.
  - *Decision:* Per D5, migrate FAQ storage to **pgvector on Supabase** with an in-memory cache in the agent, eliminating the local ChromaDB and PyTorch dependencies from the agent runtime.

### 6.2 Toolchain Issues
- **Virtual Environment Corruption:**
  - `backend/venv` and `agent/venv` are unusable because their shebangs reference `/Users/palashrajpara/Developer/AI/livekit-voice-ai-support/backend/venv/bin/python3.14`.
  - The repository root has `/Users/palashrajpara/.local/bin/uv` (uv 0.11.22) available, which can build hermetic Python virtual environments.
- **Frontend Toolchain:**
  - Both `frontend/` and `dashboard/` use Create React App (`react-scripts` 5.0.1) with Node.js v22.22.2.
  - CRA is deprecated, slow, and does not support modern TypeScript ESM tooling or fast HMR.
  - `pnpm` is not installed globally; `corepack` (0.34.6) is available to activate pnpm.

---

## 7. Test Coverage & Quality Assurance Baseline

| Subsystem | Existing Tests | Code Coverage | CI/CD Automation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Core Domain Models** | None | 0.0% | None | **CRITICAL DEFICIT** |
| **FastAPI Backend (`backend/`)** | None | 0.0% | None | **CRITICAL DEFICIT** |
| **LiveKit Agent (`agent/`)** | None | 0.0% | None | **CRITICAL DEFICIT** |
| **Customer App (`frontend/`)** | None | 0.0% | None | **CRITICAL DEFICIT** |
| **Supervisor Dashboard (`dashboard/`)** | None | 0.0% | None | **CRITICAL DEFICIT** |
| **Database Migrations** | None | N/A | None | **CRITICAL DEFICIT** |

The codebase currently has zero regression tests. Any refactoring carries high risk without a comprehensive unit, integration, and security test harness.

---

## 8. Invariant Preservation (Nuances from Section 14)

Section 14 of `PROJECT_CONTEXT.md` details 5 hard-earned engineering invariants that must be preserved:

1. **`ctx.room.sid` Asynchronous Deadlock Prevention:**
   Awaiting `ctx.room.sid` blocks the event loop for 30–40 seconds. The agent must connect immediately and resolve `room.sid` in a detached background task.
2. **Multi-Participant Track Isolation:**
   When a human supervisor (`agent_*` or `human_*`) joins, the AI agent must call `publication.set_subscribed(False)` to avoid hearing or responding to human speech.
3. **DOM Garbage Collection Protection for WebRTC Audio:**
   In WebRTC browser clients, audio elements created by `track.attach()` must be explicitly appended to the DOM (`document.body.appendChild`) to prevent browser garbage collection after ~20 seconds of silence.
4. **Strict Word-Boundary Escalation Regex:**
   Escalation detection must use boundary-checked regex patterns rather than substring matches to avoid false positives (e.g., "superhuman", "I don't want a human").
5. **Stale Session Reconciliation Grace Period:**
   Active session reconciliation must grant a 60-second grace period so calls in the connection handshake phase are not prematurely marked `completed`.
6. **Voice Pipeline Tuning Parameters:**
   `interrupt_speech_duration = 0.7`, `interrupt_min_words = 2`, `min_endpointing_delay = 0.6`, and `preemptive_synthesis = False` must remain unchanged unless justified by measured latency improvements.

---

## 9. Comprehensive Risk Matrix

| Risk Event | Likelihood | Impact | Severity | Mitigation Plan |
| :--- | :--- | :--- | :--- | :--- |
| **Live Voice Pipeline Regression during Modularization** | High | High | High | Keep voice pipeline parameters invariant; implement automated mock-room unit tests before editing agent logic. |
| **Database Connection Failure via Supabase Pooler** | Medium | Critical | High | Use Supavisor transaction pooler on port 6543 with `statement_cache_size=0`; use direct/session connection on 5432 for Alembic migrations. |
| **Cross-Tenant Data Leakage** | Low | Critical | High | Multi-tenant schema with `organization_id` on every table; enforce PostgreSQL Row Level Security (RLS) and require `organization_id` in all service repository queries. |
| **Database Write Latency Affecting Speech Fluidity** | Medium | High | High | Queue transcript and latency writes to an asynchronous worker queue off the main WebRTC audio pipeline. |
| **Frontend Token Security Leakage** | Medium | High | High | Vite apps never receive the Supabase service-role key; frontends interact with backend API only via Supabase Auth JWTs. |

---

*This audit document serves as the verified baseline for Phase 0.*
