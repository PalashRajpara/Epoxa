# 05 — LangGraph Deep Dive: The Stateful Conversation State Machine

> This is the most architecturally important file in the study guide.
> LangGraph is what makes this agent "smart" — it gives it memory, branching logic,
> and the ability to handle multi-step conversations instead of just answering one question at a time.

---

## Why LangGraph on Top of LangChain?

Imagine a simple approach: customer speaks → LLM answers → done. This is a "stateless" chatbot.

**The problem:** Real support conversations are multi-step:
1. Customer says "I want to book an appointment"
2. Agent says "Are you a new or existing customer?"
3. Customer says "Existing"
4. Agent says "What's your phone number?"
5. Customer says "555-1234-567"
6. Agent verifies it, then switches to asking for booking details

Without state management:
- How does the agent know we're in the middle of verification?
- How does it remember we're trying to book an appointment after verification?
- How does it prevent re-asking for the phone number on every turn?

**LangGraph's answer:** A **state machine** where:
- The entire conversation has a **shared state** (the `AgentState` dict)
- Each turn the state machine decides which **node** (handler) to run
- Nodes READ from state, do their work, and WRITE back to state
- **Edges** define which node can follow which

---

## Core Concepts

### StateGraph

The central object. You add nodes and edges to it, then compile it.

```python
builder = StateGraph(AgentState)  # AgentState is our schema (see state.py)
```

### Nodes

Functions that process one turn of the conversation. Each node:
- Receives the current `AgentState` dict
- Does its work (classifies, calls an API, queries ChromaDB, etc.)
- Returns a **partial dict** with just the fields it wants to update

LangGraph **merges** this partial dict into the full state (it doesn't replace the whole state).

### Edges

Connections between nodes. Two types:

**Regular edge:** Always go from A to B.
```python
builder.add_edge("greeting", END)  # After greeting, always end the turn
```

**Conditional edge:** A function decides which node to go to next.
```python
builder.add_conditional_edges(
    "route_input",    # Starting node
    route_flow_edge,  # Function that returns a string (destination node name)
    {"faq": "faq", "appointment": "appointment", ...}  # Map return values to nodes
)
```

### MemorySaver (Checkpointer)

The piece that makes conversations persistent across multiple turns. Without it, the graph
would forget everything after each turn (each `.invoke()` call would start fresh).

```python
memory = MemorySaver()
compiled_graph = builder.compile(checkpointer=memory)
```

The checkpointer stores state keyed by `thread_id`. In this project, `thread_id = session_id`
(the call's UUID). Every turn for the same call uses the same thread_id, so the memory persists.

### START and END

Special sentinels. `START` is where graph execution begins. `END` signals "this turn is done,
wait for the next user input."

---

## The Graph in This Project — Visually

```
START
  │
  ▼
entry_router (conditional)
  │
  ├── (no user message yet) ──► greeting ──► END
  │                               │
  │                               (next turn starts over at START)
  │
  └── (user message exists) ──► route_input (router_node)
                                      │ (conditional)
                                      │
                      ┌───────────────┼───────────────┐
                      │               │               │
                      ▼               ▼               ▼
                  verify_customer   faq           general_chat
                      │               │               │
                      ▼               ▼               ▼
                  registration   appointment      complaint
                      │               │               │
                      └───────────────┴───────────────┘
                                      │
                                      ▼ (all go to)
                                    escalate
                                      │
                                      ▼
                                     END
```

Each turn: START → (routing) → one node → END. Then the next user utterance starts again at START.

---

## The Actual Graph Code — `agent/graph_builder.py`

### `entry_router` — First Decision on Every Turn

```python
# agent/graph_builder.py

def entry_router(state: AgentState) -> Literal["greeting", "route_input"]:
    """
    The very first function called every time the graph runs.
    It decides: is this the beginning of the call (no user messages yet)?
    Or is the user speaking (we need to route their input)?
    """
    # state.get("messages", []) safely gets the messages list,
    # defaulting to an empty list if there are no messages yet.
    messages = state.get("messages", [])

    # isinstance() checks if an object is of a certain type.
    # messages[-1] = the last message in the history.
    # HumanMessage = a message from the user.
    # If the last message is from the user, we need to process it.
    if messages and isinstance(messages[-1], HumanMessage):
        return "route_input"  # User spoke — go to router_node

    # No user message, or the last message was from the agent (greeting).
    # This means we just started the call — play the greeting.
    return "greeting"
```

### `router_node` — The Intent Router

```python
# agent/graph_builder.py

def router_node(state: AgentState) -> dict:
    """
    The brain of the routing logic. Decides WHICH conversation flow to enter.
    Returns a dict that updates ONLY the flow-related fields in state.
    """
    messages = state.get("messages", [])
    current_flow = state.get("current_flow", "idle")

    # ── PRIORITY 1: Hard-coded escalation keywords ─────────────────────────
    # We check for human-handoff keywords BEFORE calling the LLM classifier.
    # Why? Because calling the LLM adds ~300ms of latency. For a simple keyword
    # check, regex/string matching is instant and good enough.
    if messages:
        user_message = messages[-1].content.lower()
        if any(kw in user_message for kw in
               ["human", "representative", "agent", "supervisor", "manager", "handover", "transfer"]):
            # Customer wants a human — skip classification entirely
            return {"current_flow": "escalation"}

    # ── PRIORITY 2: Continue an active multi-step flow ──────────────────────
    # If we're in the middle of verification, registration, booking, or complaint,
    # we DON'T reclassify — we just continue where we left off.
    # This avoids the LLM classifying "555-123-4567" as "chat" when we know
    # we're expecting a phone number for verification.
    if current_flow == "verify":
        if messages:
            user_message = messages[-1].content.lower()
            # Check if they gave a phone number
            from nodes import extract_phone_digits
            phone = extract_phone_digits(user_message)
            if phone:
                # They gave digits — stay in verify flow, preserve the target
                return {"target_flow": state.get("target_flow"), "current_flow": "verify"}

            # Check if they identified as new or existing customer
            cust_type = classify_customer_type(user_message)
            if cust_type == "new":
                # New customer → switch to registration
                return {"current_flow": "registration", "registration_step": None}
            elif cust_type == "existing":
                # Existing customer → stay in verify (ask for phone number)
                return {"target_flow": state.get("target_flow"), "current_flow": "verify"}

        return {"target_flow": state.get("target_flow"), "current_flow": "verify"}

    elif current_flow == "registration":
        return {"current_flow": "registration"}   # Just continue collecting info
    elif current_flow == "booking":
        return {"current_flow": "booking"}         # Just continue booking
    elif current_flow == "complaint":
        return {"current_flow": "complaint"}       # Just continue complaint

    # ── PRIORITY 3: Classify new intent (call the LLM) ──────────────────────
    # We only reach here when current_flow == "idle" (no active multi-step flow).
    # The LLM classifies the customer's intent.
    intent = "chat"
    if messages:
        user_message = messages[-1].content
        intent = classify_intent(user_message)     # LLM call: ~200-400ms
        logger.info(f"Classified customer intent: {intent}")

        if intent == "escalate":
            return {"current_flow": "escalation"}

    # ── PRIORITY 4: Route based on classified intent ─────────────────────────
    if intent == "appointment":
        if state.get("customer_verified"):
            # Already verified — go straight to booking
            return {"current_flow": "booking"}
        else:
            # Need to verify first. Remember we want to book AFTER verification.
            # target_flow = "booking" tells the verify node what to do after success.
            return {"target_flow": "booking", "current_flow": "verify"}

    elif intent == "complaint":
        if state.get("customer_verified"):
            return {"current_flow": "complaint"}
        else:
            return {"target_flow": "complaint", "current_flow": "verify"}

    elif intent == "faq":
        return {"current_flow": "faq"}

    # Default: chat
    return {"current_flow": "chat"}
```

### `route_flow_edge` — The Routing Function

```python
# agent/graph_builder.py

def route_flow_edge(state: AgentState) -> Literal[
    "verify_customer", "registration", "faq", "appointment", "complaint", "escalate", "general_chat"
]:
    """
    This function is called by LangGraph after router_node runs.
    It reads state.current_flow and returns the NAME of the next node to run.

    Note: router_node WRITES to state (sets current_flow).
          route_flow_edge READS from state (uses current_flow to decide next node).
    These are two separate steps — LangGraph calls router_node, updates state,
    then calls route_flow_edge to find the next destination.
    """
    flow = state.get("current_flow", "chat")

    # Map flow names to node names (they're the same in this project, but
    # keeping the mapping explicit makes the code clearer and easier to change)
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
```

### `build_graph()` — Assembling the Full Graph

```python
# agent/graph_builder.py

def build_graph():
    """
    Creates the StateGraph, adds all nodes and edges, and compiles it.
    Called once at startup — the result (compiled_graph) is reused for every call.
    """
    builder = StateGraph(AgentState)

    # ── ADD NODES ─────────────────────────────────────────────────────────────
    # Each add_node() call registers a node by name.
    # First argument = the name you use when writing edges
    # Second argument = the function to call when this node runs
    builder.add_node("greeting", greeting_node)
    builder.add_node("route_input", router_node)
    builder.add_node("verify_customer", verify_customer_node)
    builder.add_node("registration", registration_node)
    builder.add_node("faq", faq_node)
    builder.add_node("appointment", appointment_node)
    builder.add_node("complaint", complaint_node)
    builder.add_node("general_chat", general_chat_node)
    builder.add_node("escalate", escalate_node)

    # ── ADD EDGES FROM START ───────────────────────────────────────────────────
    # add_conditional_edges from START means: the very first thing LangGraph does
    # on each graph run is call entry_router to decide where to begin.
    builder.add_conditional_edges(
        START,           # Starting point
        entry_router,    # Function to call — returns "greeting" or "route_input"
        {
            "greeting": "greeting",       # If entry_router returns "greeting" → go to greeting node
            "route_input": "route_input"  # If returns "route_input" → go to route_input node
        }
    )

    # ── GREETING → END ────────────────────────────────────────────────────────
    # After greeting, the turn is over. Wait for user to speak.
    builder.add_edge("greeting", END)

    # ── ROUTE_INPUT → (conditional) → processing node ─────────────────────────
    # After router_node updates state.current_flow, route_flow_edge picks the destination.
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

    # ── ALL PROCESSING NODES → END ────────────────────────────────────────────
    # Every processing node ends the turn. The next user utterance will start at START again.
    builder.add_edge("verify_customer", END)
    builder.add_edge("registration", END)
    builder.add_edge("faq", END)
    builder.add_edge("appointment", END)
    builder.add_edge("complaint", END)
    builder.add_edge("general_chat", END)
    builder.add_edge("escalate", END)

    # ── COMPILE ───────────────────────────────────────────────────────────────
    # Compile transforms the builder into an optimized runnable graph.
    # MemorySaver = store state in RAM (for production, could be Redis/Postgres).
    # thread_id is how LangGraph identifies which conversation's state to use.
    memory = MemorySaver()
    compiled_graph = builder.compile(checkpointer=memory)

    return compiled_graph


# This line runs ONCE when graph_builder.py is imported.
# The compiled graph is then shared across all calls.
compiled_graph = build_graph()
```

---

## Tracing a Full Call — Concrete Example

Let's trace what happens when a customer says "I want to book an appointment for Friday at 2pm":

**Turn 1 — Customer speaks for the first time (after greeting)**

1. `agent/main.py`: LiveKit fires `user_speech_committed` with text: "I want to book an appointment for Friday at 2pm"
2. `LangGraphStream._run()` is called. It adds `HumanMessage(content="I want to book...")` to the message list.
3. `graph.ainvoke({"messages": [HumanMessage(...)]}, config={"configurable": {"thread_id": session_id}})` is called.
4. LangGraph loads the saved state for this `thread_id` from `MemorySaver`.
5. **`entry_router`** runs: last message is `HumanMessage` → returns `"route_input"`.
6. **`router_node`** runs:
   - `current_flow` is `"idle"` (no active flow)
   - No escalation keywords
   - Calls `classify_intent("I want to book an appointment...")` → Groq returns `"appointment"`
   - `customer_verified` is `False` (they haven't proven who they are)
   - Returns `{"target_flow": "booking", "current_flow": "verify"}`
7. State is updated: `current_flow="verify"`, `target_flow="booking"`.
8. **`route_flow_edge`** sees `current_flow="verify"` → returns `"verify_customer"`.
9. **`verify_customer_node`** runs:
   - `verification_attempts` is `None` (first time) → prompt: "Are you a new or existing customer?"
   - Returns `{"messages": [AIMessage("Are you a new or existing customer?")], "current_flow": "verify", "verification_attempts": 0}`
10. **END** — this turn is done. The AIMessage is streamed back to TTS.

**Turn 2 — Customer says "existing"**

1. LangGraph loads state: `current_flow="verify"`, `target_flow="booking"`, `verification_attempts=0`.
2. `entry_router` → `"route_input"`.
3. `router_node`: `current_flow="verify"` → stays in verify. Customer said "existing" → `classify_customer_type` returns "existing" → `{"target_flow": "booking", "current_flow": "verify"}`.
4. `verify_customer_node` runs: `verification_attempts=0` → asks "What's your 10-digit phone number?"

**Turn 3 — Customer says "555-1234-5678"**

1. State loaded: same as above, `verification_attempts=1`.
2. `verify_customer_node` runs: `extract_phone_digits("555-1234-5678")` → `"5551234578"`. Calls `GET /api/customers/verify?phone=5551234578` → 200 OK with `{"name": "John Doe"}`. Returns `{"customer_verified": True, "current_flow": "booking"}`.
3. `route_flow_edge` doesn't run (we returned directly from verify_customer_node to END).

**Turn 4 — Agent auto-continues to ask booking details**

Actually, in the current flow, after verification the customer would need to speak again.
The agent would say "I've verified your account, John. Let's proceed with your booking..."
and then the next user utterance would re-route into the `booking` flow.

---

## State Mutation Rules

| Scenario | What to return from a node |
|----------|---------------------------|
| Update one field | `{"current_flow": "booking"}` |
| Add a message | `{"messages": [AIMessage(content="...")]}` — LangGraph APPENDS this, doesn't replace |
| Update multiple fields | `{"messages": [...], "current_flow": "booking", "customer_verified": True}` |
| Don't change anything | `{}` (empty dict) |

**Why does returning `{"messages": [...]}` append instead of replace?**
Because in `state.py`, messages is annotated with `Annotated[List[BaseMessage], add_messages]`.
The `add_messages` annotation tells LangGraph to use a special "reducer" function that appends.
Without this annotation, returning `{"messages": [...]}` would REPLACE the entire history.

---

*Next up → [06_RAG_AND_EMBEDDINGS_DEEPDIVE.md](./06_RAG_AND_EMBEDDINGS_DEEPDIVE.md)*
