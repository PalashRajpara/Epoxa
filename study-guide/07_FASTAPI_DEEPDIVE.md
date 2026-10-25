# 07 — FastAPI Deep Dive: The Backend REST API

> The FastAPI backend is the "glue layer" between the frontend (browser), the agent (Python worker),
> and the databases (SQLite + Supabase). It also generates secure tokens for LiveKit room access.

---

## What Is FastAPI?

FastAPI is a Python web framework for building REST APIs quickly. It's notable for:
- **Automatic validation**: You declare the shape of request/response data using Python type hints,
  and FastAPI validates everything automatically
- **Interactive docs**: Go to `http://localhost:8000/docs` and you get a built-in Swagger UI
  where you can test every endpoint in the browser
- **Async-first**: Routes can be `async def`, so they integrate naturally with the event loop
- **Pydantic integration**: Uses Pydantic models to validate and serialize data

**Why FastAPI in this project?**
- The AI agent (Python worker) needs to call a REST API to look up customers and create tickets.
  Using FastAPI makes these operations clean, validated, and easy to debug.
- The frontend (JavaScript) needs an API to get LiveKit tokens.
- The human agent dashboard needs APIs to fetch sessions and transcripts.

---

## Core Concept: Routes / Endpoints

A **route** is a URL pattern + HTTP method + handler function. When a request comes in
that matches the pattern, FastAPI calls the handler function.

```python
from fastapi import FastAPI
app = FastAPI()

# Route decorator: GET /hello
# FastAPI registers: "when someone sends GET /hello, call this function"
@app.get("/hello")
def say_hello():
    return {"message": "Hello, world!"}  # FastAPI converts this dict to JSON automatically
```

### In THIS project — `backend/main.py`

```python
# backend/main.py — creating the FastAPI app and adding routes

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load .env FIRST — before any other imports that read environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"), override=True)

from utils import setup_logging, get_logger
setup_logging(level="INFO")
logger = get_logger("backend.main")

from routes import router as api_router
import database

# Initialize the SQLite database: creates tables if they don't exist,
# and seeds 3 mock customers if the database is empty.
database.init_db()

# Create the FastAPI application object
app = FastAPI(
    title="LiveKit Voice AI Support Backend",
    description="Backend API for generating LiveKit access tokens and managing customer rooms.",
    version="3.0.0"
)

# CORS middleware allows the React frontend (usually running on http://localhost:3000)
# to make requests to this API (running on http://localhost:8000).
# Without CORS, the browser would block the request for security reasons.
# In production, replace "*" (allow all origins) with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow requests from any origin
    allow_credentials=True,    # Allow cookies / auth headers
    allow_methods=["*"],       # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],       # Allow all request headers
)

# Register all the route handlers defined in routes.py
app.include_router(api_router)

# Root endpoint: a simple health check that the server is running
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "LiveKit Voice AI Support Backend is running!",
        "version": "3.0.0",
    }

# If you run this file directly with `python main.py`, start the uvicorn server.
# In development, `reload=True` restarts the server whenever you change a file.
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
```

---

## Core Concept: Pydantic Models — Request/Response Validation

**Pydantic** is a Python library for data validation using type hints. FastAPI uses it to:
- Automatically parse JSON request bodies
- Validate that required fields are present and have the right types
- Convert Python dicts to JSON responses

```python
from pydantic import BaseModel
from typing import Optional

# Define what a valid request must look like
class TokenRequest(BaseModel):
    room_name: str        # Required: must be a string
    participant_name: str # Required: must be a string
    role: Optional[str] = "customer"  # Optional: defaults to "customer" if not sent
```

If the frontend sends a request without `room_name`, FastAPI returns a 422 error automatically.
You don't write the validation logic — Pydantic handles it.

---

## Every Endpoint in `backend/routes.py`

### `/api/token` — The LiveKit JWT Generator

```python
# backend/routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from livekit import api
import os, uuid

router = APIRouter()

class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    role: Optional[str] = "customer"

@router.post("/api/token")
async def generate_token(request: TokenRequest):
    """
    Generates a signed JWT token for a participant to join a LiveKit room.

    This is the FIRST thing the frontend calls when a customer starts a call:
    1. Frontend sends POST /api/token with room_name and participant_name
    2. Backend generates a JWT signed with LIVEKIT_API_KEY + LIVEKIT_API_SECRET
    3. Frontend uses this JWT to connect to LiveKit Cloud
    4. LiveKit verifies the JWT and lets the participant in
    """
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not api_key or not api_secret:
        # HTTPException tells FastAPI to return an HTTP error response
        # status_code=500 = Internal Server Error (our config is broken)
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured.")

    # Create a unique identity for this participant
    # "customer_" prefix helps the agent identify who is who
    prefix = "agent" if request.role == "agent" else "customer"
    unique_identity = f"{prefix}_{uuid.uuid4().hex[:8]}"  # e.g., "customer_a3f8b2d1"

    try:
        # api.AccessToken is LiveKit's token builder
        token = (
            api.AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(unique_identity)       # Unique identifier for this participant
            .with_name(request.participant_name)  # Display name (e.g., "John Doe")
            .with_grants(
                api.VideoGrants(
                    room_join=True,             # Permission: allowed to join rooms
                    room=request.room_name      # Permission: specifically this room only
                )
            )
        )

        # Return the JWT and connection info
        # The frontend needs both token AND server_url to connect to LiveKit
        return {
            "token": token.to_jwt(),             # The signed JWT string
            "identity": unique_identity,
            "room": request.room_name,
            "participant_name": request.participant_name,
            "server_url": os.getenv("LIVEKIT_URL")  # The wss:// LiveKit server address
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")
```

### `/api/customers/verify` — Customer Lookup (Used by the AI Agent)

```python
# backend/routes.py

@router.get("/api/customers/verify")
def verify_customer(phone: str = Query(..., description="Phone number to verify")):
    """
    Checks the SQLite database for a customer with the given phone number.

    Called by: agent/nodes.py → verify_customer_node()
    The agent calls this during identity verification:
    1. Customer says their phone number
    2. Agent extracts digits using extract_phone_digits()
    3. Agent calls GET /api/customers/verify?phone=5551234567
    4. Backend looks up in SQLite
    5. Returns customer info if found, 404 if not

    Query parameter: phone (comes from the URL: /api/customers/verify?phone=5551234567)
    Query(...) = "this parameter is required, no default"
    """
    # Clean the phone number (remove any dashes, spaces, etc.)
    cleaned_phone = "".join(char for char in phone if char.isdigit())

    customer = verify_customer_by_phone(cleaned_phone)  # SQLite lookup

    if not customer:
        # 404 = Not Found: customer doesn't exist in our database
        raise HTTPException(
            status_code=404,
            detail="Customer verification failed. Phone number not found."
        )

    # Return both the verified status and the customer's data
    return {
        "verified": True,
        "customer": customer   # {"id": 1, "name": "John Doe", "phone": "...", "email": "...", "status": "Premium"}
    }
```

### `/api/tickets` — Creating Support Tickets (Used by the AI Agent)

```python
# backend/routes.py

class CreateTicketRequest(BaseModel):
    customer_id: Optional[int] = None   # Optional: might be null for unverified callers
    category: str                        # "Complaint" or "Escalation"
    description: str                     # What the customer said

@router.post("/api/tickets")
def create_ticket(request: CreateTicketRequest):
    """
    Creates a support ticket in the SQLite database.

    Called by: agent/nodes.py → complaint_node() and escalate_node()

    complaint_node calls this when a customer reports a problem:
      - category="Complaint", description="My product arrived broken"

    escalate_node calls this when the customer requests a human:
      - category="Escalation", description="Customer requested human agent..."
    """
    try:
        ticket_id = create_support_ticket(
            customer_id=request.customer_id,
            category=request.category,
            description=request.description
        )
        return {
            "success": True,
            "message": "Support ticket created successfully.",
            "ticket_id": ticket_id   # e.g., 42 (auto-incremented integer from SQLite)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")
```

### `/api/rooms/active-sessions` — Dashboard: Active Call Sessions

```python
# backend/routes.py

@router.get("/api/rooms/active-sessions")
async def list_active_sessions():
    """
    Returns all call sessions from Supabase, with auto-healing for stale ones.

    Called by: The human agent support dashboard (React app in dashboard/)
    Used to show: which calls are active, session status, participant names, etc.

    The "auto-healing" part fixes a real-world problem:
    If the agent crashes or the server restarts, call_sessions in Supabase might
    still be marked "active" even though the LiveKit room is gone.
    This endpoint detects that mismatch and marks stale sessions as "completed".
    """
    client = get_supabase_client()
    if not client:
        return {"sessions": []}

    try:
        # Fetch the list of currently active rooms from LiveKit Cloud
        active_room_names = set()
        try:
            lk_client = get_livekit_api()
            async with lk_client as lkapi:
                lk_response = await lkapi.room.list_rooms(api.ListRoomsRequest())
                for r in lk_response.rooms:
                    active_room_names.add(r.name)  # e.g., {"support-abc12", "support-xyz99"}
        except Exception as e:
            logger.warning(f"Could not fetch rooms from LiveKit: {e}")
            active_room_names = None  # Don't auto-heal if we can't verify

        # Fetch all sessions from Supabase
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.table("call_sessions").select("*").order("started_at", desc=True).execute()
        )
        db_sessions = response.data or []

        verified_sessions = []
        for session in db_sessions:
            room_name = session.get("room_name")
            session_id = session.get("id")
            status = session.get("status")

            # If the session is marked "active" or "escalated" in DB,
            # but the room doesn't exist in LiveKit anymore → it's stale
            if status in ("active", "escalated"):
                if active_room_names is not None and room_name not in active_room_names:
                    # Auto-heal: mark as completed and calculate duration
                    logger.info(f"Session {session_id[:8]} is stale. Auto-healing.")
                    session["status"] = "completed"
                    # ... (update Supabase in background task)

            verified_sessions.append(session)

        return {"sessions": verified_sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")
```

### `/health` — System Health Check

```python
# backend/routes.py

@router.get("/health")
async def health_check():
    """
    Checks if all critical components are working.
    Returns detailed status for each component.

    Used by: monitoring tools, deployment checks, the dashboard
    Response example:
    {
        "status": "ok",
        "components": {
            "api": "ok",
            "sqlite_database": "ok (3 customers)",
            "supabase": "ok"
        },
        "environment": {
            "livekit_configured": true,
            "groq_configured": true,
            "deepgram_configured": true,
            "supabase_configured": true
        }
    }
    """
    component_statuses = {}
    overall_status = "ok"

    # Check 1: API itself is responding (if we got here, it's working)
    component_statuses["api"] = "ok"

    # Check 2: SQLite database
    try:
        customers = get_all_customers()
        component_statuses["sqlite_database"] = f"ok ({len(customers)} customers)"
    except Exception as e:
        component_statuses["sqlite_database"] = f"error: {str(e)}"
        overall_status = "error"

    # Check 3: Supabase connectivity
    try:
        supabase_ok = check_supabase_connection()  # Runs a simple .select() query
        component_statuses["supabase"] = "ok" if supabase_ok else "not connected"
        if not supabase_ok:
            overall_status = "degraded"  # Not full error, but not 100% healthy either
    except Exception as e:
        component_statuses["supabase"] = f"error: {str(e)}"
        overall_status = "degraded"

    # Check 4: Are all environment variables configured?
    env_status = {
        "livekit_configured": all([
            bool(os.getenv("LIVEKIT_URL")),
            bool(os.getenv("LIVEKIT_API_KEY")),
            bool(os.getenv("LIVEKIT_API_SECRET")),
        ]),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "deepgram_configured": bool(os.getenv("DEEPGRAM_STT_API_KEY")),
        "supabase_configured": all([
            bool(os.getenv("SUPABASE_URL")),
            bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        ]),
    }

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "3.0.0",
        "components": component_statuses,
        "environment": env_status,
    }
```

---

## How the Agent Calls the Backend — `agent/nodes.py`

The AI agent calls the FastAPI backend using `httpx` (an HTTP client for Python):

```python
# agent/nodes.py — how nodes call the FastAPI backend

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def verify_customer_node(state: AgentState, config: RunnableConfig = None) -> dict:
    # ...
    phone = extract_phone_digits(last_user_message)

    # Build the URL for the verify endpoint
    verify_url = f"{BACKEND_URL}/api/customers/verify?phone={phone}"

    try:
        # httpx.get() makes a synchronous HTTP GET request.
        # timeout=5.0 means: give up after 5 seconds (prevents hanging the call).
        response = httpx.get(verify_url, timeout=5.0)

        if response.status_code == 200:
            # response.json() parses the JSON response body into a Python dict
            customer_info = response.json().get("customer", {})
            customer_name = customer_info.get("name", "Customer")
            success_msg = f"Thank you. I have verified your account, {customer_name}."
            return {
                "messages": [AIMessage(content=success_msg)],
                "customer_verified": True,
                "customer_info": customer_info,
                "current_flow": state.get("target_flow") or "idle"
            }
        else:
            # 404 = customer not found
            return {"messages": [AIMessage(content="I couldn't find your account.")]}

    except Exception as e:
        # Network error, timeout, or backend is down
        logger.error(f"Failed to call verification backend: {str(e)}")
        return {
            "messages": [AIMessage(content="I'm having trouble connecting. Let me get a supervisor.")],
            "current_flow": "escalation"
        }
```

---

## Summary: API Endpoints at a Glance

| Endpoint | Method | Called By | What It Does |
|----------|--------|-----------|-------------|
| `/` | GET | Browser (health check) | Confirms server is running |
| `/health` | GET | Dashboard, monitoring | Detailed component status |
| `/api/token` | POST | Frontend React app | Generates LiveKit JWT |
| `/api/rooms` | GET | Dashboard | Lists active LiveKit rooms |
| `/api/rooms` | POST | Admin | Creates a room in advance |
| `/api/rooms/active-sessions` | GET | Dashboard | All call sessions + auto-heal |
| `/api/rooms/{id}/transcript` | GET | Dashboard | Full conversation transcript |
| `/api/customers` | GET | Dashboard | List all customers |
| `/api/customers` | POST | Agent (registration_node) | Register a new customer |
| `/api/customers/verify` | GET | Agent (verify_customer_node) | Look up customer by phone |
| `/api/tickets` | GET | Dashboard | List all support tickets |
| `/api/tickets` | POST | Agent (complaint_node, escalate_node) | Create a support ticket |

---

*Next up → [08_SUPABASE_DEEPDIVE.md](./08_SUPABASE_DEEPDIVE.md)*
