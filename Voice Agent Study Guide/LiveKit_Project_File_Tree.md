# LiveKit Voice AI Project — Full File Structure

This is the complete folder structure for the entire project (all phases combined).
You don't need everything on Day 1 — folders/files get filled in as you complete each phase.

```
livekit-voice-ai-support/
│
├── README.md                          # Project overview, setup steps (Phase 5)
├── .env                                # All API keys / secrets (never commit this)
├── .env.example                        # Template showing what keys are needed
├── .gitignore
│
├── backend/                            # FastAPI backend
│   ├── main.py                         # FastAPI app entry point
│   ├── requirements.txt                # Python dependencies
│   │
│   ├── routes/
│   │   ├── token.py                    # Generates LiveKit access tokens (Phase 1)
│   │   ├── rooms.py                    # Room creation/management (Phase 1)
│   │   ├── customers.py                # Customer verification endpoints (Phase 2)
│   │   ├── tickets.py                  # Ticket creation endpoints (Phase 2)
│   │   └── health.py                   # Health check endpoint (Phase 5)
│   │
│   ├── database/
│   │   ├── connection.py               # Supabase PostgreSQL connection setup (Phase 3)
│   │   ├── models.py                   # Database table definitions (Phase 2-3)
│   │   └── schema.sql                  # SQL schema for reference
│   │
│   └── utils/
│       ├── logger.py                   # Logging setup (Phase 3)
│       └── latency_tracker.py          # Latency logging helper (Phase 3)
│
├── agent/                              # LiveKit Agents SDK — the AI voice agent
│   ├── main.py                         # Agent entry point (connects to LiveKit room)
│   ├── requirements.txt
│   │
│   ├── config/
│   │   └── settings.py                 # API keys, model settings
│   │
│   ├── graph/                          # LangGraph conversation flow (Phase 2)
│   │   ├── graph_builder.py            # Builds the LangGraph flow
│   │   ├── state.py                    # Conversation state definition
│   │   └── nodes/
│   │       ├── greeting.py
│   │       ├── verify_customer.py
│   │       ├── faq.py                  # Uses ChromaDB for RAG
│   │       ├── appointment.py
│   │       ├── complaint.py
│   │       └── escalation.py           # Decides AI vs human (Phase 4)
│   │
│   ├── knowledge_base/                 # ChromaDB setup (Phase 2)
│   │   ├── faq_docs/                   # Your raw FAQ text files
│   │   ├── embed_documents.py          # Script to load docs into ChromaDB
│   │   └── chroma_client.py            # ChromaDB connection helper
│   │
│   ├── handoff/                        # Human handoff logic (Phase 4)
│   │   ├── handoff_manager.py          # Transfers control AI <-> human
│   │   └── transcript_sharer.py        # Sends transcript to human agent
│   │
│   └── memory/
│       └── conversation_memory.py      # Tracks conversation history (Phase 2)
│
├── frontend/                           # React app (customer-facing)
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.jsx                     # Main app component
│       ├── index.js
│       │
│       ├── components/
│       │   ├── JoinRoom.jsx            # Join call screen (Phase 1)
│       │   ├── CallScreen.jsx          # Active call UI (Phase 1)
│       │   ├── MicButton.jsx           # Mic on/off control
│       │   └── ConnectionStatus.jsx    # Shows connected/reconnecting (Phase 3)
│       │
│       └── utils/
│           └── livekit_client.js       # LiveKit room connection logic
│
├── dashboard/                          # Human support agent dashboard (Phase 4)
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── ActiveCallsList.jsx     # Shows calls needing a human
│           ├── TranscriptView.jsx      # Shows AI-to-human handoff transcript
│           └── JoinCallButton.jsx      # Lets human join a LiveKit room
│
├── sip/                                # SIP telephony setup (Phase 6, optional)
│   ├── sip_config.md                   # LiveKit SIP configuration notes
│   └── twilio_setup.md                 # Twilio trial number setup steps
│
├── docs/                               # Documentation (Phase 5)
│   ├── architecture_diagram.md         # Text-based system architecture
│   └── api_documentation.md            # FastAPI endpoint docs
│
└── deployment/                         # Deployment configs (Phase 5)
    ├── vercel.json                     # React deployment config
    ├── railway.json / render.yaml      # Backend deployment config
    └── supabase_setup.md               # Database setup notes
```

---

## Quick setup script

Copy this into a file called `setup_folders.sh`, then run `bash setup_folders.sh` in your project folder to auto-create the whole structure at once.

```bash
#!/bin/bash
# This script creates the full folder and empty file structure for the project.
# Run it once inside your empty project folder.

mkdir -p backend/routes backend/database backend/utils
mkdir -p agent/config agent/graph/nodes agent/knowledge_base/faq_docs agent/handoff agent/memory
mkdir -p frontend/public frontend/src/components frontend/src/utils
mkdir -p dashboard/src/components
mkdir -p sip docs deployment

# backend files
touch backend/main.py backend/requirements.txt
touch backend/routes/token.py backend/routes/rooms.py backend/routes/customers.py backend/routes/tickets.py backend/routes/health.py
touch backend/database/connection.py backend/database/models.py backend/database/schema.sql
touch backend/utils/logger.py backend/utils/latency_tracker.py

# agent files
touch agent/main.py agent/requirements.txt agent/config/settings.py
touch agent/graph/graph_builder.py agent/graph/state.py
touch agent/graph/nodes/greeting.py agent/graph/nodes/verify_customer.py agent/graph/nodes/faq.py
touch agent/graph/nodes/appointment.py agent/graph/nodes/complaint.py agent/graph/nodes/escalation.py
touch agent/knowledge_base/embed_documents.py agent/knowledge_base/chroma_client.py
touch agent/handoff/handoff_manager.py agent/handoff/transcript_sharer.py
touch agent/memory/conversation_memory.py

# frontend files
touch frontend/package.json frontend/public/index.html
touch frontend/src/App.jsx frontend/src/index.js
touch frontend/src/components/JoinRoom.jsx frontend/src/components/CallScreen.jsx
touch frontend/src/components/MicButton.jsx frontend/src/components/ConnectionStatus.jsx
touch frontend/src/utils/livekit_client.js

# dashboard files
touch dashboard/package.json dashboard/src/App.jsx
touch dashboard/src/components/ActiveCallsList.jsx dashboard/src/components/TranscriptView.jsx
touch dashboard/src/components/JoinCallButton.jsx

# sip, docs, deployment
touch sip/sip_config.md sip/twilio_setup.md
touch docs/architecture_diagram.md docs/api_documentation.md
touch deployment/vercel.json deployment/supabase_setup.md

# root files
touch README.md .env.example .gitignore

echo "Project folder structure created successfully!"
```

**Note:** This script only creates empty files and folders — it doesn't install anything or write code. You (or your coding agent) will fill in each file phase by phase.
