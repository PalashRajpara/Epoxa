import os
import chromadb
from chromadb.utils import embedding_functions

# Resolve directory path for ChromaDB storage
# Located in: agent/chroma_db/
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

# Pre-load ChromaDB client and embedding function globally at startup.
# Attempt to load from local cache first to avoid slow Hugging Face network check delay.
_client = chromadb.PersistentClient(path=DB_DIR)
try:
    _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2",
        local_files_only=True
    )
except Exception:
    _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

def get_chroma_client():
    return _client

def get_embedding_fn():
    return _embedding_fn

def get_or_create_collection():
    """
    Retrieves or creates the faq_collection vector storage.
    Automatically applies sentence-transformer local embeddings.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="faq_collection",
        embedding_function=get_embedding_fn()
    )

def query_faq(query_text: str, n_results: int = 1):
    """
    Queries ChromaDB vector store with the user's speech transcript.
    Returns lists of matched documents and metadatas.
    """
    collection = get_or_create_collection()
    
    # Query Chroma DB
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    # Parse output documents and metadata
    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    
    return documents, metadatas
