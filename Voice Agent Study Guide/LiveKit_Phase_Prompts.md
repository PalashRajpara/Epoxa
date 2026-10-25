# LiveKit Voice AI — Phase Prompts (for coding agents)

Use ONE prompt per chat/session. Each prompt is self-contained — paste it into a new agent session for that phase.

---

## 🔑 Universal Rule (already included in every prompt below)

> Write beginner-friendly, readable code. No advanced/clever tricks, no unnecessary abstractions, no over-engineering. Add clear comments explaining what each part does and why. Prefer simple, explicit code over "smart" shortcuts. I am new to this and learning as I build.

---

## Phase 1 Prompt — Foundation & Basic Voice Agent

```
I'm building a voice AI customer support project using LiveKit. I'm a beginner, so please write beginner-friendly, readable code only — no advanced or clever tricks, no unnecessary abstractions. Add clear comments in the code explaining what each part does and why.

Build Phase 1 of my project: Foundation & Basic Voice Agent.

Goal: Build a working voice conversation between a customer and an AI agent.

Requirements:
- FastAPI backend (for LiveKit token generation and basic room management)
- React frontend (simple UI: join room, mic on/off, connection status)
- LiveKit room setup
- Customer joins the room from the frontend
- AI agent built using the LiveKit Agents SDK (Python) — use the official livekit-agents framework, not manual STT/LLM/TTS wiring
- AI components: Groq for LLM, Deepgram for STT, Cartesia for TTS (all as LiveKit Agents SDK plugins)
- Customer speaks → AI understands and replies with voice
- Token-based authentication for joining rooms

Everything must use free tiers only (LiveKit free tier, Groq free tier, Deepgram/Cartesia free credits).

Please:
1. Explain the folder/file structure before writing code
2. Write the backend first, then frontend, then the agent
3. Add comments in every file explaining what it does
4. Tell me exactly what environment variables / API keys I need to set up and where to get them for free
5. Give me simple step-by-step instructions to run it locally

Deliverable: I should be able to open the React app, join a room, speak into my mic, and hear the AI reply.
```

---

## Phase 2 Prompt — Intelligent Customer Support

```
I'm continuing my LiveKit voice AI customer support project. I'm a beginner, so please write beginner-friendly, readable code only — no advanced or clever tricks, no unnecessary abstractions. Add clear comments in the code explaining what each part does and why.

Context: Phase 1 is done — I have a working FastAPI backend, React frontend, LiveKit room, and a basic voice AI agent built with the LiveKit Agents SDK (Groq LLM, Deepgram STT, Cartesia TTS).

Build Phase 2: Intelligent Customer Support.

Goal: Turn the basic agent into a useful customer support assistant.

Requirements:
- FAQ system using ChromaDB for semantic search (RAG) — store a small set of sample FAQ docs and let the AI answer questions from them
- Appointment booking (simple mock booking flow — no real calendar integration needed)
- Customer verification (mock check, e.g. against a fake customer list)
- Complaint registration
- Ticket creation (store tickets in the database)
- Mock customer database (simple table with fake customer data)
- Conversation memory (AI remembers what was said earlier in the same call)
- Use LangGraph to structure the conversation flow with nodes like: Greeting, Verify Customer, FAQ, Appointment, Complaint, Escalation Decision
- Enable barge-in (interruptions) and voice activity detection using LiveKit's built-in features

Everything must use free tiers only.

Please:
1. Explain how the LangGraph flow will work before coding it (a simple diagram in text is fine)
2. Show me where ChromaDB fits into the flow and how documents get embedded/queried
3. Add comments in every function explaining the logic
4. Tell me how to test each feature manually (FAQ, booking, complaint, ticket)

Deliverable: The AI can verify a customer, answer FAQs from the knowledge base, book a mock appointment, register a complaint, and create a ticket — all through voice conversation, with interruption support.
```

---

## Phase 3 Prompt — Production Features

```
I'm continuing my LiveKit voice AI customer support project. I'm a beginner, so please write beginner-friendly, readable code only — no advanced or clever tricks, no unnecessary abstractions. Add clear comments in the code explaining what each part does and why.

Context: Phase 1 and 2 are done. I have a voice AI agent (LiveKit Agents SDK + Groq + Deepgram + Cartesia) with LangGraph-based conversation flow, FAQ via ChromaDB, appointment booking, complaints, and tickets.

Build Phase 3: Production Features.

Goal: Make it behave like a real company system.

Requirements:
- Call transcript (save the full text of each conversation)
- Call summary (generate a short summary of each call using the LLM)
- Conversation logs stored in the database
- Customer history (link past calls to a customer)
- Error handling (graceful handling of failures — API errors, disconnects, etc.)
- Session timeout handling
- Reconnection handling if a customer's connection drops
- Latency logging — log how long each step takes (speech-to-text, LLM response, text-to-speech) so I can see where time is being spent
- Use LiveKit's Room Events, Participant Events, and Event Listeners to detect joins/leaves/disconnects
- Database: use Supabase PostgreSQL directly (do not use SQLite at all, skip that step entirely)

Please:
1. Show me the database schema (tables) you're creating and why
2. Explain how the transcript and summary get generated and saved
3. Add comments explaining the event listener logic
4. Show me a simple way to view the latency logs (e.g. print to console or a simple log file)

Deliverable: Every call is tracked, recoverable, has a transcript and summary, and I can see how fast each part of the pipeline responds.
```

---

## Phase 4 Prompt — Human Handoff & Multi-Agent

```
I'm continuing my LiveKit voice AI customer support project. I'm a beginner, so please write beginner-friendly, readable code only — no advanced or clever tricks, no unnecessary abstractions. Add clear comments in the code explaining what each part does and why.

Context: Phases 1-3 are done. I have a production-style voice AI agent with transcripts, summaries, call logs, customer history, and latency tracking, all stored in Supabase PostgreSQL.

Build Phase 4: Human Handoff & Multi-Agent.

Goal: Implement seamless escalation from AI to a human agent.

Requirements:
- A simple human support dashboard (basic React page where a human agent can see active calls and join one)
- Human agent can join the same LiveKit room as the AI and customer
- AI can "transfer" the conversation — meaning it stops responding and lets the human take over
- AI shares the call transcript with the human when handing off, so the human has context
- Human can continue the call normally (talk to customer directly)
- AI can rejoin later if needed (e.g. human marks the issue resolved and hands back to AI)
- Use LiveKit's multi-participant support, participant permissions, and room management features

Please:
1. Explain how you'll detect "this needs a human" vs "AI can handle it" (keep this decision logic simple)
2. Explain how the transcript gets shown to the human when they join
3. Add comments explaining the handoff logic step by step
4. Tell me how to test this manually (simulate customer + AI + human all in one call)

Deliverable: AI handles routine issues on its own, and when it decides a call needs a human, a human can join, see the transcript, and take over without the customer noticing a broken conversation.
```

---

## Phase 5 Prompt — Deployment & Production Readiness

```
I'm continuing my LiveKit voice AI customer support project. I'm a beginner, so please write beginner-friendly, readable code only — no advanced or clever tricks, no unnecessary abstractions. Add clear comments in config files and scripts explaining what each part does.

Context: Phases 1-4 are done. I have a full voice AI customer support system: LiveKit Agents SDK agent, LangGraph flow, FAQ via ChromaDB, appointment/complaint/ticket handling, transcripts/summaries/latency logs in Supabase PostgreSQL, and human handoff.

Build Phase 5: Deployment & Production Readiness.

Goal: Deploy everything so it's accessible online, for free.

Requirements:
- Deploy React frontend to Vercel (free)
- Deploy FastAPI backend to Railway or Render (free tier)
- Confirm PostgreSQL is running on Supabase (free)
- Set up LiveKit Cloud free tier (or explain self-hosting if I want to learn that instead)
- Set up GitHub repo for version control
- Add environment variable handling (so API keys aren't hardcoded)
- Add basic logging
- Add a health check endpoint (so I can confirm the backend is alive)
- Add basic monitoring (simple, free option is fine)
- Write a README explaining the project, setup steps, and how to run it
- Create a simple architecture diagram description (text-based is fine, I can turn it into an image later)
- Write basic API documentation for my FastAPI endpoints

Testing checklist to verify after deployment:
- Single customer call works
- Multiple customers can use it at the same time
- Disconnect and reconnect works
- Human handoff still works
- Long conversations don't break
- Invalid inputs are handled gracefully
- Check latency logs under real network conditions

Please walk me through deployment step by step, one platform at a time, and tell me exactly what settings/environment variables to configure on each platform.

Deliverable: A fully deployed, portfolio-ready application I can share with a live link.
```

---

## Phase 6 Prompt — SIP Telephony (Optional)

```
I'm continuing my LiveKit voice AI customer support project. I'm a beginner, so please write beginner-friendly, readable code only — no advanced or clever tricks, no unnecessary abstractions. Add clear comments explaining what each part does.

Context: Phases 1-5 are done and deployed. My voice AI agent currently works through a browser microphone via LiveKit rooms.

Build Phase 6: SIP Telephony (optional add-on).

Goal: Let real phone calls reach my AI agent, not just browser-based conversations.

Requirements:
- Set up LiveKit SIP integration
- Connect a free Twilio trial phone number
- Route inbound calls from that phone number into my existing LiveKit room, where my AI agent answers exactly like it does for browser customers

Please:
1. Explain what SIP is and how it connects to LiveKit, in simple terms
2. Walk me through Twilio's free trial setup step by step
3. Show me the exact LiveKit SIP configuration needed
4. Add comments explaining each config value
5. Tell me how to test it (i.e. actually calling the number)

Deliverable: I can call a real phone number and have a voice conversation with my AI agent, same as the browser experience.
```
