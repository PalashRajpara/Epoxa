# 04 — LangChain Deep Dive: The LLM Plumbing Layer

> LangChain is used **within** LangGraph in this project. You'll see it again in
> [05_LANGGRAPH_DEEPDIVE.md](./05_LANGGRAPH_DEEPDIVE.md). This file focuses on the
> LangChain pieces that appear directly in the code.

---

## What Is LangChain?

LangChain is a Python framework for **orchestrating LLM calls**. Instead of writing raw
HTTP requests to OpenAI (or Groq), LangChain gives you a consistent API for:
- Sending prompts to any LLM with a unified interface
- Chaining multiple LLM calls together
- Structuring prompts with templates
- Defining what "messages" look like (system, human, AI)

**Why LangChain instead of just `requests` or `openai`?**
- You can swap LLM providers without changing logic (Groq today, Anthropic tomorrow)
- The message format is standardized and plays nicely with LangGraph
- LangGraph is built on top of LangChain — they share the same message types

---

## Core Concept: Message Types

LangChain defines three types of messages that map to the familiar "roles" in an LLM API:

| LangChain Type | Role | Used When |
|----------------|------|-----------|
| `SystemMessage` | `system` | Instructions for the AI ("You are a helpful agent...") |
| `HumanMessage` | `user` | What the customer said |
| `AIMessage` | `assistant` | What the AI said (past turns OR new responses) |
| `BaseMessage` | base class | Parent of all message types (used in type hints) |

### In THIS project — `agent/state.py` and `agent/nodes.py`

```python
# agent/state.py
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # messages is a list of BaseMessage objects — can be HumanMessage, AIMessage, etc.
    # BaseMessage is the parent class so this works for any message type.
    messages: Annotated[List[BaseMessage], add_messages]
```

```python
# agent/nodes.py — nodes return new AIMessage objects to add to the conversation
from langchain_core.messages import AIMessage, SystemMessage

def greeting_node(state: AgentState) -> dict:
    # We return a dict with a list of new messages to add.
    # LangGraph's 'add_messages' annotation APPENDS these to the existing history.
    # If we just returned the whole list, it would REPLACE the history.
    return {
        "messages": [AIMessage(content="Hello! Welcome to Epoxcel.")],
        "current_flow": "greeting"
    }
```

---

## Core Concept: ChatOpenAI (LangChain's LLM Client)

`ChatOpenAI` is LangChain's wrapper for OpenAI-compatible APIs. It's called "ChatOpenAI"
because it uses the "chat completions" format (messages with roles, as opposed to plain text completion).

The key insight here: **Groq implements the same API format as OpenAI.**
So by pointing `base_url` at Groq's server, `ChatOpenAI` talks to Groq instead of OpenAI.
This is sometimes called an "OpenAI-compatible API."

### In THIS project — `agent/nodes.py`

```python
# agent/nodes.py

from langchain_openai import ChatOpenAI

def get_groq_llm() -> ChatOpenAI:
    # This creates a LangChain LLM client that talks to Groq.
    # model="llama-3.1-8b-instant" = the specific Groq-hosted Llama model.
    # "instant" = optimized for speed (critical for real-time voice responses).
    # base_url = Groq's API endpoint, which accepts OpenAI-format requests.
    # api_key = the Groq API key from our .env file.
    return ChatOpenAI(
        model="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY")
    )


def get_fast_groq_llm(max_tokens: Optional[int] = None, temperature: float = 0.0) -> ChatOpenAI:
    # This variant is used for classification and extraction tasks.
    # temperature=0.0 means "deterministic" output — no randomness.
    #   (For classification, you want the same answer every time, not creative variation.)
    # max_tokens limits how long the response can be.
    #   For classify_intent, we just need one word ("appointment", "faq", etc.) — capping at
    #   10 tokens prevents the LLM from rambling, and saves API cost + latency.
    # request_timeout=5.0 means: give up after 5 seconds instead of waiting indefinitely.
    return ChatOpenAI(
        model="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,    # 0.0 = greedy decoding (always pick highest probability token)
        max_tokens=max_tokens,      # None = unlimited; 10 for single-word classification
        request_timeout=5.0         # Fail fast so calls don't hang
    )
```

---

## Core Concept: `.invoke()` — How You Call an LLM

Once you have a `ChatOpenAI` object, you call it with `.invoke()`. You can pass either:
- A **string** (simple prompt)
- A **list of message objects** (conversation with history)

```python
groq_llm = get_groq_llm()

# Option 1: Simple string prompt
response = groq_llm.invoke("What is the capital of France?")
print(response.content)   # → "Paris"

# Option 2: List of messages (for conversations with history)
from langchain_core.messages import SystemMessage, HumanMessage
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is the capital of France?")
]
response = groq_llm.invoke(messages)
print(response.content)   # → "The capital of France is Paris."
```

The return value is an `AIMessage` object. The actual text is in `.content`.

### In THIS project — `agent/nodes.py` (classify_intent)

```python
# agent/nodes.py — classify_intent() uses the LLM to categorize user input

def classify_intent(user_message: str) -> str:
    try:
        # Build a prompt that asks the LLM to classify the intent.
        # The prompt is carefully crafted: it lists exact category names and
        # tells the LLM to respond with ONLY one word — no explanation needed.
        prompt = (
            "Analyze the following customer utterance and classify their intent "
            "into exactly one of these categories:\n"
            "- 'appointment': The user wants to book, schedule, or reschedule.\n"
            "- 'complaint': The user wants to file a complaint or report a problem.\n"
            "- 'faq': The user has a general question (hours, location, refund policy).\n"
            "- 'escalate': The user wants to speak to a human agent.\n"
            "- 'chat': General smalltalk or greetings.\n\n"
            f"Utterance: '{user_message}'\n\n"
            "Respond ONLY with one of the category names. No extra text."
        )

        # get_fast_groq_llm(max_tokens=10) limits the response to 10 tokens.
        # For a single word like "appointment", 10 tokens is more than enough.
        # This saves ~100ms of LLM processing time vs. unlimited tokens.
        response = get_fast_groq_llm(max_tokens=10).invoke(prompt)

        # response.content might be "appointment" or "  appointment\n" — strip whitespace
        intent = response.content.strip().lower()

        # The LLM might sometimes return "appointment." or "The intent is: faq"
        # We validate by checking if any of our valid intents appear anywhere in the response
        valid_intents = ["appointment", "complaint", "faq", "escalate", "chat"]
        for valid in valid_intents:
            if valid in intent:
                return valid
        return "chat"  # Default to chat if we can't parse the response

    except Exception as e:
        logger.error(f"Error classifying intent: {str(e)}")
        return "chat"   # Safe fallback: general chat handler can handle anything
```

---

## Core Concept: Prompts — The Art of Telling the LLM What to Do

A **prompt** is the text you send to the LLM to get the response you want. Writing good prompts
is arguably the most important skill in AI engineering. In this project, prompts follow a pattern:

```
1. Set the role/persona: "You are a friendly customer support agent..."
2. State the constraint: "Answer ONLY using the provided context..."
3. Format the context: "Context:\n{retrieved_text}"
4. State the task: "Customer Question:\n{user_question}"
5. Signal where to start: "Agent Response:"
```

### In THIS project — `agent/nodes.py` (faq_node)

```python
# agent/nodes.py — faq_node builds a RAG prompt with retrieved context

def faq_node(state: AgentState) -> dict:
    user_query = state.get("messages", [])[-1].content

    # STEP 1: Retrieve the most relevant FAQ document from ChromaDB
    # (see 06_RAG_AND_EMBEDDINGS_DEEPDIVE.md for how this works)
    documents, metadatas = query_faq(user_query, n_results=1)
    context = documents[0] if documents else "No FAQ document context found."

    # STEP 2: Build the prompt. This is a RAG (Retrieval-Augmented Generation) prompt.
    # The LLM is constrained to ONLY use the retrieved context — this prevents it from
    # making up answers (hallucinating) about store hours or policies.
    prompt = (
        "You are a friendly and polite customer support agent. "
        # CONSTRAINT: only use provided context (prevents hallucination)
        "Answer the customer's question using ONLY the provided context. "
        # FORMAT: voice-specific instruction (no bullet points — they sound weird when spoken)
        "Keep your answer concise, friendly, and conversational since this is a voice call. "
        "Do not use bullet points or lists. Speak in natural, complete sentences.\n\n"
        # CONTEXT: the actual FAQ text retrieved from ChromaDB
        f"Context:\n{context}\n\n"
        # QUESTION: what the customer asked
        f"Customer Question:\n{user_query}\n\n"
        # SIGNAL: this tells the LLM to start generating the answer immediately
        "Agent Response:"
    )

    try:
        # get_groq_llm() (without max_tokens limit) because the FAQ answer
        # could be several sentences — we don't want to cut it off
        response = get_groq_llm().invoke(prompt)
        answer = response.content.strip()
    except Exception as e:
        logger.error(f"Error calling LLM for FAQ: {str(e)}")
        answer = "I'm sorry, I'm having trouble answering that right now."

    return {
        "messages": [AIMessage(content=answer)],
        "current_flow": "idle"
    }
```

### In THIS project — `agent/nodes.py` (general_chat_node)

```python
# agent/nodes.py — general_chat_node uses a list of messages (conversation format)

def general_chat_node(state: AgentState) -> dict:
    # Build a list of message objects instead of a string prompt.
    # This format passes the conversation HISTORY to the LLM so it can
    # give contextually aware responses (not just answer in a vacuum).
    prompt_context = (
        "You are a polite, helpful customer support voice assistant for Epoxcel. "
        "Keep your responses concise, friendly, and conversational. "
        "Do not use list formatting. Speak in natural complete sentences.\n"
    )

    # Start with the system message (instructions for the AI)
    messages_for_llm = [SystemMessage(content=prompt_context)]

    # Then add the last 5 messages from the conversation.
    # We use [-5:] (last 5) instead of the full history to:
    #   1. Keep the context window small (lower latency + lower cost)
    #   2. Keep the LLM focused on the recent conversation
    for msg in state["messages"][-5:]:
        messages_for_llm.append(msg)   # These are already BaseMessage objects from state

    try:
        response = get_groq_llm().invoke(messages_for_llm)
        reply = response.content.strip()
    except Exception as e:
        logger.error(f"Error in general chat: {str(e)}")
        reply = "I'm here to help. You can ask me to book an appointment, file a complaint, or answer FAQs."

    return {
        "messages": [AIMessage(content=reply)],
        "current_flow": "idle"
    }
```

---

## LangChain in `agent/main.py` (Call Summary)

```python
# agent/main.py — generate_call_summary() uses LangChain directly (not via LangGraph)

async def generate_call_summary(session_id: str) -> str:
    # STEP 1: Fetch the full transcript from Supabase
    transcript_entries = get_full_transcript(session_id)

    # STEP 2: Format as readable conversation text
    conversation_text = "\n".join([
        f"{entry['role'].capitalize()}: {entry['content']}"
        for entry in transcript_entries
    ])

    # STEP 3: Call Groq directly (no LangGraph needed for this one-shot task)
    from langchain_openai import ChatOpenAI
    groq_llm = ChatOpenAI(
        model="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY")
    )

    # Detailed prompt asking for a structured summary
    summary_prompt = (
        "You are a customer support call analyst. "
        "Read the following support call transcript and write a brief 2-3 sentence summary. "
        "Include: (1) what the customer needed help with, (2) what actions were taken, "
        "and (3) the final outcome. Be concise and factual.\n\n"
        f"TRANSCRIPT:\n{conversation_text}\n\n"
        "SUMMARY:"
    )

    # .invoke() with a string sends it as a single "user" message
    response = groq_llm.invoke(summary_prompt)
    summary = response.content.strip()
    return summary
```

---

## Summary: What LangChain Provides in This Project

| Component | Where Used | Purpose |
|-----------|-----------|---------|
| `ChatOpenAI` | `nodes.py`, `main.py` | Client for Groq LLM API |
| `AIMessage` | `nodes.py`, `graph_builder.py`, `main.py` | Represents agent responses |
| `HumanMessage` | `graph_builder.py` | Represents customer speech |
| `SystemMessage` | `graph_builder.py`, `nodes.py` | System instructions for the LLM |
| `BaseMessage` | `state.py` | Type hint for any message type |
| `add_messages` | `state.py` | LangGraph reducer: append-not-replace for messages |
| `RunnableConfig` | `nodes.py` | Carries LangGraph config (thread_id) to nodes |

---

*Next up → [05_LANGGRAPH_DEEPDIVE.md](./05_LANGGRAPH_DEEPDIVE.md)*
