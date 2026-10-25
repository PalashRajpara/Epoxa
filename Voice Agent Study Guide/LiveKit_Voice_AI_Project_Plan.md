# LiveKit Voice AI Customer Support — Project Plan (Updated)

**Stack:** LiveKit + LiveKit Agents SDK + FastAPI + React + LangGraph + Groq + Deepgram + Cartesia + Supabase Postgres + ChromaDB

---

## Phase 1 — Foundation & Basic Voice Agent

**Goal:** Build a working voice conversation between a customer and an AI agent.

**What you'll build:**
- FastAPI backend (for token generation + room management)
- React frontend
- LiveKit room
- Customer joins room
- **AI agent built using the LiveKit Agents SDK (Python)** — don't hand-wire STT→LLM→TTS yourself, use `livekit-agents` which already handles room join, audio pipeline, and turn detection
- Customer speaks
- AI replies with voice

**LiveKit Features:**
- LiveKit Server
- Rooms
- Participants
- WebRTC Audio
- Agent Session (via LiveKit Agents SDK)
- Token Authentication

**AI Components:**
- Groq LLM
- Deepgram STT
- Cartesia TTS
- All connected through LiveKit Agents SDK plugins (`livekit-plugins-groq`, `livekit-plugins-deepgram`, `livekit-plugins-cartesia`)

**Learn:**
- How LiveKit streams audio
- How an AI agent joins a room via Agents SDK
- How audio reaches the AI
- How AI sends audio back

**Note on free credits:** Deepgram and Cartesia free tiers are one-time signup credits, not monthly. Track usage — if they run out, you can fall back to open-source local STT/TTS (e.g. Whisper + Piper) to keep testing for free.

**Deliverable:** A customer can have a basic voice conversation with the AI, built the way real LiveKit voice agents are built in industry.

---

## Phase 2 — Intelligent Customer Support

**Goal:** Turn the basic agent into a useful customer support assistant.

**What you'll build:**
- FAQ system — powered by **ChromaDB** for semantic search/RAG over your FAQ docs (this was missing before, added explicitly here)
- Appointment booking
- Customer verification
- Complaint registration
- Ticket creation
- Mock customer database (in Postgres, see note below)
- Conversation memory

**LiveKit Features:**
- Barge-in (interruptions)
- Voice Activity Detection
- Streaming audio
- Data Channels (optional)

**LangGraph:**
Nodes like:
- Greeting
- Verify Customer
- FAQ (queries ChromaDB)
- Appointment
- Complaint
- Escalation Decision

**Learn:**
- Real conversation flow
- Tool calling
- Memory
- Interruptions
- Basic RAG with a vector DB

**Deliverable:** The AI can solve common customer support tasks, including answering FAQs from your own knowledge base.

---

## Phase 3 — Production Features

**Goal:** Make it behave like a real company system.

**What you'll build:**
- Call transcript
- Call summary
- Conversation logs
- Customer history
- Error handling
- Session timeout
- Reconnection handling
- **Latency logging** — log STT→LLM→TTS round-trip time per turn (new addition — latency is the #1 thing that makes or breaks a voice agent in production, worth tracking early)

**LiveKit Features:**
- Room Events
- Participant Events
- Session Management
- Reconnection
- Metadata
- Event Listeners

**Database:**
Use **Supabase PostgreSQL from the start** — skip SQLite entirely. There's no benefit to starting on SQLite since Supabase's free tier is free from day one, and this avoids a pointless migration step later.

**Learn:**
- Managing call lifecycle
- Handling disconnects
- Storing conversation data
- Building reliable systems
- Measuring and improving latency

**Deliverable:** Every call is tracked, recoverable, and you have visibility into how fast your agent responds.

---

## Phase 4 — Human Handoff & Multi-Agent

**Goal:** Implement the feature companies care about most: seamless escalation.

**What you'll build:**
- Human support dashboard
- Human joins the LiveKit room
- AI transfers conversation
- AI shares transcript
- Human continues the call
- AI can rejoin if needed

**LiveKit Features:**
- Multiple Participants
- Human Handoff
- Agent Dispatch
- Participant Permissions
- Room Management

**Learn:**
- Multi-user communication
- Agent-to-human transfer
- Managing participants
- Production support workflows

**Deliverable:** AI handles routine issues and transfers complex ones to a human without losing context.

---

## Phase 5 — Deployment & Production Readiness

**Goal:** Deploy everything and make it accessible online.

**Deploy:**
- React → Vercel (Free)
- FastAPI → Railway or Render (Free tier, if available)
- PostgreSQL → Supabase (Free)
- LiveKit → LiveKit Cloud Free tier (or self-host if you want to learn operations)
- GitHub for version control

**Add:**
- Environment variables
- Logging
- Health check endpoint
- Basic monitoring
- README
- Architecture diagram
- API documentation

**Test:**
- Single customer
- Multiple customers
- Disconnect and reconnect
- Human handoff
- Long conversations
- Invalid inputs
- Latency under load

**Learn:**
- Deployment
- Production configuration
- Security basics
- Environment management
- End-to-end testing

**Deliverable:** A deployed, portfolio-ready application.

---

## Phase 6 — SIP Telephony (Optional, Recommended)

**Goal:** Make your agent take real phone calls, not just browser-mic conversations — a major reason companies actually choose LiveKit.

**What you'll build:**
- LiveKit SIP integration
- Connect a free Twilio trial phone number
- Inbound call → routes into your LiveKit room → AI agent answers

**LiveKit Features:**
- SIP Trunking
- Inbound/Outbound call handling

**Learn:**
- How voice AI systems connect to the real phone network
- SIP basics

**Deliverable:** Someone can call a real phone number and talk to your AI agent.

---

## Final Tech Stack (Free)

| Component | Tool |
|---|---|
| Voice Platform | LiveKit (Free tier or self-hosted) |
| Agent Framework | LiveKit Agents SDK |
| Backend | FastAPI |
| Frontend | React |
| AI Workflow | LangGraph |
| LLM | Groq (Free) |
| STT | Deepgram (Free credits) |
| TTS | Cartesia (Free credits) |
| Database | Supabase PostgreSQL (Free) |
| Vector DB | ChromaDB |
| Telephony | LiveKit SIP + Twilio trial (Optional) |
| Deployment | Vercel + Railway/Render + Supabase |
| Version Control | GitHub |

---

## Final Project Features

By the end, your project will include:
- Real-time voice conversations
- LiveKit rooms and participants
- Token-based authentication
- Streaming speech-to-text
- Streaming text-to-speech
- Built on LiveKit Agents SDK (industry-standard pattern)
- AI customer support
- FAQ handling with RAG (ChromaDB)
- Appointment booking
- Complaint registration
- Ticket creation
- Conversation memory
- Tool calling
- Barge-in (interruptions)
- Session management
- Latency tracking
- Call transcripts
- Call summaries
- Customer history
- Human handoff
- Multi-participant support
- Reconnection handling
- Logging and monitoring
- Full cloud deployment
- Real phone call support via SIP (optional)
