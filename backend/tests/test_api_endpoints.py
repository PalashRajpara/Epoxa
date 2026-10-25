import pytest
import httpx

@pytest.mark.asyncio
async def test_health_endpoints(client: httpx.AsyncClient):
    # Liveness
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # Readiness
    resp = await client.get("/health/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert data["status"] in ("ready", "degraded")
    assert "version" in data

@pytest.mark.asyncio
async def test_voice_token_issuance(client: httpx.AsyncClient):
    resp = await client.post(
        "/api/v1/voice/token",
        json={"customer_name": "Test Caller", "customer_phone": "+15550001111"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "room_name" in data
    assert "session_id" in data
    assert data["room_name"].startswith("epoxa-room-")

@pytest.mark.asyncio
async def test_speech_turn_processing(client: httpx.AsyncClient):
    # 1. Initiate session
    token_resp = await client.post("/api/v1/voice/token", json={})
    session_id = token_resp.json()["session_id"]

    # 2. Send speech turn
    turn_resp = await client.post(
        f"/api/v1/voice/sessions/{session_id}/turn",
        json={"speech": "Hello, what is your standard return policy?"}
    )
    assert turn_resp.status_code == 200
    data = turn_resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 5

    # 3. End session
    end_resp = await client.post(f"/api/v1/voice/sessions/{session_id}/end")
    assert end_resp.status_code == 200
    assert end_resp.json()["status"] == "completed"

@pytest.mark.asyncio
async def test_ticket_crud_endpoints(client: httpx.AsyncClient):
    # Create ticket
    create_resp = await client.post(
        "/api/v1/tickets",
        json={
            "title": "Broken item received",
            "description": "Item arrived broken in shipment",
            "category": "technical",
            "priority": "high"
        }
    )
    assert create_resp.status_code == 200
    ticket = create_resp.json()
    assert "ticket_number" in ticket
    assert ticket["title"] == "Broken item received"
    ticket_id = ticket["id"]

    # List tickets
    list_resp = await client.get("/api/v1/tickets")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # Update ticket
    patch_resp = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "resolved"

@pytest.mark.asyncio
async def test_supervisor_database_login(client: httpx.AsyncClient):
    # 1. Test invalid password rejected with 401
    bad_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "sup_a@tenant-a.com", "password": "WrongPassword!"}
    )
    assert bad_resp.status_code == 401

    # 2. Test non-existent user rejected with 401
    missing_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@tenant-a.com", "password": "AnyPassword"}
    )
    assert missing_resp.status_code == 401

    # 3. Test valid password succeeds with 200 and issues JWT
    good_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "sup_a@tenant-a.com", "password": "ValidPass123!"}
    )
    assert good_resp.status_code == 200
    data = good_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sup_a@tenant-a.com"

@pytest.mark.asyncio
async def test_handoff_announcements_endpoint(client: httpx.AsyncClient):
    # Test takeover announcement
    takeover_resp = await client.get("/api/v1/voice/announcement?type=takeover")
    assert takeover_resp.status_code == 200
    takeover_data = takeover_resp.json()
    assert takeover_data["announcement_type"] == "takeover"
    assert "supervisor has joined" in takeover_data["text"]

    # Test handback announcement
    handback_resp = await client.get("/api/v1/voice/announcement?type=handback")
    assert handback_resp.status_code == 200
    handback_data = handback_resp.json()
    assert handback_data["announcement_type"] == "handback"
    assert "Epoxa AI, and I am back" in handback_data["text"]

