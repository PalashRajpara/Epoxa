import os
from chroma_client import get_or_create_collection

# Define path to raw FAQ documents
FAQ_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq_docs")

def embed_faq_documents():
    """
    Reads all text documents in the 'faq_docs' directory,
    generates embeddings, and stores them in the ChromaDB collection.
    """
    collection = get_or_create_collection()
    
    # Check if the folder exists
    if not os.path.exists(FAQ_DOCS_DIR):
        print(f"Directory {FAQ_DOCS_DIR} not found. Please create it first.")
        return
        
    # Get all .txt files
    files = [f for f in os.listdir(FAQ_DOCS_DIR) if f.endswith(".txt")]
    if not files:
        print(f"No FAQ text files found in {FAQ_DOCS_DIR}.")
        return
        
    documents = []
    ids = []
    metadatas = []
    
    for file_name in files:
        file_path = os.path.join(FAQ_DOCS_DIR, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        if content:
            documents.append(content)
            # Use file name without extension as id
            doc_id = os.path.splitext(file_name)[0]
            ids.append(doc_id)
            metadatas.append({"source": file_name})
            print(f"Loaded: {file_name} ({len(content)} chars)")
            
    if documents:
        # Upsert documents to prevent duplicates
        collection.upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        print(f"Successfully embedded and stored {len(documents)} documents in ChromaDB!")
    else:
        print("No document content to insert.")

if __name__ == "__main__":
    print("Starting document embedding process...")
    embed_faq_documents()
