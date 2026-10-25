# 06 — RAG and Embeddings Deep Dive: How the Agent Answers FAQs

> This file explains how your agent knows that store hours are "Mon-Fri 9am-6pm IST"
> without that fact being baked into the LLM's training data.

---

## The Problem: LLMs Don't Know Your Business

When you ask Groq's LLaMA model "What are Epoxcel's store hours?", it will likely say
"I don't have that information" or make something up. That's because:
1. The LLM was trained on general internet data, not your company's data
2. Even if your info was in the training data, it would be frozen at the training cutoff date
3. You can't retrain the LLM every time your hours change (that costs millions of dollars)

**RAG (Retrieval-Augmented Generation) solves this** by:
1. Storing your business knowledge in a searchable database
2. When a customer asks a question, finding the relevant document FIRST
3. Feeding that document to the LLM AS CONTEXT in the prompt
4. The LLM answers based on your data, not its training data

Think of it as: "Instead of asking the LLM to remember everything, give it the right textbook page to read BEFORE answering."

---

## What Are Embeddings?

An **embedding** is a way of converting text into a list of numbers (a "vector") that
represents its meaning. The key property: **similar meanings → similar numbers**.

### The Analogy

Imagine a giant 3D space where every sentence is a point. Sentences with similar meanings
are placed close together; unrelated sentences are far apart:

```
                        "What are your opening times?"
                              ●
                         ●   ●       ← related to hours
"When do you open?" ●
                                          ● "How do I get a refund?" ← different topic
                                    ●
                              "Can I return a product?"  ← near refund topic
```

**Embedding** = the (x, y, z, ...) coordinates of each sentence in this space.
In practice, the space has 384 dimensions (not 3), but the concept is the same.

### What Model Does This Project Use?

```python
# agent/chroma_client.py
_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
```

`all-MiniLM-L6-v2` is a small, fast, open-source model from HuggingFace that runs
**locally on your machine** (no API call needed). It converts any text into a 384-number vector.

---

## What Is Vector Search / Similarity Search?

When a customer asks "What time do you open?":
1. Convert that question to a vector (384 numbers)
2. Compare it to ALL stored document vectors (hours.txt, location.txt, pricing.txt, refunds.txt)
3. Find the vector that is CLOSEST (most similar) to the question vector
4. Return the document at that location

"Closest" is measured using **cosine similarity** — basically, the angle between two vectors.
Smaller angle = more similar meaning. ChromaDB does this math automatically.

---

## What Is ChromaDB?

ChromaDB is a **vector database** — a database specifically designed to store and query embeddings.

Key concepts:
- **Collection**: Like a table in a regular database. All your FAQ documents go into one collection.
- **Document**: The actual text content (e.g., the contents of `hours.txt`)
- **Embedding**: The vector representation of each document (auto-generated when you add a document)
- **Metadata**: Extra information stored alongside each document (e.g., `{"source": "hours.txt"}`)
- **ID**: A unique string identifier for each document

ChromaDB stores everything in the `agent/chroma_db/` folder as files on disk.

---

## Step 1: Loading FAQ Documents into ChromaDB — `agent/embed_documents.py`

This script runs **once** (or whenever you update the FAQ files). It reads `.txt` files and
stores them in ChromaDB:

```python
# agent/embed_documents.py

import os
from chroma_client import get_or_create_collection

# Define where the raw FAQ text files live
FAQ_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq_docs")

def embed_faq_documents():
    # Get or create the "faq_collection" in ChromaDB
    # If it already exists, this returns the existing one
    collection = get_or_create_collection()

    # Verify the directory exists before trying to read it
    if not os.path.exists(FAQ_DOCS_DIR):
        print(f"Directory {FAQ_DOCS_DIR} not found.")
        return

    # List comprehension: get all .txt files (skip .DS_Store etc.)
    files = [f for f in os.listdir(FAQ_DOCS_DIR) if f.endswith(".txt")]

    # These three lists will be parallel:
    # documents[0] corresponds to ids[0] and metadatas[0]
    documents = []   # The actual text content of each file
    ids = []         # A unique ID for each document
    metadatas = []   # Extra info (like which file it came from)

    for file_name in files:
        file_path = os.path.join(FAQ_DOCS_DIR, file_name)

        # Read the full text content of the file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()  # .strip() removes leading/trailing whitespace

        if content:   # Only process non-empty files
            documents.append(content)

            # Use filename without extension as the ID
            # "hours.txt" → "hours"
            doc_id = os.path.splitext(file_name)[0]
            ids.append(doc_id)

            # Metadata: store the filename so we can reference it in logs
            metadatas.append({"source": file_name})
            print(f"Loaded: {file_name} ({len(content)} chars)")

    if documents:
        # collection.upsert() = "insert if new, update if already exists"
        # This is safer than .add() which would fail on duplicates.
        # ChromaDB automatically:
        #   1. Calls the embedding function on each document text
        #   2. Gets back 384-number vectors
        #   3. Stores them alongside the text and metadata
        collection.upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        print(f"Stored {len(documents)} documents in ChromaDB!")


# This block runs when you execute: python embed_documents.py
if __name__ == "__main__":
    embed_faq_documents()
```

**Clean version (what the file actually looks like):**
```python
import os
from chroma_client import get_or_create_collection

FAQ_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq_docs")

def embed_faq_documents():
    collection = get_or_create_collection()
    files = [f for f in os.listdir(FAQ_DOCS_DIR) if f.endswith(".txt")]
    documents, ids, metadatas = [], [], []
    for file_name in files:
        with open(os.path.join(FAQ_DOCS_DIR, file_name), "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            documents.append(content)
            ids.append(os.path.splitext(file_name)[0])
            metadatas.append({"source": file_name})
    if documents:
        collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

if __name__ == "__main__":
    embed_faq_documents()
```

---

## Step 2: The ChromaDB Client — `agent/chroma_client.py`

```python
# agent/chroma_client.py

import os
import chromadb
from chromadb.utils import embedding_functions

# The path where ChromaDB stores its files on disk.
# os.path.dirname(os.path.abspath(__file__)) = the agent/ directory
# "chroma_db" = a subfolder inside agent/
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

# PersistentClient = ChromaDB stores data to disk (survives restarts).
# Without PersistentClient (using just Client()), data lives only in RAM.
# Every restart would require re-embedding all documents — that takes 30+ seconds.
_client = chromadb.PersistentClient(path=DB_DIR)

# Load the embedding model.
# We try local_files_only=True first to avoid a slow Hugging Face network check.
# If the model isn't cached locally, fall back to downloading it.
try:
    _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2",
        local_files_only=True    # Don't go to the internet — use cached version
    )
except Exception:
    # Model not cached yet — download it from Hugging Face
    _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_or_create_collection():
    """
    Returns the faq_collection, creating it if it doesn't exist yet.
    The embedding_function is attached so ChromaDB auto-embeds everything.
    """
    return _client.get_or_create_collection(
        name="faq_collection",           # The name of our FAQ vector store
        embedding_function=_embedding_fn  # This model converts text → vectors
    )


def query_faq(query_text: str, n_results: int = 1):
    """
    Converts 'query_text' to a vector, finds the n_results most similar
    documents in the collection, and returns them.

    Args:
        query_text: The customer's question (as a string)
        n_results:  How many results to return (1 = just the best match)

    Returns:
        documents: list of text strings (the matching FAQ content)
        metadatas: list of metadata dicts ({"source": "hours.txt"} etc.)
    """
    collection = get_or_create_collection()

    # collection.query() does the vector search:
    # 1. Converts query_text to a vector using _embedding_fn
    # 2. Calculates similarity between this vector and all stored vectors
    # 3. Returns the top n_results most similar documents
    results = collection.query(
        query_texts=[query_text],   # Note: this is a LIST — ChromaDB can batch queries
        n_results=n_results
    )

    # results structure from ChromaDB:
    # {
    #   "documents": [["text of result 1", "text of result 2"]],  # nested list (one list per query)
    #   "metadatas": [[{"source": "hours.txt"}, {"source": "location.txt"}]],
    #   "distances": [[0.12, 0.45]],   # similarity scores (lower = more similar)
    #   "ids": [["hours", "location"]]
    # }
    # We passed one query, so we access index [0] to get the inner list.
    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []

    return documents, metadatas
```

---

## Step 3: Using the Query Result in `faq_node` — `agent/nodes.py`

This is where everything comes together. The customer's question is searched against ChromaDB,
and the result is injected directly into the LLM prompt:

```python
# agent/nodes.py — faq_node

def faq_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return {"messages": [AIMessage(content="How can I help you today?")], "current_flow": "idle"}

    # Get the customer's question from the last message in state
    user_query = messages[-1].content
    logger.info(f"Querying FAQ database for: {user_query}")

    # VECTOR SEARCH: query_faq returns the single most similar FAQ document
    # Example: if user_query = "When do you open?"
    #   → embedding converts it to a 384-dim vector
    #   → ChromaDB finds hours.txt as the closest match
    #   → documents[0] = the full text of hours.txt
    documents, metadatas = query_faq(user_query, n_results=1)
    context = documents[0] if documents else "No FAQ document context found."

    if documents:
        # Log which FAQ document was matched (helps with debugging)
        logger.info(f"ChromaDB Match: {metadatas[0]['source']}")

    # RAG PROMPT: inject the retrieved FAQ text as context
    # The LLM now has the EXACT answer it needs, and is told to ONLY use this context.
    # This prevents hallucination — the LLM won't invent opening hours.
    prompt = (
        "You are a friendly and polite customer support agent. "
        "Answer the customer's question using ONLY the provided context. "
        "Keep your answer concise, friendly, and conversational since this is a voice call. "
        "Do not use bullet points or lists. Speak in natural, complete sentences.\n\n"
        f"Context:\n{context}\n\n"          # ← The retrieved FAQ text goes here
        f"Customer Question:\n{user_query}\n\n"
        "Agent Response:"
    )

    try:
        response = get_groq_llm().invoke(prompt)
        answer = response.content.strip()
    except Exception as e:
        logger.error(f"Error calling LLM for FAQ: {str(e)}")
        answer = "I'm sorry, I'm having trouble answering that question right now."

    return {
        "messages": [AIMessage(content=answer)],
        "current_flow": "idle"
    }
```

### Concrete Example: End-to-End FAQ Flow

**Customer says:** "What are your store hours?"

```
1. user_query = "What are your store hours?"

2. query_faq("What are your store hours?", n_results=1)
   → Embedding model converts query to vector: [0.23, -0.41, 0.18, ... 384 numbers]
   → ChromaDB compares to stored vectors:
       hours.txt    distance: 0.12  ← CLOSEST (most similar)
       location.txt distance: 0.67
       pricing.txt  distance: 0.74
       refunds.txt  distance: 0.81
   → Returns documents=["Our customer support is available Monday through Friday..."]
             metadatas=[{"source": "hours.txt"}]

3. context = "Our customer support is available Monday through Friday 
              from 9:00 AM to 6:00 PM Indian Standard Time (IST)..."

4. Prompt sent to Groq LLM:
   "You are a friendly support agent. Answer ONLY using this context:
    Context: Our customer support is available Monday through Friday 9 AM to 6 PM IST...
    Customer Question: What are your store hours?
    Agent Response:"

5. LLM response: "We're available Monday through Friday, from 9 AM to 6 PM
                  Indian Standard Time. We're closed on weekends and public holidays."

6. This text is returned as AIMessage, streamed to TTS, spoken to customer.
```

---

## Step 4: The Warm-Up Query — `agent/main.py`

```python
# agent/main.py — startup code

# Without pre-warming, the SentenceTransformer model loads on the FIRST FAQ query.
# Loading takes 6-9 seconds — during which the customer hears silence.
# By running a dummy query at startup, we force the model into RAM immediately.
# Subsequent queries are instant (< 50ms) because the model is already loaded.
logger.info("Pre-warming ChromaDB SentenceTransformer embedding model...")
try:
    from chroma_client import query_faq as _warmup_query
    _warmup_query("warmup", n_results=1)   # Dummy query — result is discarded
    logger.info("ChromaDB embedding model pre-warmed successfully.")
except Exception as _warmup_err:
    # Non-fatal: if this fails (e.g., chroma_db is empty), calls still work.
    # The first FAQ query will just be slow.
    logger.warning(f"ChromaDB pre-warm failed (non-fatal): {_warmup_err}")
```

---

## What the FAQ Files Actually Contain

```
agent/faq_docs/hours.txt:
"Our customer support is available Monday through Friday from 9:00 AM to 6:00 PM
Indian Standard Time (IST). We are closed on weekends and standard public holidays.
For urgent matters outside business hours, you can register a complaint and a support
ticket will be addressed the next business day morning."
```

These are the source documents for RAG. To add new knowledge:
1. Create a new `.txt` file in `agent/faq_docs/`
2. Run `python embed_documents.py` to embed and store it
3. The agent can now answer questions about that topic

---

## When to Use RAG vs. The General Chat Node

| Scenario | Which node handles it |
|----------|----------------------|
| "What are your hours?" | `faq_node` — vector search finds `hours.txt` |
| "Where are you located?" | `faq_node` — finds `location.txt` |
| "How much does X cost?" | `faq_node` — finds `pricing.txt` |
| "Can I get a refund?" | `faq_node` — finds `refunds.txt` |
| "Thanks, that's helpful!" | `general_chat_node` — no FAQ needed, just conversation |
| "How's your day going?" | `general_chat_node` — general conversation |
| "I need to book an appointment" | NOT `faq_node` → `classify_intent` routes to appointment |

The `classify_intent` LLM call in `router_node` decides whether a message goes to `faq_node`
or elsewhere. FAQs = questions about the company/service. Non-FAQs = actions to take.

---

*Next up → [07_FASTAPI_DEEPDIVE.md](./07_FASTAPI_DEEPDIVE.md)*
