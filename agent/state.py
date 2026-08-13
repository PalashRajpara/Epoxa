from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Defines the structured state carried through the LangGraph conversation nodes.
    Using 'add_messages' annotation keeps a history of the chat context automatically.
    """
    # The history of chat messages exchanged in the session
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Customer verification fields
    customer_verified: bool
    customer_info: Optional[Dict[str, Any]]
    verification_attempts: int
    
    # State tracking details for business tasks
    appointment_details: Optional[Dict[str, Any]]
    complaint_details: Optional[Dict[str, Any]]
    
    # Flow orchestration tracks
    target_flow: Optional[str]   # Where to redirect (e.g., 'appointment', 'complaint') after successful verification
    current_flow: str            # Current conversation category ('greeting', 'verify', 'faq', 'booking', 'complaint', 'escalation', 'idle')
    
    # Registration step-by-step tracks
    registration_step: Optional[str]   # 'name', 'phone', 'email', 'done'
    reg_name: Optional[str]
    reg_phone: Optional[str]
    reg_email: Optional[str]
