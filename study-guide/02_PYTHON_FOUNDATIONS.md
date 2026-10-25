# 02 — Python Foundations: The Language Concepts This Project Uses

> **Before touching any of the project's code,** let's make sure you understand the Python
> building blocks it relies on. Every concept below includes:
> - A plain-English explanation
> - A small standalone example you can run yourself
> - The ACTUAL code from this project that uses it

---

## 1. Virtual Environments — Why We Isolate Dependencies

### What is it?

A **virtual environment** (venv) is a self-contained folder that holds a specific version of Python
and all the packages your project needs — **separate from every other project on your machine**.

**The problem without venvs:**
Imagine two projects:
- Project A needs `langchain version 0.1`
- Project B needs `langchain version 0.3`

If you install both globally, one overwrites the other. Both projects may break.

A venv solves this by giving each project its own little Python world.

### Standalone example

```bash
# Create a virtual environment in a folder called my_env
python3 -m venv my_env

# Activate it (Mac/Linux)
source my_env/bin/activate
# Now your terminal prompt shows (my_env)

# Install packages ONLY into this venv — not globally
pip install langchain

# When done, deactivate
deactivate
```

### In THIS project

The project has separate venvs:
- `agent/venv/` — for the AI agent's packages
- `backend/venv/` — for the FastAPI server's packages

Their dependencies are listed in `requirements.txt`:

```
# agent/requirements.txt — these are what pip installs into the agent's venv

livekit-agents<1.0           # The LiveKit voice agent framework
livekit-plugins-deepgram<1.0 # Deepgram STT + TTS integration
livekit-plugins-silero<1.0   # Silero VAD (voice activity detection)
python-dotenv>=1.0.0         # Reads .env files into os.environ

langgraph>=0.1.0             # State machine for conversations
langchain-openai>=0.1.0      # LangChain wrapper for OpenAI-compatible APIs (e.g., Groq)
chromadb>=0.4.0              # Vector database for FAQ search
sentence-transformers>=2.2.0 # Turns text into vectors (embeddings)
httpx>=0.24.0                # HTTP client (for the agent to call FastAPI)

supabase>=2.0.0              # Cloud PostgreSQL client for call telemetry
```

When you run `pip install -r requirements.txt`, Python reads this file and installs every package listed.

---

## 2. Environment Variables & `.env` Files — Keeping Secrets Safe

### What is it?

An **environment variable** is a named value stored in your operating system's memory,
not in your source code. You use them to store secrets (API keys, passwords) so they
never end up in your code files or on GitHub.

**Why not hardcode the key?**
If you write `api_key = "sk-abc123"` directly in code and push it to GitHub, everyone can see it.
Someone could use your key, rack up API charges, and you'd foot the bill.

### How `.env` files work

A `.env` file is a plain text file (never uploaded to GitHub — it's listed in `.gitignore`)
that stores variables as `KEY=VALUE` pairs:

```
# .env (at the project root)
LIVEKIT_URL=wss://my-project.livekit.cloud
GROQ_API_KEY=gsk_abc123xyz
DEEPGRAM_STT_API_KEY=Token_abc123
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
```

The `python-dotenv` library reads this file and loads the values into `os.environ` at runtime.

### Standalone example

```python
# First create a file called .env with the line: MY_SECRET=hello_world

from dotenv import load_dotenv   # pip install python-dotenv
import os

load_dotenv()                    # Reads .env, puts all KEY=VALUE into os.environ

secret = os.getenv("MY_SECRET")  # Retrieve a value by name
print(secret)                    # → hello_world

# If the variable doesn't exist, os.getenv returns None (no error)
missing = os.getenv("DOES_NOT_EXIST")
print(missing)                   # → None

# You can provide a default value as the second argument:
port = os.getenv("PORT", "8000") # Returns "8000" if PORT isn't in .env
```

### In THIS project — `agent/config.py`

```python
# agent/config.py
import os
from dotenv import load_dotenv

# Calculate the path to the project root directory.
# os.path.abspath(__file__)    = full path to config.py
# os.path.dirname(...)         = the folder it's in  → agent/
# os.path.dirname(... again)   = one level up        → project root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Build the full path to the .env file: project_root/.env
env_path = os.path.join(root_dir, ".env")

# Load it. After this, os.getenv("LIVEKIT_URL") will work.
# override=True: if a variable was already set in os.environ, replace it
load_dotenv(dotenv_path=env_path, override=True)

# Read individual values. Returns None if the key isn't in the .env file.
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPGRAM_STT_API_KEY = os.getenv("DEEPGRAM_STT_API_KEY")
```

And the validation function catches missing keys with a helpful error message:

```python
# agent/config.py — validate_config()
def validate_config():
    missing_vars = []
    for var_name, description in REQUIRED_ENV_VARS.items():
        val = os.getenv(var_name)
        # If the value is missing, or still has placeholder text like "your-api-key"
        if not val or val.startswith("your-") or val.endswith("-key"):
            missing_vars.append((var_name, description))

    if missing_vars:
        print("Configuration ERROR: Missing environment variables!")
        for name, desc in missing_vars:
            print(f"  {name}: {desc}")
        sys.exit(1)  # Stop the program immediately with a clear error
```

---

## 3. `async` / `await` — How Python Does Multiple Things at Once

### What is it?

Normally Python runs one line at a time. If one line takes 2 seconds (like a network request),
Python *sits and waits*, doing nothing else.

**`async/await` is Python's solution.** It lets you say:
"Start this task, and while it's waiting on the network, go do something else."

This is called **cooperative concurrency**.

### Why does a voice agent NEED this?

Think about what happens during one call turn:
1. Customer speaks → Deepgram STT processes audio (~300ms)
2. LangGraph runs → Groq LLM generates a response (~500ms)
3. Deepgram TTS converts text to audio and streams it back
4. Simultaneously, transcript and latency data must be saved to Supabase

If any of these blocked (waited synchronously), the audio pipeline would stutter and freeze.
`async/await` keeps everything flowing smoothly.

### Key terms

| Term | What it means |
|------|--------------|
| `coroutine` | A function defined with `async def`. Doesn't run until you `await` it. |
| `await` | "Pause here, let other tasks run while this one waits for I/O." |
| `event loop` | The "traffic controller" that decides which coroutine runs next. |
| `asyncio.create_task()` | Schedule a coroutine to run in the background — don't wait for it. |
| `asyncio.ensure_future()` | Similar to create_task; older style. Used in this project. |
| `run_in_executor()` | Runs a blocking (synchronous) function in a thread so it doesn't freeze the event loop. |

### Standalone example

```python
import asyncio

# 'async def' means this is a coroutine — you must await it to use it
async def fetch_data():
    print("Starting fetch...")
    await asyncio.sleep(2)   # Simulate a 2-second network wait
                             # 'await' = "pause here and let other code run"
    print("Fetch complete!")
    return "result"

async def do_other_work():
    print("Doing other work...")
    await asyncio.sleep(1)   # Simulate 1 second of other work
    print("Other work done!")

async def main():
    # create_task() starts both coroutines running "simultaneously"
    task1 = asyncio.create_task(fetch_data())
    task2 = asyncio.create_task(do_other_work())

    await task1              # Wait for task1 to finish
    await task2              # Wait for task2 to finish

asyncio.run(main())
# Output:
# Starting fetch...
# Doing other work...
# Other work done!     ← finished at 1 second
# Fetch complete!      ← finished at 2 seconds
```

### In THIS project — `agent/main.py`

```python
# The entrypoint function is 'async def' because it coordinates many
# network operations that each take variable amounts of time.
# Without async, every await would block the whole program.
async def entrypoint(ctx: JobContext):

    # 'await ctx.connect()' tells Python:
    # "Connect to the LiveKit room. While the network handshake happens
    # (could take 50-200ms), let other things run if needed."
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # 'await agent.say(...)' plays audio over LiveKit.
    # We await it so the function pauses until the greeting audio starts.
    # Without await here, we'd move on before the customer hears anything.
    await agent.say("Hello! Welcome to Epoxcel...", allow_interruptions=True)
```

```python
# Background task pattern: the event listener is a REGULAR function (not async)
# but it schedules an async task using asyncio.ensure_future()
@agent.on("user_speech_committed")
def on_user_speech_committed(msg: llm.ChatMessage):
    text = msg.content if isinstance(msg.content, str) else ""

    # ensure_future() says: "schedule this coroutine on the event loop and run
    # it as soon as the loop is free. Don't wait for it here."
    # This means the transcript save happens in the background — it never
    # delays the audio pipeline.
    asyncio.ensure_future(
        _save_transcript_async(session_id, "user", text, message_sequence[0])
    )

# The actual async function that does the work
async def _save_transcript_async(session_id, role, content, sequence):
    try:
        loop = asyncio.get_event_loop()
        # run_in_executor() moves a BLOCKING (synchronous) call into a thread pool.
        # The Supabase Python client uses requests (synchronous/blocking).
        # If we called it directly, it would freeze the event loop.
        # run_in_executor wraps it so it runs in a separate thread while the
        # event loop stays free to handle audio.
        await loop.run_in_executor(
            None,   # None = use the default thread pool executor
            lambda: save_transcript_entry(session_id, role, content, sequence)
        )
    except Exception as e:
        # Never crash the call because of a logging failure
        logger.error(f"Failed to save transcript: {e}")
```

---

## 4. Type Hints — What `str`, `Optional[str]`, `list[dict]` Mean

### What is it?

Python is dynamically typed — you can put any value in any variable. Type hints let you
*annotate* what type a variable should be. They don't enforce anything at runtime, but
they help editors catch bugs and make code self-documenting.

### Standalone example

```python
# Without type hints — works, but editor can't help you
def greet(name):
    return "Hello " + name

# With type hints — same function, now self-documenting
def greet(name: str) -> str:     # Takes a str, returns a str
    return "Hello " + name

# Common types:
x: int = 42
y: float = 3.14
z: str = "hello"
flag: bool = True

# Optional means "this can be None OR the type"
from typing import Optional
def find_customer(phone: str) -> Optional[dict]:
    # Returns a dict if found, or None if not found
    ...

# List of strings
names: list[str] = ["Alice", "Bob"]

# Dict with string keys and any-type values
data: dict[str, any] = {"name": "Alice", "age": 30}
```

### In THIS project — `agent/state.py`

```python
# agent/state.py
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# TypedDict is a dict where each key has a declared type.
# This is the "whiteboard" shared between all LangGraph nodes.
class AgentState(TypedDict):

    # Annotated[List[BaseMessage], add_messages] means:
    #   - It's a List of BaseMessage objects (chat history)
    #   - add_messages is a LangGraph instruction: "when updating this field,
    #     APPEND new messages instead of replacing the whole list"
    messages: Annotated[List[BaseMessage], add_messages]

    # bool: only True or False
    customer_verified: bool

    # Optional[Dict[str, Any]]: a dict with string keys, any-type values, OR None
    customer_info: Optional[Dict[str, Any]]

    # int: a whole number (0, 1, 2...)
    verification_attempts: int

    # str: always a string (e.g., "greeting", "verify", "booking")
    current_flow: str

    # Optional[str]: a string or None (not all calls need a target_flow)
    target_flow: Optional[str]
    registration_step: Optional[str]
```

### In THIS project — `agent/nodes.py`

```python
# agent/nodes.py — function signatures show types at a glance

def get_groq_llm() -> ChatOpenAI:
    # Tells you: this returns a ChatOpenAI object, always
    ...

def get_fast_groq_llm(
    max_tokens: Optional[int] = None,   # int or None, default None
    temperature: float = 0.0             # float, default 0.0
) -> ChatOpenAI:
    ...

def extract_phone_digits(text: str) -> Optional[str]:
    # Takes a string, returns either a 10-digit string or None
    ...

def extract_appointment_info(text: str) -> Dict[str, Optional[str]]:
    # Returns e.g.: {"date": "Friday", "time": None}
    ...
```

---

## 5. Decorators — What `@agent.on(...)` Actually Does

### What is it?

A **decorator** is a function that wraps another function and adds behavior to it.

The `@` syntax is shorthand for: `my_function = decorator(my_function)`.

### Standalone example

```python
# A decorator that logs whenever a function is called
def log_calls(func):
    # 'wrapper' is the replacement function
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}...")   # Before the original function
        result = func(*args, **kwargs)          # Call the original function
        print(f"{func.__name__} finished.")     # After it returns
        return result
    return wrapper   # Return the new, wrapped version

# The @ syntax applies the decorator:
@log_calls           # Same as: greet = log_calls(greet)
def greet(name):
    return f"Hello {name}"

greet("Alice")
# Calling greet...
# greet finished.
# → "Hello Alice"
```

### In THIS project — `agent/main.py`

The most important decorator pattern is `@agent.on(event_name)`:

```python
# agent/main.py

# agent.on("user_speech_committed") is itself a function that RETURNS a decorator.
# When Python processes this, it:
#   1. Calls agent.on("user_speech_committed") → gets a decorator back
#   2. Applies that decorator to on_user_speech_committed
#   3. The decorator registers the function in LiveKit's internal event registry

# Result: LiveKit will AUTOMATICALLY CALL this function every time the
# "user_speech_committed" event fires. We never call it manually.
@agent.on("user_speech_committed")
def on_user_speech_committed(msg: llm.ChatMessage):
    # 'committed' means VAD confirmed the user fully stopped speaking
    text = msg.content if isinstance(msg.content, str) else ""
    if not text.strip():
        return   # Skip blank/noise utterances

    message_sequence[0] += 1
    last_activity_time[0] = datetime.now(timezone.utc)

    # Save the transcript to Supabase in the background
    asyncio.ensure_future(
        _save_transcript_async(session_id, "user", text, message_sequence[0])
    )

# Room events use the same pattern on a different object (ctx.room instead of agent)
@ctx.room.on("participant_connected")
def on_participant_connected(participant: rtc.RemoteParticipant):
    # LiveKit calls this automatically when the customer joins.
    # 'participant' is passed by LiveKit — we don't provide it.
    logger.info(f"[Room Event] Participant JOINED: {participant.identity}")
```

---

## 6. Classes and `__init__` — The Blueprint Pattern

### What is it?

A **class** is a blueprint for creating objects that bundle:
- **data** (called attributes or instance variables, stored on `self`)
- **functions that act on that data** (called methods)

`__init__` is the constructor — it runs when you create a new instance with `ClassName(args)`.

`self` is a reference to the specific instance being used.

### In THIS project — `agent/utils.py` (LatencyTracker)

```python
# agent/utils.py

class LatencyTracker:
    # __init__ runs when you write: tracker = LatencyTracker("abc-123")
    def __init__(self, session_id: str):
        # Store session_id on THIS specific instance
        # (multiple calls can each have their own tracker)
        self.session_id = session_id

        # A fresh empty dict for this instance's timing data
        self._start_times: Dict[str, float] = {}   # step → start timestamp
        self._results: Dict[str, float] = {}        # step → elapsed ms

    # 'start' marks when a pipeline step begins
    def start(self, step: str) -> None:
        # time.perf_counter() returns a high-precision timestamp in seconds
        # We store it so end() can calculate elapsed time
        self._start_times[step] = time.perf_counter()

    # 'end' marks when a step finishes and calculates how long it took
    def end(self, step: str) -> Optional[float]:
        if step not in self._start_times:
            return None   # Can't calculate if start() wasn't called

        # (current time) - (start time) = elapsed seconds → convert to ms
        elapsed_ms = (time.perf_counter() - self._start_times[step]) * 1000.0
        self._results[step] = elapsed_ms
        del self._start_times[step]  # Clean up so we don't double-count

        # Log the result
        _latency_file_logger.info(
            f"[LATENCY] session={self.session_id[:8]}... | step={step:<4} | {elapsed_ms:.1f}ms"
        )
        self._save_to_db(step, elapsed_ms)
        return elapsed_ms

    def reset(self) -> None:
        # Clear all data at the start of each new call turn
        self._start_times.clear()
        self._results.clear()
```

In `main.py`:

```python
# One LatencyTracker is created per call session
latency_tracker = LatencyTracker(session_id=session_id)

# Each event updates the tracker for this specific session
@agent.on("user_started_speaking")
def on_user_started_speaking():
    latency_tracker.reset()       # Fresh start for this turn
    latency_tracker.start("stt")  # STT timer begins

@agent.on("user_stopped_speaking")
def on_user_stopped_speaking():
    latency_tracker.end("stt")    # STT is processing now (user stopped)
    latency_tracker.start("llm")  # LLM timer begins immediately after

@agent.on("agent_started_speaking")
def on_agent_started_speaking():
    latency_tracker.end("llm")    # LLM produced its response
    latency_tracker.start("tts")  # TTS is now converting it to audio

@agent.on("agent_stopped_speaking")
def on_agent_stopped_speaking():
    latency_tracker.end("tts")        # TTS finished streaming
    latency_tracker.print_summary()   # Logs: stt=312ms | llm=489ms | tts=203ms | total=1004ms
```

---

## 7. f-strings — Readable String Formatting

### What is it?

An f-string (`f"..."`) lets you embed any Python expression directly inside a string,
wrapped in `{}`.

### Standalone example

```python
name = "Epixa"
session_id = "abc-123-xyz-789-full-uuid"

# Old way (messy):
msg = "Agent: " + name + " | Session: " + session_id[:8] + "..."

# f-string (clean):
msg = f"Agent: {name} | Session: {session_id[:8]}..."
# → "Agent: Epixa | Session: abc-123-..."

# You can put any expression inside {}:
print(f"Two plus two is {2 + 2}")           # → Two plus two is 4
print(f"Uppercase: {'hello'.upper()}")       # → Uppercase: HELLO

# Format numbers:
ms = 342.5678
print(f"Latency: {ms:.1f}ms")    # .1f = 1 decimal place → 342.6ms
print(f"Step: {'stt':<4}")       # :<4 = left-align in 4-char field → "stt "
```

### In THIS project — `agent/main.py`

```python
# agent/main.py — the greeting uses an f-string to personalize
customer_name = state.get("customer_info", {}).get("name", "")
greeting = f"I can certainly help you book an appointment, {customer_name}."

# agent/utils.py — latency log formatting
_latency_file_logger.info(
    # session_id[:8] = first 8 chars of the UUID (keeps logs readable)
    # step:<4       = left-align step name in a 4-char field (stt, llm, tts align nicely)
    # elapsed_ms:.1f = 1 decimal place for milliseconds
    f"[LATENCY] session={self.session_id[:8]}... | step={step:<4} | {elapsed_ms:.1f}ms"
)
```

---

## 8. Error Handling — `try` / `except` / `finally`

### What is it?

`try/except` lets you catch runtime errors and handle them gracefully instead of crashing.

### Standalone example

```python
# Without error handling — crashes if Groq API is down:
response = groq_llm.invoke(prompt)   # Raises an exception if network fails

# With error handling — catches the error and returns a safe fallback:
try:
    response = groq_llm.invoke(prompt)
    answer = response.content.strip()
except Exception as e:
    # 'Exception' is the base class for all errors in Python
    # 'as e' binds the exception object so we can inspect it
    logger.error(f"LLM call failed: {e}")
    answer = "I'm having trouble right now. Please try again."

# 'finally' always runs, even if there was an exception
try:
    conn = open_database_connection()
    conn.execute(some_query)
except Exception as e:
    logger.error(f"Database error: {e}")
finally:
    conn.close()   # Always close the connection, even on error
```

### In THIS project — `agent/graph_builder.py` (LangGraphStream._run)

```python
# agent/graph_builder.py — the core LLM stream handler

async def _run(self) -> None:
    try:
        # Check if the human has taken over — if so, stay silent
        if is_handoff_active(self._llm.thread_id):
            return   # Exit immediately; don't generate any response

        # Build LangChain message list from LiveKit ChatContext
        lc_messages = []
        for msg in self._chat_ctx.messages:
            if msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))

        # Run the LangGraph state machine with this session's thread_id
        config = {"configurable": {"thread_id": self._llm.thread_id}}
        result = await self.graph.ainvoke({"messages": lc_messages}, config=config)

        # Stream the response word by word so TTS can start early
        messages = result.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content
            for i, word in enumerate(content.split(" ")):
                space = " " if i > 0 else ""
                chunk_text = space + word

                choice_delta = llm.ChoiceDelta(role="assistant", content=chunk_text)
                choice = llm.Choice(delta=choice_delta, index=0)
                chunk = llm.ChatChunk(request_id="langgraph", choices=[choice])
                self._event_ch.send_nowait(chunk)   # Push word to TTS
                await asyncio.sleep(0.005)           # Yield briefly for cooperative scheduling

    except Exception as e:
        # If anything goes wrong (LangGraph error, Groq timeout, etc.)
        # we log it but don't re-raise — this prevents the whole call from crashing
        logger.error(f"Error in LangGraph stream executor: {str(e)}")
    finally:
        # This ALWAYS runs.
        # Without closing the event channel, LiveKit would wait forever
        # for more tokens and the TTS pipeline would hang permanently.
        self._event_ch.close()
```

---

## 9. List Comprehensions — Concise Filtering and Mapping

### What is it?

A compact one-line way to create a new list by transforming or filtering another.

```python
# Regular loop:
numbers = [1, 2, 3, 4, 5]
squared = []
for n in numbers:
    squared.append(n ** 2)

# List comprehension — same result:
squared = [n ** 2 for n in numbers]
# → [1, 4, 9, 16, 25]

# With a filter (only even numbers):
evens = [n for n in numbers if n % 2 == 0]
# → [2, 4]
```

### In THIS project — `agent/embed_documents.py`

```python
# Get all files in the faq_docs directory (might include .DS_Store, etc.)
all_files = os.listdir(FAQ_DOCS_DIR)

# Comprehension: only include files that end with ".txt"
# Without this filter, .DS_Store or other files would cause errors
files = [f for f in os.listdir(FAQ_DOCS_DIR) if f.endswith(".txt")]
# → ["hours.txt", "location.txt", "pricing.txt", "refunds.txt"]
```

### In THIS project — `agent/main.py` (generate_call_summary)

```python
# transcript_entries is a list of dicts: [{"role": "user", "content": "..."},  ...]
transcript_entries = get_full_transcript(session_id)

# Format each entry as "User: ..." or "Agent: ..." and join them with newlines
# .capitalize() changes "user" → "User", "agent" → "Agent"
conversation_text = "\n".join([
    f"{entry['role'].capitalize()}: {entry['content']}"
    for entry in transcript_entries
])
# → "User: I want to book an appointment\nAgent: Sure! What date works?"
```

---

*Next up → [03_LIVEKIT_DEEPDIVE.md](./03_LIVEKIT_DEEPDIVE.md)*
