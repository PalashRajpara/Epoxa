import json
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.integrations.llm import llm_service
from app.agents.tools import TOOL_DEFINITIONS, tool_executor
from app.agents.prompts import SYSTEM_PROMPT_TEMPLATE, CALL_SUMMARY_PROMPT
from app.repositories.voice_repo import voice_repo
from app.repositories.tenant_repo import tenant_repo
from app.repositories.knowledge_repo import knowledge_repo

class ConversationOrchestrator:
    """Orchestrates conversation turn flow, tool execution, and transcript persistence."""

    async def handle_turn(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        user_speech: str,
        customer_id: Optional[uuid.UUID] = None
    ) -> str:
        """Processes one customer speech turn, invokes tools if needed, logs transcripts, and returns AI reply."""
        # 1. Persist customer transcript turn
        await voice_repo.add_transcript_turn(
            db, session_id=session_id, org_id=org_id, speaker="customer", content=user_speech
        )
        await voice_repo.add_event(
            db, session_id=session_id, event_type="customer_speech", actor="customer", payload={"text": user_speech}
        )

        # 2. Build conversation context
        past_turns = await voice_repo.get_transcripts(db, session_id=session_id)
        org = await tenant_repo.get_organization_by_id(db, org_id=org_id)
        org_name = org.name if org else "Epoxa"

        # Check custom agent config
        agent_cfg = await knowledge_repo.get_active_agent_config(db, org_id=org_id)
        system_prompt = agent_cfg.system_prompt if agent_cfg else SYSTEM_PROMPT_TEMPLATE.format(org_name=org_name)

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in past_turns[-8:]:  # Keep recent context window
            role = "assistant" if turn.speaker == "ai_agent" else "user"
            messages.append({"role": role, "content": turn.content or ""})

        # 3. LLM generation with tools
        llm_output = await llm_service.generate_response(
            messages=messages,
            tools=TOOL_DEFINITIONS
        )

        tool_calls = llm_output.get("tool_calls", [])
        ai_reply = llm_output.get("content", "")

        # 4. If tools requested, execute them and generate grounded follow-up
        if tool_calls:
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                raw_args = tc["function"]["arguments"]
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                tool_result = await tool_executor.execute_tool(
                    db,
                    tool_name=fn_name,
                    arguments=args,
                    org_id=org_id,
                    session_id=session_id,
                    customer_id=customer_id
                )

                messages.append({
                    "role": "assistant",
                    "content": f"[Invoked {fn_name} with {json.dumps(args)}]"
                })
                messages.append({
                    "role": "system",
                    "content": f"Tool '{fn_name}' returned: {json.dumps(tool_result)}. Now formulate a concise, spoken reply to the customer."
                })

            # Re-generate grounded spoken response
            follow_up = await llm_service.generate_response(messages=messages)
            ai_reply = follow_up.get("content", "")

        if not ai_reply.strip():
            ai_reply = "I understand. Let me check our system for you. Could you please confirm any details?"

        # 5. Persist AI transcript turn
        await voice_repo.add_transcript_turn(
            db, session_id=session_id, org_id=org_id, speaker="ai_agent", content=ai_reply
        )
        await voice_repo.add_event(
            db, session_id=session_id, event_type="agent_speech", actor="ai_agent", payload={"text": ai_reply}
        )

        return ai_reply

    async def generate_call_summary(
        self, db: AsyncSession, org_id: uuid.UUID, session_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Generates and persists an objective summary at call completion."""
        turns = await voice_repo.get_transcripts(db, session_id=session_id)
        if not turns:
            return {"summary": "Brief session ended without conversation."}

        dialogue = "\n".join([f"{t.speaker}: {t.content}" for t in turns if t.content])
        messages = [
            {"role": "system", "content": CALL_SUMMARY_PROMPT},
            {"role": "user", "content": f"Transcript:\n{dialogue}"}
        ]

        llm_res = await llm_service.generate_response(messages=messages, temperature=0.0)
        content = llm_res.get("content", "")

        try:
            summary_data = json.loads(content)
        except Exception:
            summary_data = {
                "summary": "Customer inquiry resolved or escalated during voice session.",
                "primary_intent": "general_inquiry",
                "detected_sentiment": "neutral",
                "follow_up_required": False
            }

        await voice_repo.upsert_summary(
            db,
            session_id=session_id,
            org_id=org_id,
            summary_text=summary_data.get("summary", ""),
            intent=summary_data.get("primary_intent"),
            sentiment=summary_data.get("detected_sentiment"),
            follow_up=bool(summary_data.get("follow_up_required", False))
        )

        return summary_data

orchestrator = ConversationOrchestrator()
