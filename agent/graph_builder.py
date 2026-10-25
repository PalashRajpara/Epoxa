import os
import logging
from typing import Literal
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Flat imports from the same directory
from state import AgentState
from nodes import (
    greeting_node,
    verify_customer_node,
    registration_node,
    faq_node,
    appointment_node,
    complaint_node,
    escalate_node,
    general_chat_node,
    classify_intent,
    classify_customer_type
)
from handoff import is_handoff_active

logger = logging.getLogger("graph-builder")

def entry_router(state: AgentState) -> Literal["greeting", "route_input"]:
    """
    Entry router determines if this is the start of the call (no customer input)
    or if we should process user speech.
    """
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], HumanMessage):
        return "route_input"
    return "greeting"


def router_node(state: AgentState) -> dict:
    """
    Inspects the state to decide the next node.
    It preserves active flows (verify, registration, booking, complaint) to keep the conversation on track.
    If idle, it classifies the new user intent.
    Escalation intent takes global precedence.
    """
    messages = state.get("messages", [])
    current_flow = state.get("current_flow", "idle")
    
    # 1. Fast path check for escalation (explicit customer keywords)
    # This prevents running the LLM classifier if they just ask for a human
    # Uses word-boundary regex to avoid false-positives like "superhuman" or
    # "I don't want a human" where the keyword appears but intent is different.
    if messages:
        user_message = messages[-1].content.lower()
        import re
        escalation_pattern = r'\b(speak\s+to\s+a?\s*human|talk\s+to\s+a?\s*human|transfer\s+me|speak\s+to\s+a?\s*(representative|agent|supervisor|manager)|handover|hand\s+me\s+over|connect\s+me\s+to\s+a?\s*human|i\s+want\s+a?\s*(human|representative|agent|supervisor|manager))\b'
        if re.search(escalation_pattern, user_message):
            return {"current_flow": "escalation"}
            
    # 2. Check if we have an ongoing active flow.
    # If active, we SKIP intent classification entirely to avoid slow Groq LLM API overhead (saves 1-2s).
    if current_flow == "verify":
        # Check if the user response decides new vs existing customer
        if messages:
            user_message = messages[-1].content.lower()
            
            # If they provided a phone number directly, let it process
            from nodes import extract_phone_digits
            phone = extract_phone_digits(user_message)
            if phone:
                return {"target_flow": state.get("target_flow"), "current_flow": "verify"}
                
            cust_type = classify_customer_type(user_message)
            if cust_type == "new":
                return {"current_flow": "registration", "registration_step": None}
            elif cust_type == "existing":
                return {"target_flow": state.get("target_flow"), "current_flow": "verify"}
                
        return {"target_flow": state.get("target_flow"), "current_flow": "verify"}
        
    elif current_flow == "registration":
        return {"current_flow": "registration"}
    elif current_flow == "booking":
        return {"current_flow": "booking"}
    elif current_flow == "complaint":
        return {"current_flow": "complaint"}
        
    # 3. If idle, classify intent to route to the correct flow
    intent = "chat"
    if messages:
        user_msg_obj = messages[-1]
        user_message = user_msg_obj.content if isinstance(user_msg_obj.content, str) else str(user_msg_obj.content or "")
        intent = classify_intent(user_message)
        logger.info(f"Classified customer intent: {intent}")
        if intent == "escalate":
            print(f"🎯 [ROUTER]: Intent='escalate' -> routing to ESCALATION", flush=True)
            return {"current_flow": "escalation"}
            
    # 4. Route based on intent and verification requirements
    if intent == "appointment":
        if state.get("customer_verified"):
            print(f"🎯 [ROUTER]: Intent='appointment' (Verified) -> routing to BOOKING", flush=True)
            return {"current_flow": "booking"}
        else:
            print(f"🎯 [ROUTER]: Intent='appointment' (Unverified) -> routing to VERIFY", flush=True)
            return {"target_flow": "booking", "current_flow": "verify"}
            
    elif intent == "complaint":
        if state.get("customer_verified"):
            print(f"🎯 [ROUTER]: Intent='complaint' (Verified) -> routing to COMPLAINT", flush=True)
            return {"current_flow": "complaint"}
        else:
            print(f"🎯 [ROUTER]: Intent='complaint' (Unverified) -> routing to VERIFY", flush=True)
            return {"target_flow": "complaint", "current_flow": "verify"}
            
    elif intent == "faq":
        print(f"🎯 [ROUTER]: Intent='faq' -> routing to FAQ (ChromaDB RAG)", flush=True)
        return {"current_flow": "faq"}
        
    # Default to chat
    print(f"🎯 [ROUTER]: Intent='chat' -> routing to GENERAL CHAT", flush=True)
    return {"current_flow": "chat"}


def route_flow_edge(state: AgentState) -> Literal["verify_customer", "registration", "faq", "appointment", "complaint", "escalate", "general_chat"]:
    """
    Directs transitions to the correct processing node based on the flow set in router_node.
    """
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


def build_graph():
    """
    Assembles, connects, and compiles the customer support LangGraph.
    Uses in-memory checkpointer to maintain conversational history across turns.
    """
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node("greeting", greeting_node)
    builder.add_node("route_input", router_node)
    builder.add_node("verify_customer", verify_customer_node)
    builder.add_node("registration", registration_node)
    builder.add_node("faq", faq_node)
    builder.add_node("appointment", appointment_node)
    builder.add_node("complaint", complaint_node)
    builder.add_node("general_chat", general_chat_node)
    builder.add_node("escalate", escalate_node)
    
    # Add initial conditional routing from start
    builder.add_conditional_edges(
        START,
        entry_router,
        {
            "greeting": "greeting",
            "route_input": "route_input"
        }
    )
    
    # Connect greeting to end (it will end the turn and wait for user utterance)
    builder.add_edge("greeting", END)
    
    # Add conditional routing from route_input
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
            "general_chat": "general_chat"
        }
    )
    
    # Connect all processing nodes to end of turn
    builder.add_edge("verify_customer", END)
    builder.add_edge("registration", END)
    builder.add_edge("faq", END)
    builder.add_edge("appointment", END)
    builder.add_edge("complaint", END)
    builder.add_edge("general_chat", END)
    builder.add_edge("escalate", END)
    
    # Compile with memory checkpointer for persistence
    memory = MemorySaver()
    compiled_graph = builder.compile(checkpointer=memory)
    
    return compiled_graph


# Custom LiveKit LLM Wrapper to execute LangGraph state machine turns
from livekit.agents import llm
from livekit.agents.utils import aio
import asyncio

class LangGraphLLM(llm.LLM):
    """
    Custom LiveKit LLM subclass that wraps the LangGraph compiled state graph.
    Translates incoming LiveKit ChatContext to LangChain format, invokes the graph,
    and returns a streaming connection.
    """
    def __init__(self, graph, thread_id: str):
        super().__init__()
        self.graph = graph
        self.thread_id = thread_id

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool] | None = None,
        **kwargs
    ) -> llm.LLMStream:
        """
        Invoked by the pipeline agent. Returns our custom LangGraphStream.
        """
        return LangGraphStream(self, chat_ctx, self.graph)

class LangGraphStream(llm.LLMStream):
    """
    Streaming implementation for our custom LangGraph LLM integration.
    Feeds chunks word-by-word into the event channel to simulate natural TTS synthesis pacing.
    """
    def __init__(self, llm_obj: LangGraphLLM, chat_ctx: llm.ChatContext, graph):
        from livekit.agents.llm.llm import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(
            llm=llm_obj,
            chat_ctx=chat_ctx,
            fnc_ctx=None,
            conn_options=DEFAULT_API_CONNECT_OPTIONS
        )
        self.graph = graph

    async def _run(self) -> None:
        try:
            # Check if handoff is active for this session
            if is_handoff_active(self._llm.thread_id):
                logger.info(f"[GraphStream] Handoff active for session {self._llm.thread_id[:8]}. Muting AI response.")
                return

            # 1. Map LiveKit chat context to LangChain messages safely
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
            lc_messages = []
            for msg in self._chat_ctx.messages:
                content_str = msg.content if isinstance(msg.content, str) else " ".join([str(c) for c in msg.content]) if isinstance(msg.content, list) else str(msg.content or "")
                if not content_str.strip():
                    continue
                if msg.role == "system":
                    lc_messages.append(SystemMessage(content=content_str))
                elif msg.role == "user":
                    lc_messages.append(HumanMessage(content=content_str))
                elif msg.role == "assistant":
                    lc_messages.append(AIMessage(content=content_str))

            # Print latest user input directly to terminal
            last_human = next((m.content for m in reversed(lc_messages) if isinstance(m, HumanMessage)), "")
            if last_human:
                print(f"\n🎙️ [USER SPOKE]: \"{last_human}\"", flush=True)

            # 2. Run the graph state machine with dynamic checkpointer thread_id
            config = {"configurable": {"thread_id": self._llm.thread_id}}
            result = await self.graph.ainvoke({"messages": lc_messages}, config=config)

            # 3. Stream back the latest AIMessage generated by the graph node
            messages = result.get("messages", [])
            if messages and isinstance(messages[-1], AIMessage):
                content = messages[-1].content
                print(f"🤖 [EPIXA AI REPLY]: \"{content}\"\n", flush=True)
                
                # Send the complete response cleanly to TTS without artificial sleep gaps
                choice_delta = llm.ChoiceDelta(role="assistant", content=content)
                choice = llm.Choice(delta=choice_delta, index=0)
                chunk = llm.ChatChunk(request_id="langgraph", choices=[choice])
                self._event_ch.send_nowait(chunk)
            else:
                choice_delta = llm.ChoiceDelta(role="assistant", content="I'm here to help. What can I do for you today?")
                choice = llm.Choice(delta=choice_delta, index=0)
                chunk = llm.ChatChunk(request_id="langgraph", choices=[choice])
                self._event_ch.send_nowait(chunk)
        except Exception as e:
            logger.error(f"Error in LangGraph custom stream executor: {str(e)}")
        finally:
            # Always close event channel to terminate stream
            self._event_ch.close()

# Compile the graph globally once on import
compiled_graph = build_graph()
