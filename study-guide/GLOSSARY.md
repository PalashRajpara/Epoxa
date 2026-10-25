# GLOSSARY — Quick Reference for Every Concept in This Project

> Sorted alphabetically. Each entry gives a 2-3 sentence definition and
> where in the project you'll find it.

---

## A

**`add_messages` (LangGraph)**
A special annotation from `langgraph.graph.message` applied to the `messages` field in `AgentState`. It tells LangGraph to APPEND new messages to the list instead of replacing the entire list when a node returns `{"messages": [...]}`. Without it, each node's return would wipe out the conversation history.

**`AgentState` (`agent/state.py`)**
The shared "whiteboard" that all LangGraph nodes read from and write to. It's a `TypedDict` (a typed dictionary) containing `messages`, `customer_verified`, `customer_info`, `current_flow`, `target_flow`, `registration_step`, `appointment_details`, `verification_attempts`, and `session_id`. Every turn of the conversation passes this object between nodes.

**`ainvoke()` (LangGraph/LangChain)**
The async version of `.invoke()`. Runs the LangGraph state machine for one conversation turn and returns a dict with the updated state. Used in `LangGraphStream._run()` as `await self.graph.ainvoke(...)` because network calls (to Groq API) must be awaited.

**API Key**
A secret string that identifies you to a third-party service. In this project: `LIVEKIT_API_KEY`, `GROQ_API_KEY`, `DEEPGRAM_STT_API_KEY`, `DEEPGRAM_TTS_API_KEY`, `CARTESIA_API_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`. Never hardcode these — always read them from environment variables via `os.getenv()`.

**`asyncio`**
Python's standard library for cooperative concurrency. The `asyncio` event loop schedules coroutines (async functions) and switches between them when one is waiting on I/O. This project uses `asyncio.ensure_future()` to fire-and-forget background tasks (saving transcripts, latency logs), and `asyncio.create_task()` for similar purposes.

**`async def` / `await`**
`async def` marks a function as a coroutine — it can pause mid-execution to let other tasks run. `await` pauses execution at that point and yields control to the event loop until the awaited coroutine (or future) completes. Every network call in this project uses `await` to avoid freezing the audio pipeline.

---

## C

**`ChatContext` (LiveKit)**
LiveKit's representation of a conversation history — a list of messages with roles (`system`, `user`, `assistant`). Created with `llm.ChatContext().append(role="system", text=...)` in `main.py`. Passed to `VoicePipelineAgent` so the LLM knows the conversation so far.

**`ChatOpenAI` (LangChain)**
LangChain's LLM client for OpenAI-compatible APIs. In this project, it's configured with `base_url="https://api.groq.com/openai/v1"` to talk to Groq instead of OpenAI. Uses `.invoke(prompt)` to get a response. The response is an `AIMessage` object; use `.content` to get the text.

**ChromaDB**
The vector database used to store FAQ document embeddings. Stores data in `agent/chroma_db/` on disk (persistent). Provides `get_or_create_collection()` and `collection.query()` for vector similarity search. Used in `chroma_client.py` and called by `faq_node()` in `nodes.py`.

**`compiled_graph`**
The output of `build_graph()` in `graph_builder.py`. A `CompiledGraph` object returned by `builder.compile(checkpointer=MemorySaver())`. It's a singleton — created once at startup and reused for every call. The `thread_id` (passed via `config`) distinguishes each call's separate conversation memory.

**Conditional Edge (LangGraph)**
An edge where a function decides which node to route to next, rather than always going to the same destination. Set up with `builder.add_conditional_edges(source_node, routing_fn, mapping_dict)`. Used in this project to route from `entry_router` to either `greeting` or `route_input`, and from `route_input` to one of 7 processing nodes.

**CORS (Cross-Origin Resource Sharing)**
A browser security mechanism that blocks JavaScript from making requests to a different domain/port than the page was loaded from. Added via `CORSMiddleware` in `backend/main.py` to allow the React frontend (port 3000) to call the FastAPI backend (port 8000).

**Coroutine**
A Python function defined with `async def`. It doesn't execute when called — it returns a coroutine object. You must `await` it (or pass it to `asyncio.create_task()`) to actually run it.

---

## D

**Deepgram**
The speech-to-text (STT) and text-to-speech (TTS) provider. `deepgram.STT` converts the customer's voice audio to text. `deepgram.TTS` converts the agent's text response to audio. Both are LiveKit plugins configured with an API key. TTS uses streaming mode (`use_streaming=True`) to start playing audio before the full response is generated.

**Decorator**
A function that wraps another function to add behavior. In Python, written with `@` syntax. Key examples in this project: `@agent.on("user_speech_committed")` registers an event listener; `@router.post("/api/token")` registers a FastAPI route handler; `@app.get("/")` registers the root endpoint.

**`dotenv` / `.env`**
`python-dotenv` is the library (`from dotenv import load_dotenv`). `.env` is the file it reads. The file stores secrets as `KEY=VALUE` pairs. `load_dotenv()` reads the file and puts all values into `os.environ`. Without this, `os.getenv("GROQ_API_KEY")` would return `None`.

---

## E

**Edge (LangGraph)**
A connection between two nodes in a StateGraph. Regular edges always connect A→B. Conditional edges call a function to decide the destination. Added with `builder.add_edge("source", "destination")` or `builder.add_conditional_edges(...)`.

**Embedding**
A fixed-size list of floating-point numbers (e.g., 384 numbers) that represents the "meaning" of a piece of text. Similar meanings produce similar vectors. Used in this project to convert FAQ documents and customer questions into numbers, enabling similarity search in ChromaDB. Generated by the `all-MiniLM-L6-v2` SentenceTransformer model.

**`entrypoint()` (`agent/main.py`)**
The main async function called by LiveKit when a new call comes in. Creates the voice pipeline agent, registers all event listeners, plays the greeting, and runs the main call loop. Has the signature `async def entrypoint(ctx: JobContext)`.

**`ensure_future()` (`asyncio`)**
Schedules a coroutine to run on the event loop without waiting for it. Returns immediately. Used throughout `main.py` to fire-and-forget background tasks like saving transcripts and latency logs, so they never block the audio pipeline.

---

## F

**FastAPI**
The Python web framework for the backend (`backend/main.py` and `backend/routes.py`). Handles incoming HTTP requests, validates request bodies using Pydantic, and returns JSON responses. Provides automatic `/docs` interactive documentation. Run with `uvicorn main:app --reload`.

**`f-string`**
Python string formatting syntax using `f"..."`. Expressions inside `{}` are evaluated at runtime and inserted into the string. Example: `f"Session: {session_id[:8]}"` → `"Session: abc-12345"`. Used throughout the project for log messages and LLM prompts.

**Fire-and-Forget**
A pattern where you start an async task and don't wait for its result. In this project, saving transcripts and latency logs to Supabase is fire-and-forget — the audio pipeline continues immediately while the database writes happen in the background.

---

## G

**Graceful Degradation**
Designing a system so that it continues working (possibly with reduced features) when a non-critical component fails. In this project, if Supabase is unavailable, voice calls still work — transcripts and latency logs just aren't saved. Every Supabase function returns `False` (not an exception) on failure.

**Groq**
The LLM API provider. Groq hosts Meta's Llama models and serves them extremely fast (often 500+ tokens/second). Uses the OpenAI-compatible API format, so `ChatOpenAI` with a custom `base_url` works without any changes. Used for intent classification, FAQ answering, call summarization, and general chat.

---

## H

**`handoff.py` (`agent/handoff.py`)**
The module that manages human escalation state. Contains `_active_handoffs` (in-memory dict), `set_handoff_active()` (updates dict + Supabase), `is_handoff_active()` (instant check), and `share_transcript()` (fetches transcript for human agent context).

**Human Handoff**
The process of transferring a call from the AI agent to a human support representative. Triggered by the customer requesting it, verification failure, or technical errors. Controlled by `handoff.py` — sets a flag that causes `LangGraphStream._run()` to return early without generating a response.

**`httpx`**
The Python HTTP client library used by the agent to call the FastAPI backend. Example: `httpx.get(f"{BACKEND_URL}/api/customers/verify?phone={phone}", timeout=5.0)`. `timeout=5.0` prevents the agent from hanging if the backend is slow.

---

## J

**JWT (JSON Web Token)**
A signed, encoded string that carries authentication information. In this project, LiveKit access tokens are JWTs signed with the `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`. The LiveKit server verifies the signature to confirm the token is genuine and hasn't been tampered with. Generated by `api.AccessToken(...).to_jwt()` in `backend/routes.py`.

---

## L

**LangChain**
A Python framework for working with LLMs. Provides `ChatOpenAI` (LLM client), message types (`SystemMessage`, `HumanMessage`, `AIMessage`), and utilities for building prompts. Used as the foundation that LangGraph builds on. Key imports: `from langchain_openai import ChatOpenAI`, `from langchain_core.messages import AIMessage`.

**LangGraph**
A library (built on LangChain) for building stateful, multi-step LLM applications as graphs. Key concepts: `StateGraph`, `nodes` (functions), `edges` (connections), `MemorySaver` (conversation memory). The conversation logic lives in `graph_builder.py`. The graph is compiled once at startup and reused for all calls.

**`LangGraphLLM` (`agent/graph_builder.py`)**
A custom class that subclasses LiveKit's `llm.LLM`. Makes LiveKit think our LangGraph state machine is a regular LLM. Implements the `.chat()` method which returns a `LangGraphStream`. The `thread_id` attribute links each call to its conversation memory in `MemorySaver`.

**`LangGraphStream` (`agent/graph_builder.py`)**
A custom class that subclasses LiveKit's `llm.LLMStream`. Implements `_run()`, which: checks handoff status, converts messages, runs `graph.ainvoke()`, then streams the response word-by-word via `self._event_ch.send_nowait(chunk)`.

**`LatencyTracker` (`agent/utils.py`)**
A class that measures how long each pipeline step takes. Has `start(step)`, `end(step)`, `print_summary()`, and `reset()` methods. Uses `time.perf_counter()` for high-precision timing. Saves measurements to Supabase via `_save_to_db()`. One instance per call, keyed by `session_id`.

**LiveKit**
The real-time audio/video platform this project uses. Provides the WebSocket infrastructure for routing audio between the customer's browser and the AI agent. The `livekit-agents` Python SDK provides `VoicePipelineAgent`, `cli.run_app()`, `WorkerOptions`, and all the event types.

---

## M

**`MemorySaver` (LangGraph)**
The in-process checkpointer that saves LangGraph state between turns of a conversation. Stores state in a Python dict keyed by `thread_id`. When `graph.ainvoke()` is called with the same `thread_id`, it loads the saved state so the conversation continues from where it left off.

**Metadata (ChromaDB)**
Extra information stored alongside each document in ChromaDB. In this project, `{"source": "hours.txt"}`. Not used for search, but logged when a FAQ document is returned to help with debugging: "ChromaDB returned hours.txt for query: 'What time do you open?'".

---

## N

**Node (LangGraph)**
A Python function that represents one step in the conversation. Each node receives the current `AgentState`, does its work, and returns a partial dict of state updates. Examples: `greeting_node`, `faq_node`, `verify_customer_node`, `escalate_node`. Added to the graph with `builder.add_node("name", function)`.

---

## P

**Pydantic**
A Python data validation library. Used in FastAPI to define the shape of request and response bodies. `class TokenRequest(BaseModel)` defines what fields a POST request must have. FastAPI automatically validates incoming JSON against the model and returns a 422 error if validation fails.

**Prompt Engineering**
The practice of crafting LLM prompts to get reliable, high-quality responses. Key techniques used in this project:
- **Role setting**: "You are a friendly support agent..."
- **Constraint**: "Answer ONLY using the provided context"
- **Format**: "Do not use bullet points"
- **Few-shot**: Sometimes providing examples
- **Signal phrase**: "Agent Response:" to signal where generation starts

---

## R

**RAG (Retrieval-Augmented Generation)**
A technique where you retrieve relevant information FIRST, then inject it into the LLM prompt as context. In this project: query ChromaDB → get FAQ text → insert into prompt → LLM answers based on your FAQ text, not its training data. Prevents hallucination and keeps answers current.

**`RunnableConfig` (LangChain)**
A dictionary containing configuration for a LangChain/LangGraph run. The key field in this project: `config["configurable"]["thread_id"]` — this is how nodes access the session_id. Passed automatically by LangGraph when a node declares `config: RunnableConfig` as a parameter.

**`run_in_executor()` (asyncio)**
Runs a blocking (synchronous) function in a thread pool, so it doesn't freeze the event loop. Pattern: `await loop.run_in_executor(None, lambda: some_blocking_function(args))`. Used whenever the agent needs to call a synchronous library (like the Supabase Python client) from an async context.

---

## S

**Session ID (`session_id`)**
A UUID (Universally Unique Identifier) string generated at the start of each call using `str(uuid.uuid4())`. Example: `"a1b2c3d4-e5f6-7890-abcd-ef1234567890"`. Used as both the Supabase `call_sessions.id` and the LangGraph `thread_id`, linking all data from a call together.

**Silero VAD**
The Voice Activity Detection model from Silero. Continuously analyzes incoming audio and determines whether the customer is currently speaking. Fires `user_started_speaking` and `user_stopped_speaking` events in LiveKit. Loaded at startup with `silero.VAD.load()` and assigned to `VAD_PLUGIN`.

**SQLite**
A lightweight, file-based SQL database. In this project, stored at `backend/voice_support.db`. Handles the `customers` and `tickets` tables — operational data that the agent needs to verify customers and create support tickets. Managed by Python's built-in `sqlite3` module.

**`StateGraph` (LangGraph)**
The builder class for creating a LangGraph state machine. You instantiate it with a schema (`StateGraph(AgentState)`), add nodes and edges, then call `.compile()` to get a `CompiledGraph` you can run with `.invoke()` or `.ainvoke()`.

**Supabase**
A cloud-hosted PostgreSQL database service. Used in this project for telemetry: `call_sessions`, `call_transcripts`, and `latency_logs`. The Python client (`from supabase import create_client`) uses a builder pattern: `client.table("table_name").select("*").eq("id", value).execute()`.

**SentenceTransformer**
The model type used to generate embeddings. In this project, `all-MiniLM-L6-v2` from the `sentence-transformers` library. Converts text of any length into a 384-dimensional vector. Runs locally (no API needed). Integrated into ChromaDB via `SentenceTransformerEmbeddingFunction`.

---

## T

**Thread ID (LangGraph)**
The key used by `MemorySaver` to store and retrieve conversation state. In this project, `thread_id = session_id` (the call UUID). Passed via `config={"configurable": {"thread_id": session_id}}` in every `graph.ainvoke()` call. Without this, every turn would start with a blank slate.

**TTS (Text-to-Speech)**
The process of converting text to audio. In this project, Deepgram's TTS converts the agent's text responses into voice audio that plays through the customer's speakers. Uses `use_streaming=True` so TTS starts producing audio before the full response is ready, reducing perceived latency.

**TypedDict**
A Python class (from `typing`) that defines a dictionary with specific named keys and expected types. `AgentState(TypedDict)` declares the schema for LangGraph's state object. It's just documentation/typing — the actual runtime object is a regular Python dict.

---

## U

**Uvicorn**
The ASGI web server that runs FastAPI. Run with `uvicorn main:app --reload` from inside the `backend/` directory. ASGI (Asynchronous Server Gateway Interface) means it handles requests asynchronously, letting FastAPI's `async def` routes work properly.

---

## V

**VAD (Voice Activity Detection)**
A model that determines whether audio contains human speech or silence. In this project, Silero VAD monitors the audio stream continuously and fires events (`user_started_speaking`, `user_stopped_speaking`) that the voice pipeline uses to know when to start/stop listening.

**Vector**
In the context of this project: a list of floating-point numbers representing the "semantic meaning" of a piece of text. Used by ChromaDB to find similar documents. Two texts with similar meanings have vectors that are "close together" in the mathematical sense (small cosine distance).

**`VoicePipelineAgent` (LiveKit)**
The central object in the agent code. Wires together VAD → STT → LLM → TTS into a complete voice pipeline. Registers the audio input from the room, processes it through each stage, and sends the audio output back. Created in `entrypoint()` and started with `agent.start(ctx.room)`.

---

## W

**WebSocket (`wss://`)**
A persistent, bidirectional network connection. Unlike regular HTTP (request → response → done), WebSockets stay open. LiveKit uses WebSockets to stream audio in real-time between the customer's browser and the LiveKit server (and between the server and the agent worker). The `wss://` prefix means it's a secure (encrypted) WebSocket.

**Worker (LiveKit)**
The long-running Python process that handles calls. Started with `cli.run_app(WorkerOptions(...))` in `main.py`. Connects to the LiveKit server, registers as available to handle jobs, and calls `entrypoint(ctx)` whenever a new call comes in. One worker can handle multiple concurrent calls.

---

## Z

**Zero-downtime Pattern**
This project uses several patterns to ensure calls never drop due to non-critical failures:
- Fire-and-forget for Supabase logging (a DB timeout doesn't pause audio)
- `try/except` with fallback responses in every node (LLM failure → safe fallback message)
- Graceful degradation (Supabase down → calls still work, just without telemetry)
- Reconnection events in LiveKit (transient network issues auto-recover)
