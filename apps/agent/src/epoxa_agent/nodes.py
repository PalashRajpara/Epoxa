"""LangGraph nodes for Epoxa Voice Agent with dependency injection."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from epoxa_agent.state import AgentState
from epoxa_agent.handoff import update_local_handoff_cache
from epoxa_core.settings import get_settings
from epoxa_core.services.appointment_service import AppointmentService
from epoxa_core.services.customer_service import CustomerService
from epoxa_core.services.ticket_service import TicketService
from epoxa_core.services.kb_service import KBService
from epoxa_core.exceptions import SlotUnavailableError, BusinessHoursViolationError, PastAppointmentError

logger = structlog.get_logger("epoxa_agent.nodes")

# Dependency Container
class AgentContainer:
    """Dependency container for injecting services into LangGraph nodes."""

    def __init__(
        self,
        appointment_service: Optional[AppointmentService] = None,
        customer_service: Optional[CustomerService] = None,
        ticket_service: Optional[TicketService] = None,
        kb_service: Optional[KBService] = None,
        llm: Optional[ChatOpenAI] = None,
        fast_llm: Optional[ChatOpenAI] = None,
        org_id: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.appointment_service = appointment_service or AppointmentService()
        self.customer_service = customer_service or CustomerService()
        self.ticket_service = ticket_service or TicketService()
        self.kb_service = kb_service or KBService()
        self.org_id = org_id or settings.DEFAULT_ORG_ID

        api_key = settings.GROQ_API_KEY.get_secret_value() if settings.GROQ_API_KEY else "mock-key"
        self.llm = llm or ChatOpenAI(
            model=settings.LLM_MODEL,
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            temperature=0.3,
            max_tokens=250,
            request_timeout=15.0,
        )
        self.fast_llm = fast_llm or ChatOpenAI(
            model=settings.LLM_MODEL,
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            temperature=0.0,
            max_tokens=30,
            request_timeout=8.0,
        )

# Global or context-scoped container instance
_default_container: Optional[AgentContainer] = None

def get_agent_container() -> AgentContainer:
    global _default_container
    if _default_container is None:
        _default_container = AgentContainer()
    return _default_container

def set_agent_container(container: AgentContainer) -> None:
    global _default_container
    _default_container = container


# =============================================================================
# SPOKEN TEXT & REGEX UTILITIES
# =============================================================================

ESCALATION_REGEX = re.compile(
    r"\b(speak\s+to\s+a?\s*human|talk\s+to\s+a?\s*human|transfer\s+me|speak\s+to\s+a?\s*(representative|agent|supervisor|manager)|handover|hand\s+me\s+over|connect\s+me\s+to\s+a?\s*human|i\s+want\s+a?\s*(human|representative|agent|supervisor|manager))\b",
    re.IGNORECASE,
)

def is_escalation_intent(text: str) -> bool:
    """Strict word-boundary regex check for human transfer."""
    if not text:
        return False
    return bool(ESCALATION_REGEX.search(text))

def normalize_spoken_digits(spoken: str) -> str:
    """Normalize spoken phrases like 'double nine', 'triple zero', 'oh' for zero."""
    text = spoken.lower()
    text = re.sub(r"\boh\b", "zero", text)
    word_to_digit = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"
    }
    for word, digit in word_to_digit.items():
        text = re.sub(rf"\bdouble\s+{word}\b", f"{digit}{digit}", text)
        text = re.sub(rf"\btriple\s+{word}\b", f"{digit}{digit}{digit}", text)
        text = re.sub(rf"\b{word}\b", digit, text)
    digits = re.sub(r"\D", "", text)
    return digits

def extract_phone_number(text: str, container: Optional[AgentContainer] = None) -> Optional[str]:
    """Extract and validate 10-digit phone number, returning clean digits."""
    c = container or get_agent_container()
    cleaned = normalize_spoken_digits(text)
    if len(cleaned) == 10:
        return cleaned
    if len(cleaned) > 10:
        return cleaned[-10:]

    # Fallback to fast LLM if spoken format was complex
    try:
        prompt = (
            f"Extract the 10-digit phone number from this text: '{text}'. "
            "Respond with only the 10 digits with no spaces or symbols. "
            "If no phone number exists, reply 'None'."
        )
        res = c.fast_llm.invoke(prompt)
        digits = re.sub(r"\D", "", str(res.content).strip())
        if len(digits) == 10:
            return digits
    except Exception as e:
        logger.warning("phone_extraction_llm_failed", error=str(e))

    return None

def extract_appointment_details(text: str, container: Optional[AgentContainer] = None) -> Dict[str, Optional[str]]:
    """Extract requested date and time string from utterance."""
    c = container or get_agent_container()
    try:
        prompt = (
            "Extract the desired appointment date and time from this customer speech: "
            f"'{text}'.\n"
            "Respond ONLY with a raw JSON object with keys 'date' and 'time'. Set to null if not specified.\n"
            'Example: {"date": "tomorrow", "time": "2 PM"}'
        )
        res = c.fast_llm.invoke(prompt)
        content = str(res.content).replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        return {"date": data.get("date"), "time": data.get("time")}
    except Exception as e:
        logger.warning("appointment_extraction_failed", error=str(e))
        return {"date": None, "time": None}

def classify_customer_type(user_message: str, container: Optional[AgentContainer] = None) -> str:
    """Classify if customer is 'existing' or 'new'."""
    text = (user_message or "").lower()
    if any(w in text for w in ["existing", "already", "have account", "yes I am", "registered"]):
        return "existing"
    if any(w in text for w in ["new", "register", "first time", "sign up", "never called"]):
        return "new"
    c = container or get_agent_container()
    try:
        prompt = (
            "Classify caller response into one word: 'existing' (has account/returning), "
            "'new' (first time/wants to register), or 'unknown':\n"
            f"Utterance: '{user_message}'\n"
            "Response (existing/new/unknown):"
        )
        res = c.fast_llm.invoke(prompt)
        ans = str(res.content).strip().lower()
        if "existing" in ans:
            return "existing"
        if "new" in ans:
            return "new"
    except Exception:
        pass
    return "unknown"

def classify_intent(user_message: str, container: Optional[AgentContainer] = None) -> str:
    """Classify user intent: 'escalate', 'appointment', 'complaint', 'faq', 'chat'."""
    text_clean = (user_message or "").strip()
    text_lower = text_clean.lower()

    if is_escalation_intent(text_lower):
        return "escalate"
    if re.search(r"\b(appointment|book|schedule|reschedule|slot|booking)\b", text_lower):
        return "appointment"
    if re.search(r"\b(complaint|grievance|problem|issue|broken|refund|terrible|not working|dispute)\b", text_lower):
        return "complaint"
    if re.search(r"\b(hours|timing|location|address|where are you|services|pricing|cost)\b", text_lower):
        return "faq"

    c = container or get_agent_container()
    try:
        prompt = (
            "Classify the customer request into one word: appointment, complaint, faq, escalate, or chat.\n"
            f"Utterance: '{text_clean}'\n"
            "Response:"
        )
        res = c.fast_llm.invoke(prompt)
        intent = str(res.content).strip().lower()
        for valid in ["appointment", "complaint", "faq", "escalate", "chat"]:
            if valid in intent:
                return valid
    except Exception as e:
        logger.warning("intent_classification_fallback", error=str(e))
    return "chat"


# =============================================================================
# CONVERSATION NODES
# =============================================================================

async def greeting_node(state: AgentState) -> dict:
    """First turn greeting."""
    greeting = "Hello! Welcome to Voice AI Agent. How can I help you today?"
    return {
        "messages": [AIMessage(content=greeting)],
        "current_flow": "greeting",
    }

async def verify_customer_node(state: AgentState, config: Optional[RunnableConfig] = None) -> dict:
    """Customer lookup via CustomerService with E.164 normalization."""
    container = get_agent_container()
    messages = state.get("messages", [])

    if state.get("verification_attempts") is None:
        return {
            "messages": [AIMessage(content="I'd be glad to help with that. First, are you an existing customer or a new customer?")],
            "current_flow": "verify",
            "verification_attempts": 0,
        }

    if not messages:
        return {"messages": [AIMessage(content="Could you please tell me your phone number?")]}

    last_user_message = str(messages[-1].content)
    phone = extract_phone_number(last_user_message, container)

    if not phone:
        attempts = state.get("verification_attempts", 0) + 1
        if attempts >= 3:
            session_id = config.get("configurable", {}).get("thread_id") if config else None
            if session_id:
                update_local_handoff_cache(session_id, "human_pending")
            return {
                "messages": [AIMessage(content="I'm having trouble verifying your account. Let me transfer you to a human agent who can help.")],
                "current_flow": "escalation",
                "verification_attempts": attempts,
            }
        return {
            "messages": [AIMessage(content="I couldn't catch that. Could you please say your 10-digit phone number clearly?")],
            "verification_attempts": attempts,
            "current_flow": "verify",
        }

    # Verify against database via CustomerService
    try:
        customer = await container.customer_service.get_by_phone(container.org_id, phone)
        if customer:
            # Privacy guard: confirm first name only, do not read full records
            first_name = customer.name.split()[0] if customer.name else "there"
            success_msg = f"Thank you, {first_name}. I have verified your account. Let's proceed with your request."
            next_flow = state.get("target_flow") or "chat"
            return {
                "messages": [AIMessage(content=success_msg)],
                "customer_verified": True,
                "customer_info": {"id": str(customer.id), "name": customer.name, "phone": customer.phone_e164},
                "current_flow": next_flow,
            }
        else:
            attempts = state.get("verification_attempts", 0) + 1
            if attempts >= 3:
                session_id = config.get("configurable", {}).get("thread_id") if config else None
                if session_id:
                    update_local_handoff_cache(session_id, "human_pending")
                return {
                    "messages": [AIMessage(content="I could not find an account with that number. Let me transfer you to a live support representative.")],
                    "current_flow": "escalation",
                    "verification_attempts": attempts,
                }
            return {
                "messages": [AIMessage(content="I'm sorry, I couldn't find an account with that number. Would you like to try again, or register as a new customer?")],
                "verification_attempts": attempts,
                "current_flow": "verify",
            }
    except Exception as e:
        logger.error("verification_error", error=str(e))
        return {
            "messages": [AIMessage(content="I'm having trouble connecting to our database right now. Let me connect you with a representative.")],
            "current_flow": "escalation",
        }

async def registration_node(state: AgentState) -> dict:
    """Step-by-step caller registration (Name -> Phone -> Email)."""
    container = get_agent_container()
    messages = state.get("messages", [])
    step = state.get("registration_step")

    if not messages or step is None:
        return {
            "messages": [AIMessage(content="I'd be happy to set up a new account for you. Let's start with your full name. What is your name?")],
            "registration_step": "name",
            "current_flow": "registration",
        }

    last_user_message = str(messages[-1].content).strip()

    if step == "name":
        return {
            "messages": [AIMessage(content=f"Got it, {last_user_message}. What is your 10-digit phone number?")],
            "registration_step": "phone",
            "reg_name": last_user_message,
            "current_flow": "registration",
        }

    elif step == "phone":
        phone_digits = extract_phone_number(last_user_message, container)
        if not phone_digits:
            return {
                "messages": [AIMessage(content="Please provide a valid 10-digit phone number so we can register your account.")],
                "registration_step": "phone",
                "current_flow": "registration",
            }
        return {
            "messages": [AIMessage(content="Thank you. And lastly, what is your email address?")],
            "registration_step": "email",
            "reg_phone": phone_digits,
            "current_flow": "registration",
        }

    elif step == "email":
        reg_name = state.get("reg_name") or "Valued Customer"
        reg_phone = state.get("reg_phone") or ""
        reg_email = last_user_message

        try:
            cust = await container.customer_service.create_customer(
                org_id=container.org_id,
                name=reg_name,
                phone=reg_phone,
                email=reg_email,
            )
            return {
                "messages": [AIMessage(content="Perfect! I've successfully registered your account. Welcome to Voice AI Agent! How can I assist you today?")],
                "current_flow": "chat",
                "registration_step": "done",
                "customer_verified": True,
                "customer_info": {"id": str(cust.id), "name": cust.name, "phone": cust.phone_e164},
            }
        except Exception as e:
            logger.error("registration_failed", error=str(e))
            return {
                "messages": [AIMessage(content="I had trouble saving your profile in our system. Let me connect you with a representative to get you set up.")],
                "current_flow": "escalation",
            }

    return {"current_flow": "chat"}

async def faq_node(state: AgentState) -> dict:
    """FAQ retrieval node using pgvector with LLM synthesis."""
    container = get_agent_container()
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="How can I help you today?")], "current_flow": "chat"}

    user_query = str(messages[-1].content)
    try:
        chunks = await container.kb_service.search_faq(container.org_id, user_query, limit=1)
        context = chunks[0]["content"] if chunks else "Voice AI Agent is an enterprise voice AI support platform operating Mon-Sat 9 AM to 6 PM IST."

        prompt = (
            "You are a friendly customer support assistant for Voice AI Agent. "
            "Answer the customer's question using ONLY the provided context. "
            "Keep your answer concise (1-2 sentences), friendly, and conversational since this is a voice call. "
            "Never use bullet points, asterisks, or markdown symbols.\n\n"
            f"Context: {context}\n"
            f"Customer Question: {user_query}\n"
            "Response:"
        )
        res = container.llm.invoke(prompt)
        answer = str(res.content).strip()
    except Exception as e:
        logger.error("faq_search_error", error=str(e))
        answer = "Voice AI Agent is open Monday through Saturday from 9 AM to 6 PM. How else may I assist you?"

    return {"messages": [AIMessage(content=answer)], "current_flow": "chat"}

async def appointment_node(state: AgentState, config: Optional[RunnableConfig] = None) -> dict:
    """
    Appointment booking node with true PostgreSQL persistence.
    Validates business hours, prevents slot collisions, and generates unambiguous confirmation code.
    """
    container = get_agent_container()
    messages = state.get("messages", [])

    if state.get("current_flow") != "booking":
        first_name = (state.get("customer_info", {}).get("name") or "").split()[0]
        greeting = f"I can certainly help you book an appointment, {first_name}. What date and time would you like to schedule?" if first_name else "I can help you book an appointment. What date and time would you like to schedule?"
        return {
            "messages": [AIMessage(content=greeting)],
            "current_flow": "booking",
            "appointment_details": {"date": None, "time": None},
        }

    if not messages:
        return {"messages": [AIMessage(content="What date and time works best for you?")]}

    last_user_message = str(messages[-1].content)
    extracted = extract_appointment_details(last_user_message, container)
    appt_details = dict(state.get("appointment_details") or {"date": None, "time": None})

    if extracted.get("date"):
        appt_details["date"] = extracted["date"]
    if extracted.get("time"):
        appt_details["time"] = extracted["time"]

    if not appt_details.get("date") and not appt_details.get("time"):
        return {
            "messages": [AIMessage(content="Could you please tell me what day and what time you'd like your appointment?")],
            "appointment_details": appt_details,
            "current_flow": "booking",
        }
    elif not appt_details.get("date"):
        return {
            "messages": [AIMessage(content=f"I have the time as {appt_details.get('time')}. What day would you like that on?")],
            "appointment_details": appt_details,
            "current_flow": "booking",
        }
    elif not appt_details.get("time"):
        return {
            "messages": [AIMessage(content=f"I have the day as {appt_details.get('date')}. What time works best for you?")],
            "appointment_details": appt_details,
            "current_flow": "booking",
        }

    # Ask for confirmation before booking
    if not appt_details.get("pending_confirmation"):
        appt_details["pending_confirmation"] = True
        confirm_msg = (
            f"Just to confirm, you'd like to schedule your appointment for "
            f"{appt_details.get('date')} at {appt_details.get('time')}. "
            "Should I go ahead and book that?"
        )
        return {
            "messages": [AIMessage(content=confirm_msg)],
            "appointment_details": appt_details,
            "current_flow": "booking",
        }

    # Handle confirmation answer
    user_response = last_user_message.lower().strip()
    affirmative = any(w in user_response for w in ["yes", "yeah", "sure", "correct", "confirm", "okay", "ok", "go ahead", "book it"])
    negative = any(w in user_response for w in ["no", "nope", "wrong", "change", "different", "cancel"])

    if negative:
        return {
            "messages": [AIMessage(content="No problem! What date and time would you prefer instead?")],
            "appointment_details": {"date": None, "time": None},
            "current_flow": "booking",
        }

    if not affirmative:
        return {
            "messages": [AIMessage(content=f"I have your appointment for {appt_details.get('date')} at {appt_details.get('time')}. Shall I confirm this booking?")],
            "appointment_details": appt_details,
            "current_flow": "booking",
        }

    # Customer confirmed — resolve and book with true persistence!
    customer_id = state.get("customer_info", {}).get("id")
    session_id = config.get("configurable", {}).get("thread_id") if config else None
    date_str = str(appt_details.get("date"))
    time_str = str(appt_details.get("time"))

    try:
        scheduled_at = await container.appointment_service.resolve_natural_language_slot(
            org_id=container.org_id,
            date_str=date_str,
            time_str=time_str,
        )
        appt = await container.appointment_service.book_appointment(
            org_id=container.org_id,
            customer_id=customer_id,
            session_id=session_id,
            scheduled_at=scheduled_at,
            notes=f"Booked via Voice AI Agent ({date_str} at {time_str})",
        )
        code = appt.confirmation_code
        confirmation_msg = (
            f"Excellent! I have confirmed your appointment. "
            f"Your booking confirmation code is {code}. Is there anything else I can help you with today?"
        )
        return {
            "messages": [AIMessage(content=confirmation_msg)],
            "appointment_details": {"booked": True, "confirmation_code": code},
            "current_flow": "chat",
            "target_flow": None,
        }
    except SlotUnavailableError:
        return {
            "messages": [AIMessage(content="I'm sorry, that specific time slot is already booked. Could you suggest another time or day?")],
            "appointment_details": {"date": appt_details.get("date"), "time": None},
            "current_flow": "booking",
        }
    except BusinessHoursViolationError:
        return {
            "messages": [AIMessage(content="We are open Monday through Saturday from 9 AM to 6 PM. Could you choose a time within business hours?")],
            "appointment_details": {"date": appt_details.get("date"), "time": None},
            "current_flow": "booking",
        }
    except PastAppointmentError:
        return {
            "messages": [AIMessage(content="That date appears to be in the past. What future date would you like?")],
            "appointment_details": {"date": None, "time": None},
            "current_flow": "booking",
        }
    except Exception as e:
        logger.error("appointment_booking_failed", error=str(e))
        return {
            "messages": [AIMessage(content="I had trouble finalizing your appointment in our database. Let me transfer you to a human representative.")],
            "current_flow": "escalation",
        }

async def complaint_node(state: AgentState, config: Optional[RunnableConfig] = None) -> dict:
    """Submit customer grievance to TicketService with PostgreSQL persistence."""
    container = get_agent_container()
    messages = state.get("messages", [])

    if state.get("current_flow") != "complaint":
        return {
            "messages": [AIMessage(content="I'm sorry to hear that you're experiencing issues. Could you please describe what the problem is so I can file a complaint?")],
            "current_flow": "complaint",
            "complaint_details": {"description": None, "ticket_created": False},
        }

    if not messages:
        return {"messages": [AIMessage(content="Could you please describe the issue?")]}

    complaint_text = str(messages[-1].content)
    customer_id = state.get("customer_info", {}).get("id")
    session_id = config.get("configurable", {}).get("thread_id") if config else None

    try:
        ticket = await container.ticket_service.create_ticket(
            org_id=container.org_id,
            customer_id=customer_id,
            session_id=session_id,
            category="Complaint",
            priority="normal",
            description=complaint_text[:2000],
        )
        ticket_code = f"TKT-{ticket.number:06d}"
        msg = (
            f"Thank you. I have registered your complaint and created support ticket {ticket_code}. "
            "Our team will review this promptly. Is there anything else I can help you with today?"
        )
        return {
            "messages": [AIMessage(content=msg)],
            "complaint_details": {"description": complaint_text, "ticket_created": True, "ticket_id": ticket_code},
            "current_flow": "chat",
            "target_flow": None,
        }
    except Exception as e:
        logger.error("complaint_submission_failed", error=str(e))
        return {
            "messages": [AIMessage(content="I had an issue saving your ticket. Let me connect you with a supervisor.")],
            "current_flow": "escalation",
        }

async def escalate_node(state: AgentState, config: Optional[RunnableConfig] = None) -> dict:
    """Escalation node: silences AI pipeline and files escalation ticket."""
    container = get_agent_container()
    session_id = config.get("configurable", {}).get("thread_id") if config else None
    customer_id = state.get("customer_info", {}).get("id")

    ticket_code = ""
    try:
        ticket = await container.ticket_service.create_ticket(
            org_id=container.org_id,
            customer_id=customer_id,
            session_id=session_id,
            category="Escalation",
            priority="urgent",
            description="Caller requested human transfer or verification failed.",
        )
        ticket_code = f"TKT-{ticket.number:06d}"
    except Exception as e:
        logger.warning("escalation_ticket_creation_failed", error=str(e))

    if session_id:
        update_local_handoff_cache(session_id, "human_pending")

    ref_str = f" A support ticket {ticket_code} has been opened." if ticket_code else ""
    msg = f"I am transferring you to a human agent now.{ref_str} A representative will join this call shortly. Please hold."
    return {
        "messages": [AIMessage(content=msg)],
        "current_flow": "escalation",
    }

async def general_chat_node(state: AgentState) -> dict:
    """General conversational fallback node."""
    container = get_agent_container()
    raw_msgs = state.get("messages", [])

    prompt_context = (
        "You are an intelligent and friendly voice customer support assistant for Voice AI Agent. "
        "The caller is speaking to you over a live voice phone or web call. "
        "Keep your response concise, natural, and conversational (1 to 2 sentences max). "
        "If the user asks 'Am I audible?' or 'Can you hear me?', warmly confirm you can hear them and ask how you can assist. "
        "Never use markdown formatting, asterisks, bullet points, or emojis."
    )

    clean_messages: List[BaseMessage] = [SystemMessage(content=prompt_context)]
    for m in raw_msgs[-6:]:
        content_str = str(m.content).strip() if hasattr(m, "content") else ""
        if not content_str:
            continue
        if isinstance(m, HumanMessage):
            clean_messages.append(HumanMessage(content=content_str))
        elif isinstance(m, AIMessage):
            clean_messages.append(AIMessage(content=content_str))

    try:
        res = container.llm.invoke(clean_messages)
        reply = str(res.content).strip()
    except Exception as e:
        logger.warning("general_chat_llm_failed_using_deterministic_fallback", error=str(e))
        last_human = ""
        for m in reversed(raw_msgs):
            if isinstance(m, HumanMessage):
                last_human = str(m.content).lower()
                break
        if any(w in last_human for w in ["audible", "hear me", "can you hear"]):
            reply = "Yes, I can hear you loud and clear! How can I help you today?"
        elif any(w in last_human for w in ["hello", "hi", "hey"]):
            reply = "Hello! Welcome to Voice AI Agent. How can I help you today?"
        elif any(w in last_human for w in ["appointment", "book", "schedule"]):
            reply = "I would be happy to help you book an appointment. First, are you an existing or new customer?"
        elif any(w in last_human for w in ["complaint", "issue", "problem"]):
            reply = "I'm sorry to hear that you have an issue. Could you please describe what happened?"
        else:
            reply = "I'm listening. How can I assist you today?"

    return {
        "messages": [AIMessage(content=reply)],
        "current_flow": "chat",
    }
