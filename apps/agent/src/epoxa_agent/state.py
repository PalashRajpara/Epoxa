"""AgentState definition for Epoxa Voice Agent LangGraph conversation engine."""

from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """Structured state carried through the LangGraph voice nodes."""

    # Complete conversational history of this session
    messages: Annotated[List[BaseMessage], add_messages]

    # Customer verification & identity context
    customer_verified: bool
    customer_info: Optional[Dict[str, Any]]
    verification_attempts: int

    # Business entity state
    appointment_details: Optional[Dict[str, Any]]
    complaint_details: Optional[Dict[str, Any]]

    # Flow coordination
    target_flow: Optional[str]  # e.g., 'booking', 'complaint'
    current_flow: str           # 'greeting', 'verify', 'registration', 'faq', 'booking', 'complaint', 'escalation', 'chat'

    # Step-by-step caller registration
    registration_step: Optional[str]  # 'name', 'phone', 'email', 'done'
    reg_name: Optional[str]
    reg_phone: Optional[str]
    reg_email: Optional[str]
