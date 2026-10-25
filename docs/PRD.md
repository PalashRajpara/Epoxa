# Epoxa Product Requirements Document (PRD)

## 1. Executive Summary
**Epoxa** is a production-grade, web-based AI voice customer support platform designed for modern businesses. Customers initiate real-time conversational voice calls directly from their browser without requiring accounts, login, or PSTN phone numbers. The AI support agent handles customer inquiries, grounds answers in approved organizational knowledge/policies, captures customer details when relevant, creates support tickets, and facilitates seamless live escalation to human supervisors. Supervisors utilize a dedicated, authenticated dashboard to monitor active calls, review transcript histories and generated summaries, manage tickets, and execute real-time call takeovers with clean handback to the AI.

## 2. Core Personas
1. **End-User / Customer**:
   - Accesses Epoxa via browser with microphone access.
   - Interacts naturally using voice with low latency.
   - Gets accurate policy and FAQ answers or requests human assistance.
   - Provides minimal identity details (e.g. name, phone, email) if a ticket or follow-up is needed.
2. **Supervisor / Support Agent**:
   - Authenticated via Supabase Auth.
   - Monitors live call sessions, status, and queue in real-time.
   - Inspects real-time streaming transcripts and previous call summaries.
   - Takes over calls in real-time when the customer is unsatisfied or requires human authority.
   - Hands the call back to the AI or ends the call with structured outcome notes.
3. **Organization Administrator**:
   - Manages organizational knowledge base and agent configurations.
   - Reviews ticket queues, escalations, and SLA performance.

## 3. Product Scope (V1)

### Must Have (In-Scope)
- **Real-Time Voice Support**: WebRTC audio streaming via LiveKit, Deepgram STT/TTS (or fallback adapters), fast LLM inference (Groq/OpenAI), and LangGraph state orchestration.
- **Knowledge-Grounded Answers**: FAQ/policy retrieval with explicit safe "I don't know" behavior and escalation triggers whenever knowledge is insufficient.
- **Customer Detail Records**: Tenant-scoped customer records linked to calls and tickets without customer login or passwords.
- **Call Session Lifecycle & Auditing**: Detailed tracking of call sessions, lifecycle states (`initiating`, `active`, `escalated`, `supervisor_takeover`, `completed`, `failed`), events, transcripts, and structured call summaries.
- **Support Ticket System**: Full ticket lifecycle (status, priority, category, supervisor assignment, linked call reference, resolution notes).
- **Supervisor Dashboard**:
  - Live active call view with real-time indicators (speaking, listening, supervisor takeover).
  - Call history with searchable transcript viewer and AI summaries.
  - Interactive call takeover and handback state transitions.
  - Ticket management interface.
  - Fallback ticket creation when no supervisor is available.
- **Transcript Data Retention**: 30-day retention policy strictly enforced via an automated, testable retention cleanup job.
- **Enterprise-Grade Tenant Isolation**: Tenant-aware data schema (`organizations` -> `businesses` -> `business_locations`) with strict server-side scoping and defense-in-depth security.
- **Supervisor Authentication**: Supabase Auth integration with strict server-side JWT signature, audience, issuer, and claim validation.
- **Seed Data**: Deterministic, idempotent synthetic demo data for quick setup and testing.

### Explicitly Out of Scope (V1)
- PSTN telephony and Twilio SIP trunks.
- Appointment booking, calendar sync, or appointment scheduling tables.
- Customer authentication, customer login accounts, or customer portal.
- Public self-serve multi-tenant onboarding/billing UI.
- Direct public document uploading without admin privileges.
- Premature microservices, Kubernetes, or Kafka.

## 4. Key Workflows

### 4.1. Voice Interaction & Knowledge Retrieval Flow
1. Customer clicks "Start Voice Call" on web client.
2. Web client requests a short-lived, room-scoped token from FastAPI `/api/v1/voice/token`.
3. Client establishes WebRTC audio connection with LiveKit room.
4. Audio streams to Deepgram STT adapter; transcribed speech triggers the LangGraph agent orchestrator.
5. Orchestrator classifies customer intent:
   - **FAQ/Knowledge**: Searches organization knowledge chunks; formats grounded response. If confidence is low or information is absent, responds: "I don't have that information in my official guidelines. Would you like me to connect you with a supervisor or create a support ticket?"
   - **Customer Details**: Captures name/contact info and updates tenant-scoped customer record.
   - **Ticket Creation**: Opens a support ticket with priority and problem description.
   - **Human Escalation**: Flags the session for supervisor escalation.
6. Synthesized audio (Deepgram TTS) streams back to customer room in real-time.

### 4.2. Supervisor Live Takeover & Handback Flow
1. Active call is flagged as `escalated` by customer request or AI detection.
2. Dashboard alerts online supervisors with call context and live transcript.
3. Supervisor clicks "Take Over Call".
4. FastAPI validates supervisor authorization and transitions session state to `supervisor_takeover`.
5. AI agent audio output is immediately muted/suppressed. Supervisor joins the room audio track.
6. When supervisor finishes resolution, supervisor can either:
   - Click "Hand back to AI": Audio un-mutes AI, agent receives handback context summary, and session state returns to `active`.
   - Click "End Call": Session ends, summary and ticket updates are committed.

### 4.3. 30-Day Transcript Retention Job
1. Automated background script queries `transcripts` older than 30 days (`created_at < NOW() - INTERVAL '30 days'`).
2. Content is permanently purged/redacted while retaining non-sensitive audit metadata (session ID, duration, timestamps, outcome).
3. Execution outcome and purged count are logged without exposing customer or transcript text.
