import os
import re
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig

# Ensure .env is loaded
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"), override=True)

# Flat imports
from state import AgentState
from handoff import set_handoff_active
from chroma_client import query_faq

logger = logging.getLogger("nodes")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def get_groq_llm(max_tokens: Optional[int] = 250, temperature: float = 0.3) -> ChatOpenAI:
    """
    Exposes a ChatOpenAI client pointing to Groq's Llama model.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    return ChatOpenAI(
        model="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=15.0
    )


def get_fast_groq_llm(max_tokens: Optional[int] = 20, temperature: float = 0.0) -> ChatOpenAI:
    """
    Fast extraction & classification LLM client.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    return ChatOpenAI(
        model="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=10.0
    )


def sanitize_messages_for_llm(system_prompt: str, raw_messages: List[Any], max_history: int = 6) -> List[BaseMessage]:
    """
    Constructs a clean, valid message list for Groq/OpenAI APIs:
    - Exactly 1 SystemMessage at index 0
    - Alternating/valid HumanMessage and AIMessage with non-empty string content
    - Filters out any nested lists or invalid message structures
    """
    clean_messages: List[BaseMessage] = [SystemMessage(content=system_prompt.strip())]
    
    # Take last N messages
    slice_msgs = raw_messages[-max_history:] if max_history else raw_messages
    for m in slice_msgs:
        content_str = ""
        if isinstance(m, BaseMessage):
            if isinstance(m, SystemMessage):
                continue  # Skip inner system messages
            content_str = m.content if isinstance(m.content, str) else str(m.content or "")
            if not content_str.strip():
                continue
            if isinstance(m, HumanMessage):
                clean_messages.append(HumanMessage(content=content_str.strip()))
            elif isinstance(m, AIMessage):
                clean_messages.append(AIMessage(content=content_str.strip()))
        elif isinstance(m, dict):
            role = m.get("role", "")
            text = m.get("content") or m.get("text", "")
            content_str = text if isinstance(text, str) else str(text or "")
            if not content_str.strip() or role == "system":
                continue
            if role in ("user", "customer"):
                clean_messages.append(HumanMessage(content=content_str.strip()))
            else:
                clean_messages.append(AIMessage(content=content_str.strip()))

    return clean_messages


# =============================================================================
# HELPER EXTRACTION FUNCTIONS
# =============================================================================

def extract_phone_digits(text: str) -> Optional[str]:
    """
    Uses LLM to extract exactly 10 digits representing a phone number from spoken text.
    Returns the string of 10 digits, or None if not found.
    """
    try:
        prompt = (
            f"You are a telephone number extractor. Extract the 10-digit phone number from this text: '{text}'. "
            "Respond with only the 10 digits, with no spaces, dashes, or punctuation. "
            "If no phone number or digits are present, respond with 'None'."
        )
        groq_llm = get_fast_groq_llm(max_tokens=15)
        response = groq_llm.invoke(prompt)
        digits = response.content.strip()
        
        # Strip out any non-digit chars from LLM response just in case
        digits = re.sub(r"\D", "", digits)
        
        if len(digits) == 10:
            return digits
        return None
    except Exception as e:
        logger.error(f"Error extracting phone number: {str(e)}")
        # Fallback to simple regex extraction of digits
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 10:
            return digits[-10:]
        return None


def extract_appointment_info(text: str) -> Dict[str, Optional[str]]:
    """
    Uses the LLM to extract date and time from spoken text.
    Returns a dictionary with 'date' and 'time' keys.
    """
    try:
        prompt = (
            "You are an appointment detail extractor. Extract the desired date and time from this customer utterance: "
            f"'{text}'.\n"
            "Return a JSON object with keys 'date' and 'time'. If either is not specified in the text, set its value to null. "
            "Respond ONLY with the raw JSON. Do not include any markdown formatting, code blocks, or preamble.\n"
            "Example response:\n"
            '{"date": "Friday", "time": "2 PM"}'
        )
        response = get_fast_groq_llm(max_tokens=50).invoke(prompt)
        content = response.content.strip()
        
        # Clean any markdown code ticks if returned
        content = content.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(content)
        return {
            "date": data.get("date"),
            "time": data.get("time")
        }
    except Exception as e:
        logger.error(f"Error parsing appointment details: {str(e)}")
        return {"date": None, "time": None}


# =============================================================================
# INTENT CLASSIFICATION HELPERS
# =============================================================================

def classify_customer_type(user_message: str) -> str:
    """
    Classifies if the caller is an 'existing' or 'new' customer based on their speech.
    
    Returns:
        'existing', 'new', or 'unknown'
    """
    try:
        prompt = (
            "Analyze the customer's response to the greeting and classify them into exactly one category:\n"
            "- 'existing': Caller is an existing customer, has an account, wants to verify, or has called before.\n"
            "- 'new': Caller is a new customer, wants to register, create a profile, or has never called before.\n"
            "- 'unknown': Caller response is unclear or general chit-chat.\n\n"
            f"Response: '{user_message}'\n\n"
            "Respond ONLY with one of the words: existing, new, or unknown. Do not include any other text."
        )
        response = get_fast_groq_llm(max_tokens=10).invoke(prompt)
        return response.content.strip().lower()
    except Exception as e:
        logger.error(f"Error classifying customer type: {e}")
        return "unknown"


def classify_intent(user_message: str) -> str:
    """
    Performs quick categorization of the user's request using keyword matching + LLM fallback.
    
    Returns one of:
        'appointment' (schedule/book slot)
        'complaint' (lodge grievance)
        'faq' (company info/location check)
        'escalate' (human handover request)
        'chat' (general talk/idle turn)
    """
    text_clean = (user_message or "").strip()
    text_lower = text_clean.lower()
    
    # 1. Fast regex & keyword heuristics (zero latency, 100% reliable)
    if re.search(r'\b(speak\s+to\s+a?\s*human|talk\s+to\s+a?\s*human|transfer|supervisor|human\s+agent|representative|manager|handoff|handover)\b', text_lower):
        return "escalate"
        
    if re.search(r'\b(appointment|book\s+an?\s*appointment|book\s+my\s*appointment|schedule|reschedule|book\s+a?\s*slot|booking)\b', text_lower):
        return "appointment"
        
    if re.search(r'\b(complaint|file\s+a?\s*complaint|grievance|issue|problem|broken|frustrated|refund|terrible|not\s+working|dispute)\b', text_lower):
        return "complaint"
        
    if re.search(r'\b(hours|working\s+hours|opening\s+hours|location|address|where\s+are\s+you|what\s+do\s+you\s+do|services|pricing|cost)\b', text_lower):
        return "faq"

    # 2. LLM-based categorization for ambiguous utterances
    try:
        prompt = (
            "Analyze the following customer utterance and classify their intent into exactly one category:\n"
            "- 'appointment': The user wants to book, schedule, or reschedule an appointment.\n"
            "- 'complaint': The user wants to file a complaint, report a problem, or is expressing frustration.\n"
            "- 'faq': The user has a question about opening hours, locations, address, policies, or services.\n"
            "- 'escalate': The user wants to speak to a human representative or transfer.\n"
            "- 'chat': General smalltalk, greeting (hello/hi), mic check ('am I audible'), thank you, or simple chatter.\n\n"
            f"Utterance: '{text_clean}'\n\n"
            "Respond ONLY with one word: appointment, complaint, faq, escalate, or chat."
        )
        response = get_fast_groq_llm(max_tokens=10).invoke(prompt)
        intent = response.content.strip().lower()
        
        valid_intents = ["appointment", "complaint", "faq", "escalate", "chat"]
        for valid in valid_intents:
            if valid in intent:
                return valid
        return "chat"
    except Exception as e:
        logger.warning(f"LLM intent classification fallback to chat: {e}")
        return "chat"


# =============================================================================
# CONVERSATION STATE MACHINE NODES
# =============================================================================

def greeting_node(state: AgentState) -> dict:
    """
    Executes at the beginning of the call.
    Produces a welcoming welcome statement to set customer expectations.
    """
    greeting_text = "Hello! Welcome to Epoxcel. My name is Epixa. How can I help you today?"
    return {
        "messages": [AIMessage(content=greeting_text)],
        "current_flow": "greeting"
    }


def verify_customer_node(state: AgentState, config: RunnableConfig = None) -> dict:
    """
    Manages customer account verification on-demand.
    Looks up phone numbers against SQLite database.
    If identity fails after 3 attempts, flags escalation human handoff.
    """
    messages = state.get("messages", [])
    
    # 1. Start verification flow, ask new/existing question
    if state.get("verification_attempts") is None:
        prompt_text = "I'd be glad to help with that. First, are you an existing customer or a new customer?"
        return {
            "messages": [AIMessage(content=prompt_text)],
            "current_flow": "verify",
            "verification_attempts": 0
        }
    
    if not messages:
        return {"messages": [AIMessage(content="Could you please tell me your phone number?")]}
        
    last_user_message = messages[-1].content
    
    # Run phone extraction
    phone = extract_phone_digits(last_user_message)
    
    # No phone digits caught
    if not phone:
        attempts = state.get("verification_attempts", 0)
        if attempts == 0:
            return {
                "messages": [AIMessage(content="Great! Could you please tell me your ten-digit phone number so I can look up your account?")],
                "verification_attempts": 1,
                "current_flow": "verify"
            }
        else:
            attempts += 1
            if attempts >= 3:
                session_id = config.get("configurable", {}).get("thread_id") if config else None
                if session_id:
                    set_handoff_active(session_id, True)
                return {
                    "messages": [AIMessage(content="I'm having trouble verifying your account. Let me transfer you to a human agent who can help.")],
                    "current_flow": "escalation",
                    "verification_attempts": attempts
                }
            return {
                "messages": [AIMessage(content="I couldn't catch that. Could you please say your 10-digit phone number clearly?")],
                "verification_attempts": attempts,
                "current_flow": "verify"
            }
        
    # Phone number extracted, verify against DB
    verify_url = f"{BACKEND_URL}/api/customers/verify?phone={phone}"
    
    try:
        response = httpx.get(verify_url, timeout=5.0)
        
        if response.status_code == 200:
            customer_info = response.json().get("customer", {})
            customer_name = customer_info.get("name", "Customer")
            success_msg = f"Thank you. I have verified your account, {customer_name}. Let's proceed with your request."
            next_flow = state.get("target_flow") or "idle"
            
            return {
                "messages": [AIMessage(content=success_msg)],
                "customer_verified": True,
                "customer_info": customer_info,
                "current_flow": next_flow
            }
        else:
            attempts = state.get("verification_attempts", 0) + 1
            if attempts >= 3:
                session_id = config.get("configurable", {}).get("thread_id") if config else None
                if session_id:
                    set_handoff_active(session_id, True)
                return {
                    "messages": [AIMessage(content="I'm sorry, I'm still having trouble verifying your account. Let me transfer you to a live support representative who can assist you further.")],
                    "current_flow": "escalation",
                    "verification_attempts": attempts
                }
            else:
                retry_msg = "I'm sorry, I couldn't find an account associated with that number. Could you please double check and say it again?"
                return {
                    "messages": [AIMessage(content=retry_msg)],
                    "verification_attempts": attempts
                }
                
    except Exception as e:
        logger.error(f"Failed to communicate with verification backend: {str(e)}")
        session_id = config.get("configurable", {}).get("thread_id") if config else None
        if session_id:
            set_handoff_active(session_id, True)
        return {
            "messages": [AIMessage(content="I'm having trouble accessing our verification database right now. Let me connect you with a supervisor.")],
            "current_flow": "escalation"
        }


def registration_node(state: AgentState) -> dict:
    """
    Collects Name -> Phone -> Email step-by-step for a new customer.
    Submits user information to backend database to save their profile.
    """
    messages = state.get("messages", [])
    step = state.get("registration_step")
    
    if not messages:
        return {
            "messages": [AIMessage(content="I'd be happy to set up a new account for you. What is your full name?")],
            "registration_step": "name",
            "current_flow": "registration"
        }
        
    last_user_message = messages[-1].content.strip()
    
    if step is None:
        return {
            "messages": [AIMessage(content="I'd be happy to set up a new account for you. Let's start with your full name. What is your name?")],
            "registration_step": "name",
            "current_flow": "registration"
        }
        
    elif step == "name":
        return {
            "messages": [AIMessage(content=f"Got it, {last_user_message}. What is your ten-digit phone number?")],
            "registration_step": "phone",
            "reg_name": last_user_message,
            "current_flow": "registration"
        }
        
    elif step == "phone":
        phone_digits = "".join(c for c in last_user_message if c.isdigit())
        if len(phone_digits) < 10:
            return {
                "messages": [AIMessage(content="Please provide a valid ten-digit phone number so we can register your account.")],
                "registration_step": "phone",
                "current_flow": "registration"
            }
        return {
            "messages": [AIMessage(content="Thank you. And lastly, what is your email address?")],
            "registration_step": "email",
            "reg_phone": phone_digits,
            "current_flow": "registration"
        }
        
    elif step == "email":
        reg_name = state.get("reg_name")
        reg_phone = state.get("reg_phone")
        reg_email = last_user_message
        
        try:
            response = httpx.post(
                f"{BACKEND_URL}/api/customers",
                json={
                    "name": reg_name,
                    "phone": reg_phone,
                    "email": reg_email
                },
                timeout=5.0
            )
            if response.status_code == 200:
                customer_info = response.json()
                success_msg = f"Perfect! I've successfully registered you as a new customer. Welcome to Epoxcel! How can I assist you today?"
                return {
                    "messages": [AIMessage(content=success_msg)],
                    "current_flow": "idle",
                    "registration_step": "done",
                    "customer_verified": True,
                    "customer_info": customer_info
                }
            else:
                logger.error(f"[Registration] Backend error: {response.text}")
                return {
                    "messages": [AIMessage(content="I had trouble saving your profile in our system. Let me connect you with a representative to get you set up.")],
                    "current_flow": "escalation"
                }
        except Exception as e:
            logger.error(f"[Registration] Failed to connect: {e}")
            return {
                "messages": [AIMessage(content="I'm having trouble connecting to our registration database right now. Let me connect you with a representative.")],
                "current_flow": "escalation"
            }
            
    return {"current_flow": "idle"}


def faq_node(state: AgentState) -> dict:
    """
    RAG (Retrieval-Augmented Generation) node.
    Performs vector semantic search against local ChromaDB database
    and formats responses using the LLM with strict context constraints.
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            "messages": [AIMessage(content="How can I help you today?")],
            "current_flow": "idle"
        }
        
    user_query = messages[-1].content
    logger.info(f"Querying FAQ database for: {user_query}")
    
    documents, metadatas = query_faq(user_query, n_results=1)
    context = documents[0] if documents else "No FAQ document context found."
    if documents:
        logger.info(f"ChromaDB Match: {metadatas[0]['source']}")
        
    prompt = (
        "You are a friendly and polite customer support agent. "
        "Answer the customer's question using ONLY the provided context. "
        "Keep your answer concise, friendly, and conversational since this is a voice call. "
        "Do not use bullet points or lists in your spoken response. Speak in natural, complete sentences.\n\n"
        f"Context:\n{context}\n\n"
        f"Customer Question:\n{user_query}\n\n"
        "Agent Response:"
    )
    try:
        response = get_groq_llm().invoke(prompt)
        answer = response.content.strip()
    except Exception as e:
        logger.error(f"Error calling LLM for FAQ: {str(e)}")
        answer = "I'm sorry, I'm having trouble answering that question right now. Is there anything else I can assist you with?"
        
    return {
        "messages": [AIMessage(content=answer)],
        "current_flow": "idle"
    }


def appointment_node(state: AgentState) -> dict:
    """
    Gathers date and time preferences from customer conversationally.
    Performs mock scheduling and registers appointment with confirmation code.
    """
    messages = state.get("messages", [])
    
    if state.get("current_flow") != "booking":
        customer_name = state.get("customer_info", {}).get("name", "")
        greeting = f"I can certainly help you book an appointment, {customer_name}. What date and time would you like to schedule?" if customer_name else "I can help you book an appointment. What date and time would you like to schedule?"
        return {
            "messages": [AIMessage(content=greeting)],
            "current_flow": "booking",
            "appointment_details": {"date": None, "time": None}
        }
        
    if not messages:
        return {"messages": [AIMessage(content="What date and time works for you?")]}
        
    last_user_message = messages[-1].content
    
    # Extract details using local helper function
    extracted = extract_appointment_info(last_user_message)
    appt_details = dict(state.get("appointment_details") or {"date": None, "time": None})
    
    if extracted.get("date"):
        appt_details["date"] = extracted["date"]
    if extracted.get("time"):
        appt_details["time"] = extracted["time"]
        
    if not appt_details.get("date") and not appt_details.get("time"):
        return {
            "messages": [AIMessage(content="Could you please tell me what day and what time you'd like your appointment?")],
            "appointment_details": appt_details
        }
    elif not appt_details.get("date"):
        return {
            "messages": [AIMessage(content=f"I have the time as {appt_details.get('time')}. What day would you like that on?")],
            "appointment_details": appt_details
        }
    elif not appt_details.get("time"):
        return {
            "messages": [AIMessage(content=f"I have the day as {appt_details.get('date')}. What time works best for you?")],
            "appointment_details": appt_details
        }
        
    # Both details collected — check if we need confirmation before booking
    if not appt_details.get("pending_confirmation"):
        # First time both are present: echo back and ask for confirmation
        appt_details["pending_confirmation"] = True
        confirm_msg = (
            f"Just to confirm, you'd like to schedule your appointment for "
            f"{appt_details.get('date')} at {appt_details.get('time')}. "
            f"Is that correct?"
        )
        return {
            "messages": [AIMessage(content=confirm_msg)],
            "appointment_details": appt_details,
            "current_flow": "booking"
        }
    
    # Pending confirmation — check the customer's response
    user_response = last_user_message.lower().strip()
    affirmative_words = ["yes", "yeah", "yep", "correct", "right", "sure", "confirm", "okay", "ok", "that's right", "go ahead", "book it", "sounds good"]
    negative_words = ["no", "nope", "wrong", "change", "different", "not right", "incorrect"]
    
    is_affirmative = any(word in user_response for word in affirmative_words)
    is_negative = any(word in user_response for word in negative_words)
    
    if is_negative:
        # Customer wants to change — reset and ask again
        return {
            "messages": [AIMessage(content="No problem! What date and time would you prefer instead?")],
            "appointment_details": {"date": None, "time": None},
            "current_flow": "booking"
        }
    
    if not is_affirmative:
        # Unclear response — ask again
        return {
            "messages": [AIMessage(content=f"I have your appointment for {appt_details.get('date')} at {appt_details.get('time')}. Should I go ahead and book that?")],
            "appointment_details": appt_details,
            "current_flow": "booking"
        }
    
    # Confirmed! Book the appointment
    import random
    confirmation_code = f"APT-{random.randint(1000, 9999)}"
    appt_details["confirmation_code"] = confirmation_code
    appt_details["booked"] = True
    appt_details["pending_confirmation"] = False
    
    confirmation_msg = (
        f"Excellent! I have scheduled your appointment for {appt_details.get('date')} at {appt_details.get('time')}. "
        f"Your booking confirmation code is {confirmation_code}. Is there anything else I can help you with today?"
    )
    
    return {
        "messages": [AIMessage(content=confirmation_msg)],
        "appointment_details": appt_details,
        "current_flow": "idle",
        "target_flow": None
    }


def complaint_node(state: AgentState) -> dict:
    """
    Submits customer grievances to backend API.
    Fails over to human escalation on backend communication errors.
    """
    messages = state.get("messages", [])
    
    if state.get("current_flow") != "complaint":
        return {
            "messages": [AIMessage(content="I'm sorry to hear that you're experiencing issues. Could you please describe what the problem is so I can file a complaint?")],
            "current_flow": "complaint",
            "complaint_details": {"description": None, "ticket_created": False}
        }
        
    if not messages:
        return {"messages": [AIMessage(content="Could you please describe the issue?")]}
        
    complaint_text = messages[-1].content
    logger.info(f"Registering customer complaint: {complaint_text}")
    
    customer_id = state.get("customer_info", {}).get("id") if state.get("customer_verified") else None
    
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/tickets",
            json={
                "customer_id": customer_id,
                "category": "Complaint",
                "description": complaint_text
            },
            timeout=5.0
        )
        if response.status_code == 200:
            ticket_id = response.json().get("ticket_id")
            success_msg = (
                f"Thank you. I have registered your complaint and created a support ticket. "
                f"Your ticket ID is {ticket_id}. Our team will review this and contact you. "
                "Is there anything else I can help you with today?"
            )
            return {
                "messages": [AIMessage(content=success_msg)],
                "complaint_details": {
                    "description": complaint_text,
                    "ticket_created": True,
                    "ticket_id": ticket_id
                },
                "current_flow": "idle",
                "target_flow": None
            }
        else:
            return {
                "messages": [AIMessage(content="I'm sorry, I encountered an issue recording your complaint in our system. Let me transfer you to a human agent.")],
                "current_flow": "escalation"
            }
    except Exception as e:
        logger.error(f"Failed to communicate with ticket backend: {str(e)}")
        return {
            "messages": [AIMessage(content="I'm having trouble connecting to our ticketing service right now. Let me connect you with a supervisor.")],
            "current_flow": "escalation"
        }


def escalate_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Node that processes human representative call transfers.
    Submits ticket info and silences AI pipeline.
    """
    session_id = config.get("configurable", {}).get("thread_id")
    customer_id = state.get("customer_info", {}).get("id") if state.get("customer_verified") else None
    
    logger.info(f"[Escalation] Escalating call session: {session_id}")
    
    ticket_id = None
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/tickets",
            json={
                "customer_id": customer_id,
                "category": "Escalation",
                "description": "Customer requested human agent or failed identity verification."
            },
            timeout=5.0
        )
        if response.status_code == 200:
            ticket_id = response.json().get("ticket_id")
            logger.info(f"[Escalation] Ticket #{ticket_id} created successfully.")
    except Exception as e:
        logger.error(f"[Escalation] Failed to create support ticket: {e}")
        
    ticket_str = f" support ticket {ticket_id} has been created and" if ticket_id else ""
    msg = f"I am transferring you to a human agent now. A{ticket_str} representative will join this call shortly. Please hold."
    
    if session_id:
        set_handoff_active(session_id, True)
        logger.info(f"[Escalation] Call session {session_id[:8]} placed in escalation handoff.")
        
    return {
        "messages": [AIMessage(content=msg)],
        "current_flow": "escalation"
    }


def general_chat_node(state: AgentState) -> dict:
    """
    Default node handling general chat, questions outside database,
    greetings, and closing remarks.
    """
    prompt_context = (
        "You are Epixa, an intelligent and friendly voice customer support assistant for Epoxcel. "
        "The caller is speaking to you over a live voice phone/web call. "
        "Keep your response concise, natural, and conversational (1 to 2 sentences max). "
        "If the user asks 'Am I audible?' or 'Can you hear me?', warmly confirm you can hear them and ask how you can assist them. "
        "Never use markdown bullet points, symbols, or emojis in your speech."
    )
    raw_msgs = state.get("messages", [])
    messages_for_llm = sanitize_messages_for_llm(prompt_context, raw_msgs, max_history=6)
    
    reply = ""
    try:
        response = get_groq_llm(max_tokens=150, temperature=0.3).invoke(messages_for_llm)
        reply = response.content.strip()
        print(f"🤖 [GENERAL CHAT LLM]: {reply}", flush=True)
    except Exception as e:
        logger.error(f"Error in general chat LLM call: {str(e)}")
        # Check last user utterance for smart fallback
        last_human = ""
        for m in reversed(raw_msgs):
            if isinstance(m, HumanMessage):
                last_human = m.content.lower()
                break
            elif isinstance(m, dict) and m.get("role") in ("user", "customer"):
                last_human = str(m.get("content") or m.get("text") or "").lower()
                break

        if any(w in last_human for w in ["audible", "hear me", "can you hear"]):
            reply = "Yes, I can hear you loud and clear! How can I help you today?"
        elif any(w in last_human for w in ["hello", "hi", "hey"]):
            reply = "Hello! I am Epixa. How can I help you today?"
        elif any(w in last_human for w in ["appointment", "book", "schedule"]):
            reply = "I would be happy to help you book an appointment. First, are you an existing or new customer?"
        elif any(w in last_human for w in ["complaint", "issue", "problem"]):
            reply = "I'm sorry to hear that you are having an issue. Could you please describe the problem so I can record it?"
        else:
            reply = "I'm listening. How can I assist you today?"
            
        print(f"🤖 [GENERAL CHAT FALLBACK]: {reply}", flush=True)
        
    return {
        "messages": [AIMessage(content=reply)],
        "current_flow": "idle"
    }
