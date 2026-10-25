import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.voice_repo import voice_repo
from app.repositories.ticket_repo import ticket_repo
from app.services.handoff_service import handoff_service
from app.core.exceptions import ConflictError

@pytest.mark.asyncio
async def test_supervisor_takeover_lifecycle(db_session: AsyncSession, org_a, supervisor_a):
    call = await voice_repo.create_session(
        db_session,
        org_id=org_a.id,
        room_name="test-room-lifecycle"
    )
    assert call.status == "initiating"

    # Set call to active
    await voice_repo.update_status(db_session, session_id=call.id, status="active")

    # 1. Takeover
    res = await handoff_service.request_takeover(
        db_session,
        org_id=org_a.id,
        session_id=call.id,
        supervisor_id=supervisor_a.id,
        supervisor_name=supervisor_a.full_name,
        notes="Customer sounds upset; taking over."
    )
    assert res["status"] == "supervisor_takeover"
    assert "token" in res

    # Verify DB state
    updated_call = await voice_repo.get_session_by_id(db_session, session_id=call.id)
    assert updated_call.status == "supervisor_takeover"
    assert updated_call.handoff_state == "accepted"

    # 2. Concurrency Conflict: second takeover attempt while active must fail
    second_sup_id = uuid.uuid4()
    with pytest.raises(ConflictError):
        await handoff_service.request_takeover(
            db_session,
            org_id=org_a.id,
            session_id=call.id,
            supervisor_id=second_sup_id,
            supervisor_name="Supervisor 2"
        )

    # 3. Handback to AI
    hb_res = await handoff_service.handback_to_ai(
        db_session,
        org_id=org_a.id,
        session_id=call.id,
        supervisor_id=supervisor_a.id,
        notes="Issue clarified; returned to AI."
    )
    assert hb_res["status"] == "active"
    assert hb_res["handoff_state"] == "returned_to_ai"

    # Verify DB state
    re_updated = await voice_repo.get_session_by_id(db_session, session_id=call.id)
    assert re_updated.status == "active"
    assert re_updated.handoff_state == "returned_to_ai"

@pytest.mark.asyncio
async def test_fallback_ticket_when_unavailable(db_session: AsyncSession, org_a):
    call = await voice_repo.create_session(
        db_session,
        org_id=org_a.id,
        room_name="test-room-fallback"
    )
    # Customer requested escalation
    await ticket_repo.create_escalation(
        db_session, org_id=org_a.id, session_id=call.id, reason="Customer wants manager"
    )

    # Supervisor unavailable -> Trigger fallback ticket
    fb_res = await handoff_service.create_fallback_ticket_if_unavailable(
        db_session,
        org_id=org_a.id,
        session_id=call.id,
        reason="No supervisors logged in"
    )
    assert fb_res["fallback_created"] is True
    assert "ticket_number" in fb_res
    assert fb_res["status"] == "open"

@pytest.mark.asyncio
async def test_supervisor_turn_human_voice_and_ai_synthesis(db_session: AsyncSession, org_a, supervisor_a):
    from app.api.v1.calls import supervisor_speech_turn, SupervisorTurnRequest
    from app.api.v1.voice import get_customer_supervisor_turns
    from app.schemas.auth import SupervisorContext

    # 1. Create active call session
    call = await voice_repo.create_session(
        db_session,
        org_id=org_a.id,
        room_name="test-room-supervisor-voice"
    )
    await voice_repo.update_status(db_session, session_id=call.id, status="supervisor_takeover")

    sup_ctx = SupervisorContext(
        user_id=supervisor_a.id,
        organization_id=org_a.id,
        role="supervisor",
        email=supervisor_a.email,
        full_name=supervisor_a.full_name
    )

    # 2. Test Real Human Voice Turn (audio_base64 provided from supervisor's live mic)
    dummy_audio_b64 = "GkXfo59ChoEBQveBAULygQ8="
    human_req = SupervisorTurnRequest(
        speech="Hello customer, I am the live supervisor",
        audio_base64=dummy_audio_b64,
        mime_type="audio/webm;codecs=opus"
    )
    human_res = await supervisor_speech_turn(
        session_id=call.id,
        req=human_req,
        supervisor=sup_ctx,
        db=db_session
    )
    assert human_res["is_human"] is True
    assert human_res["audio_base64"] == dummy_audio_b64
    assert human_res["mime_type"] == "audio/webm;codecs=opus"

    # Verify customer endpoint retrieves this human turn with exact audio
    cust_turns = await get_customer_supervisor_turns(
        session_id=call.id,
        org=org_a,
        db=db_session
    )
    assert len(cust_turns) == 1
    assert cust_turns[0]["is_human"] is True
    assert cust_turns[0]["audio_base64"] == dummy_audio_b64
    assert cust_turns[0]["mime_type"] == "audio/webm;codecs=opus"

    # 3. Test Typed Message Turn (no audio_base64 -> synthesized with AI Helios voice)
    typed_req = SupervisorTurnRequest(
        speech="I have approved your expedited replacement order.",
        audio_base64=None,
        mime_type="audio/webm"
    )
    typed_res = await supervisor_speech_turn(
        session_id=call.id,
        req=typed_req,
        supervisor=sup_ctx,
        db=db_session
    )
    assert typed_res["is_human"] is False
    assert typed_res["content"] == "I have approved your expedited replacement order."

    # Verify both turns exist in customer view
    cust_turns_all = await get_customer_supervisor_turns(
        session_id=call.id,
        org=org_a,
        db=db_session
    )
    assert len(cust_turns_all) == 2
