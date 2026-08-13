import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from livekit import api

# Flat imports from the same directory level
from database import (
    verify_customer_by_phone,
    get_all_customers,
    create_customer,
    create_support_ticket,
    get_all_tickets,
    check_supabase_connection,
    get_supabase_client,
    get_full_transcript
)

logger = logging.getLogger("backend.routes")

# Create a central APIRouter to register all endpoints
router = APIRouter()


# =============================================================================
# TOKEN GENERATOR ROUTE (/api/token)
# =============================================================================

class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    role: Optional[str] = "customer"  # "customer" or "agent"

@router.post("/api/token")
async def generate_token(request: TokenRequest):
    """
    Generates a secure JWT token for a participant to join a LiveKit room.
    """
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="LiveKit API Key or Secret is not configured in the environment."
        )
        
    prefix = "agent" if request.role == "agent" else "customer"
    unique_identity = f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    try:
        token = (
            api.AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(unique_identity)
            .with_name(request.participant_name)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=request.room_name
                )
            )
        )
        return {
            "token": token.to_jwt(),
            "identity": unique_identity,
            "room": request.room_name,
            "participant_name": request.participant_name,
            "server_url": os.getenv("LIVEKIT_URL")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the token: {str(e)}"
        )


# =============================================================================
# LIVEKIT ROOM CONTROL ROUTES (/api/rooms)
# =============================================================================

class CreateRoomRequest(BaseModel):
    name: str
    empty_timeout: int = 300
    max_participants: int = 20

def get_livekit_api():
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not url or not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="LiveKit credentials (URL, Key, Secret) are not fully configured in the environment."
        )
    return api.LiveKitAPI(url=url, api_key=api_key, api_secret=api_secret)


@router.get("/api/rooms")
async def list_rooms():
    """
    Lists all active rooms currently running on the LiveKit server.
    """
    try:
        client = get_livekit_api()
        async with client as lkapi:
            response = await lkapi.room.list_rooms(api.ListRoomsRequest())
            rooms = []
            for room in response.rooms:
                rooms.append({
                    "sid": room.sid,
                    "name": room.name,
                    "num_participants": room.num_participants,
                    "max_participants": room.max_participants,
                    "empty_timeout": room.empty_timeout
                })
            return {"rooms": rooms}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch active rooms from LiveKit: {str(e)}"
        )


@router.post("/api/rooms")
async def create_room(request: CreateRoomRequest):
    """
    Creates a new room on the LiveKit server in advance.
    """
    try:
        client = get_livekit_api()
        async with client as lkapi:
            create_req = api.CreateRoomRequest(
                name=request.name,
                empty_timeout=request.empty_timeout,
                max_participants=request.max_participants
            )
            room_info = await lkapi.room.create_room(create_req)
            return {
                "message": "Room created successfully",
                "room": {
                    "sid": room_info.sid,
                    "name": room_info.name,
                    "max_participants": room_info.max_participants,
                    "empty_timeout": room_info.empty_timeout
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create room: {str(e)}"
        )


@router.get("/api/rooms/active-sessions")
async def list_active_sessions():
    """
    Queries active sessions and auto-heals stale sessions (where the room is no longer active on LiveKit).
    """
    try:
        # 1. Fetch currently active rooms from LiveKit server
        active_room_names = set()
        try:
            lk_client = get_livekit_api()
            async with lk_client as lkapi:
                lk_response = await lkapi.room.list_rooms(api.ListRoomsRequest())
                for r in lk_response.rooms:
                    active_room_names.add(r.name)
        except Exception as e:
            logger.warning(f"Could not fetch active rooms from LiveKit: {e}")
            active_room_names = None
            
        # 2. Query call sessions from database (SQLite local + Supabase cloud)
        from database import get_all_call_sessions
        loop = asyncio.get_event_loop()
        db_sessions = await loop.run_in_executor(
            None,
            get_all_call_sessions
        )

        verified_sessions = []
        
        # 3. Auto-heal stale sessions
        for session in db_sessions:
            room_name = session.get("room_name")
            session_id = session.get("id")
            status = session.get("status")
            
            if status in ("active", "escalated"):
                if active_room_names is not None and room_name not in active_room_names:
                    logger.info(f"Session {session_id[:8]} is stale. Auto-healing to 'completed'.")
                    session["status"] = "completed"
                    
                    now_iso = datetime.now(timezone.utc).isoformat()
                    try:
                        started_str = session.get("started_at")
                        if started_str:
                            started_str = started_str.replace("Z", "+00:00")
                            started_dt = datetime.fromisoformat(started_str)
                            duration = int((datetime.now(timezone.utc) - started_dt).total_seconds())
                        else:
                            duration = 0
                        if duration < 0:
                            duration = 0
                    except Exception:
                        duration = 0

                    session["ended_at"] = now_iso
                    session["duration_seconds"] = duration

                    try:
                        from database import complete_call_session
                        asyncio.create_task(loop.run_in_executor(
                            None,
                            lambda s_id=session_id, dur=duration: complete_call_session(s_id, "completed", dur)
                        ))
                    except Exception as err:
                        logger.warning(f"Failed to update stale session: {err}")

            verified_sessions.append(session)
        return {"sessions": verified_sessions}
    except Exception as e:
        logger.error(f"Error listing active sessions: {e}")
        return {"sessions": []}


@router.get("/api/rooms/{session_id}/transcript")
async def get_session_transcript(session_id: str):
    """
    Retrieves transcripts and status for a session.
    """
    try:
        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(
            None,
            lambda: get_full_transcript(session_id)
        )
        
        status = "completed"
        client = get_supabase_client()
        if client:
            try:
                res = await loop.run_in_executor(
                    None,
                    lambda: client.table("call_sessions").select("status").eq("id", session_id).execute()
                )
                if res.data:
                    status = res.data[0].get("status", "completed")
            except Exception as sb_err:
                logger.warning(f"Failed to fetch session status from Supabase: {sb_err}")
                
        return {
            "transcript": transcript,
            "status": status
        }
    except Exception as e:
        logger.error(f"Failed to fetch transcript for {session_id}: {e}")
        return {
            "transcript": [],
            "status": "completed"
        }


# =============================================================================
# CUSTOMER PROFILE ROUTES (/api/customers)
# =============================================================================

class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: str

@router.post("/api/customers")
def register_customer(customer: CustomerCreate):
    """
    Registers a new customer profile.
    """
    new_cust = create_customer(
        name=customer.name,
        phone=customer.phone,
        email=customer.email
    )
    if not new_cust:
        raise HTTPException(
            status_code=400,
            detail="Failed to register customer. Phone number may already exist."
        )
    return new_cust


@router.get("/api/customers/verify")
def verify_customer(phone: str = Query(..., description="Phone number to verify")):
    """
    Checks database for matching customer phone numbers.
    """
    cleaned_phone = "".join(char for char in phone if char.isdigit())
    customer = verify_customer_by_phone(cleaned_phone)
    if not customer:
        raise HTTPException(
            status_code=404, 
            detail="Customer verification failed. Phone number not found."
        )
    return {
        "verified": True,
        "customer": customer
    }


@router.get("/api/customers")
def list_customers():
    return {"customers": get_all_customers()}


# =============================================================================
# SUPPORT TICKETS ROUTES (/api/tickets)
# =============================================================================

class CreateTicketRequest(BaseModel):
    customer_id: Optional[int] = None
    category: str
    description: str

@router.post("/api/tickets")
def create_ticket(request: CreateTicketRequest):
    """
    Creates a new support ticketing issue.
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
            "ticket_id": ticket_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record support ticket: {str(e)}"
        )


@router.get("/api/tickets")
def list_tickets():
    return {"tickets": get_all_tickets()}


# =============================================================================
# HEALTH STATUS MONITOR ROUTE (/health)
# =============================================================================

@router.get("/health")
async def health_check():
    """
    Performs critical heartbeat checks on sqlite tables and Supabase.
    """
    component_statuses = {}
    overall_status = "ok"

    component_statuses["api"] = "ok"

    try:
        customers = get_all_customers()
        component_statuses["sqlite_database"] = f"ok ({len(customers)} customers)"
    except Exception as e:
        logger.error(f"[Health] SQLite check failed: {e}")
        component_statuses["sqlite_database"] = f"error: {str(e)}"
        overall_status = "error"

    try:
        supabase_ok = check_supabase_connection()
        if supabase_ok:
            component_statuses["supabase"] = "ok"
        else:
            component_statuses["supabase"] = "not connected"
            if overall_status == "ok":
                overall_status = "degraded"
    except Exception as e:
        logger.error(f"[Health] Supabase check failed: {e}")
        component_statuses["supabase"] = f"error: {str(e)}"
        if overall_status == "ok":
            overall_status = "degraded"

    env_status = {
        "livekit_configured": all([
            bool(os.getenv("LIVEKIT_URL")),
            bool(os.getenv("LIVEKIT_API_KEY")),
            bool(os.getenv("LIVEKIT_API_SECRET")),
        ]),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "deepgram_configured": bool(os.getenv("DEEPGRAM_API_KEY") or os.getenv("DEEPGRAM_STT_API_KEY")),
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
