# Epoxa REST API Reference

Base URL: `/api/v1`

All responses are formatted in JSON with standardized error envelopes on failure.

---

## 1. Health & Diagnostics

### `GET /health/live`
Liveness probe for orchestrators and container health.
- **Response**: `200 OK`
```json
{ "status": "ok" }
```

### `GET /health/ready`
Readiness probe verifying database connectivity safely without exposing credentials.
- **Response**: `200 OK` (or `503 Service Unavailable` if database is degraded)
```json
{
  "status": "ready",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected",
  "livekit": "configured",
  "deepgram": "configured",
  "groq": "configured",
  "timestamp": "2026-10-25T12:00:00Z"
}
```

---

## 2. Customer Voice Interaction

### `POST /api/v1/voice/token`
Initiates a voice session and generates a short-lived, room-scoped LiveKit access token.
- **Request Body**:
```json
{
  "customer_name": "Sarah Connor",
  "customer_phone": "+15550192834"
}
```
- **Response**: `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "room_name": "epoxa-room-a1b2c3d4e5f6",
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "livekit_url": "wss://epoxa-demo.livekit.cloud",
  "expires_in_seconds": 900
}
```

### `POST /api/v1/voice/sessions/{session_id}/turn`
Submits a customer speech transcript turn to the LangGraph orchestrator.
- **Request Body**:
```json
{
  "speech": "What is your standard return policy?"
}
```
- **Response**: `200 OK`
```json
{
  "reply": "Our standard return policy allows customers to return any unused retail item within 30 days of delivery for a full refund. Items must include original packaging."
}
```

### `POST /api/v1/voice/sessions/{session_id}/end`
Terminates a call session and triggers automated AI call summary generation.
- **Response**: `200 OK`
```json
{
  "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "completed",
  "duration_seconds": 142,
  "summary": {
    "summary": "Customer inquired about the return window for a purchased retail product.",
    "primary_intent": "return_policy",
    "detected_sentiment": "neutral",
    "follow_up_required": false
  }
}
```

---

## 3. Supervisor Operations

### `GET /api/v1/calls/active`
Lists active voice calls for real-time monitoring on the supervisor dashboard.
- **Headers**: `Authorization: Bearer <SUPERVISOR_JWT>`
- **Response**: `200 OK`
```json
[
  {
    "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "room_name": "epoxa-room-a1b2c3d4e5f6",
    "status": "escalated",
    "handoff_state": "requested",
    "metadata": { "customer_name": "Sarah Connor" },
    "created_at": "2026-10-25T12:05:00Z"
  }
]
```

### `POST /api/v1/calls/{session_id}/takeover`
Allows an authorized supervisor to take over an ongoing or escalated customer call. The AI audio is muted immediately.
- **Headers**: `Authorization: Bearer <SUPERVISOR_JWT>`
- **Request Body**:
```json
{
  "action": "takeover_started",
  "notes": "Customer requested immediate manager assistance."
}
```
- **Response**: `200 OK`
```json
{
  "status": "supervisor_takeover",
  "room_name": "epoxa-room-a1b2c3d4e5f6",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Supervisor takeover active; AI audio suppressed."
}
```

### `POST /api/v1/calls/{session_id}/handback`
Hands conversation control back from the supervisor to the AI assistant.
- **Headers**: `Authorization: Bearer <SUPERVISOR_JWT>`
- **Request Body**:
```json
{
  "action": "handback_to_ai",
  "notes": "Issue resolved; returning to AI for wrap-up."
}
```
- **Response**: `200 OK`
```json
{
  "status": "active",
  "handoff_state": "returned_to_ai",
  "message": "Call control successfully returned to AI assistant."
}
```

---

## 4. Support Tickets

### `GET /api/v1/tickets?status=open&page=1`
Lists support tickets scoped to the authenticated supervisor's organization.
- **Headers**: `Authorization: Bearer <SUPERVISOR_JWT>`
- **Response**: `200 OK`
```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "ticket_number": "EPX-20261025-A101",
      "title": "Damaged package received on order #89211",
      "description": "Outer box crushed during transit.",
      "category": "technical",
      "priority": "high",
      "status": "open",
      "created_at": "2026-10-25T11:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```
