"""LangGraph StateGraph builder and LiveKit LLM adapter for Epoxa Voice Agent."""

from typing import Literal
import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from epoxa_agent.handoff import is_ai_silenced
from epoxa_agent.nodes import (
    appointment_node,
    classify_customer_type,
    classify_intent,
    complaint_node,
    escalate_node,
    extract_phone_number,
    faq_node,
    general_chat_node,
    greeting_node,
    is_escalation_intent,
    registration_node,
    verify_customer_node,
)
from epoxa_agent.state import AgentState

logger = structlog.get_logger("epoxa_agent.graph")

def entry_router(state: AgentState) -> Literal["greeting", "route_input"]:
    """Determine whether starting a new call or processing caller utterance."""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], HumanMessage):
        return "route_input"
    return "greeting"

async def router_node(state: AgentState) -> dict:
    """
    State router preserving active flows and prioritizing escalation.
    - Escalation regex runs first.
    - Active flows (verify, registration, booking, complaint) skip classification to preserve context and speed.
    - Idle state classifies intent and checks verification gate.
    """
    messages = state.get("messages", [])
    current_flow = state.get("current_flow", "chat")

    if messages:
        user_message = str(messages[-1].content)
        # Fast path check for escalation keywords using word-boundary regex
        if is_escalation_intent(user_message):
            logger.info("router_escalation_fast_path", flow="escalation")
            return {"current_flow": "escalation"}

    # Active flow preservation
    if current_flow == "verify":
        if messages:
            user_msg = str(messages[-1].content)
            phone = extract_phone_number(user_msg)
            if phone:
                return {"target_flow": state.get("target_flow"), "current_flow": "verify"}
            cust_type = classify_customer_type(user_msg)
            if cust_type == "new":
                return {"current_flow": "registration", "registration_step": None}
        return {"target_flow": state.get("target_flow"), "current_flow": "verify"}

    elif current_flow == "registration":
        return {"current_flow": "registration"}
    elif current_flow == "booking":
        return {"current_flow": "booking"}
    elif current_flow == "complaint":
        return {"current_flow": "complaint"}

    # Idle turn: classify intent
    user_text = str(messages[-1].content) if messages else ""
    intent = classify_intent(user_text)
    logger.info("router_classified_intent", intent=intent)

    if intent == "escalate":
        return {"current_flow": "escalation"}

    if intent == "appointment":
        if state.get("customer_verified"):
            return {"current_flow": "booking"}
        return {"target_flow": "booking", "current_flow": "verify"}

    if intent == "complaint":
        if state.get("customer_verified"):
            return {"current_flow": "complaint"}
        return {"target_flow": "complaint", "current_flow": "verify"}

    if intent == "faq":
        return {"current_flow": "faq"}

    return {"current_flow": "chat"}

def route_flow_edge(
    state: AgentState,
) -> Literal[
    "verify_customer", "registration", "faq", "appointment", "complaint", "escalate", "general_chat"
]:
    flow = state.get("current_flow", "chat")
    if flow == "verify":
        return "verify_customer"
    elif flow == "registration":
        return "registration"
    elif flow == "faq":
        return "faq"
    elif flow == "booking":
        return "appointment"
    elif flow == "complaint":
        return "complaint"
    elif flow == "escalation":
        return "escalate"
    else:
        return "general_chat"

def build_graph() -> StateGraph:
    """Assembles and compiles Epoxa conversation StateGraph with in-memory checkpointer."""
    builder = StateGraph(AgentState)

    builder.add_node("greeting", greeting_node)
    builder.add_node("route_input", router_node)
    builder.add_node("verify_customer", verify_customer_node)
    builder.add_node("registration", registration_node)
    builder.add_node("faq", faq_node)
    builder.add_node("appointment", appointment_node)
    builder.add_node("complaint", complaint_node)
    builder.add_node("general_chat", general_chat_node)
    builder.add_node("escalate", escalate_node)

    builder.add_conditional_edges(
        START,
        entry_router,
        {"greeting": "greeting", "route_input": "route_input"},
    )
    builder.add_edge("greeting", END)

    builder.add_conditional_edges(
        "route_input",
        route_flow_edge,
        {
            "verify_customer": "verify_customer",
            "registration": "registration",
            "faq": "faq",
            "appointment": "appointment",
            "complaint": "complaint",
            "escalate": "escalate",
            "general_chat": "general_chat",
        },
    )

    builder.add_edge("verify_customer", END)
    builder.add_edge("registration", END)
    builder.add_edge("faq", END)
    builder.add_edge("appointment", END)
    builder.add_edge("complaint", END)
    builder.add_edge("general_chat", END)
    builder.add_edge("escalate", END)

    return builder.compile(checkpointer=MemorySaver())


# =============================================================================
# LIVEKIT AGENTS LLM ADAPTER
# =============================================================================
try:
    from livekit.agents import llm

    class LangGraphLLM(llm.LLM):
        """LiveKit LLM adapter wrapping LangGraph conversational StateGraph."""

        def __init__(self, graph: Any, thread_id: str) -> None:
            super().__init__()
            self.graph = graph
            self.thread_id = thread_id

        def chat(
            self,
            *,
            chat_ctx: llm.ChatContext,
            tools: list[llm.Tool] | None = None,
            **kwargs: Any,
        ) -> llm.LLMStream:
            return LangGraphStream(self, chat_ctx, self.graph)

    class LangGraphStream(llm.LLMStream):
        """Custom LLMStream feeding graph output directly into LiveKit audio pipeline."""

        def __init__(self, llm_obj: LangGraphLLM, chat_ctx: llm.ChatContext, graph: Any) -> None:
            from livekit.agents.llm.llm import DEFAULT_API_CONNECT_OPTIONS
            super().__init__(
                llm=llm_obj,
                chat_ctx=chat_ctx,
                fnc_ctx=None,
                conn_options=DEFAULT_API_CONNECT_OPTIONS,
            )
            self.graph = graph

        async def _run(self) -> None:
            try:
                # Check if human agent takeover is active (silence AI)
                if is_ai_silenced(self._llm.thread_id):
                    logger.info("handoff_muted_ai_turn", session_id=self._llm.thread_id)
                    return

                lc_messages = []
                for msg in self._chat_ctx.messages:
                    content_str = (
                        msg.content
                        if isinstance(msg.content, str)
                        else " ".join([str(c) for c in msg.content])
                        if isinstance(msg.content, list)
                        else str(msg.content or "")
                    )
                    if not content_str.strip():
                        continue
                    if msg.role == "system":
                        lc_messages.append(SystemMessage(content=content_str))
                    elif msg.role == "user":
                        lc_messages.append(HumanMessage(content=content_str))
                    elif msg.role == "assistant":
                        lc_messages.append(AIMessage(content=content_str))

                config = {"configurable": {"thread_id": self._llm.thread_id}}
                result = await self.graph.ainvoke({"messages": lc_messages}, config=config)

                messages = result.get("messages", [])
                if messages and isinstance(messages[-1], AIMessage):
                    content = str(messages[-1].content)
                else:
                    content = "I am listening. How can I assist you today?"

                choice_delta = llm.ChoiceDelta(role="assistant", content=content)
                choice = llm.Choice(delta=choice_delta, index=0)
                chunk = llm.ChatChunk(request_id="langgraph", choices=[choice])
                self._event_ch.send_nowait(chunk)
            except Exception as e:
                logger.error("langgraph_stream_error", error=str(e))
            finally:
                self._event_ch.close()

except ImportError:
    # Graceful fallback when LiveKit is not in current environment during unit tests
    class LangGraphLLM:  # type: ignore
        pass

    class LangGraphStream:  # type: ignore
        pass
