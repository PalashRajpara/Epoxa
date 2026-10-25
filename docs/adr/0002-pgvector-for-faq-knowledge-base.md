# ADR 0002: pgvector for FAQ Knowledge Base

## Status
Accepted

## Context
The prototype agent used local ChromaDB (`agent/chroma_db/`) with a local SQLite file. This violated worker statelessness: multiple container replicas could not share embeddings without local file synchronization, and deployments required stateful volumes.

## Decision
1. Migrate knowledge base storage to PostgreSQL using the `vector` extension (`pgvector`) in Supabase.
2. Store documents and chunks in relational tables:
   - `kb_documents`: `(id, organization_id, title, source_path, content_hash, is_active)`
   - `kb_chunks`: `(id, document_id, organization_id, content, embedding vector(384), position)`
3. Create an **HNSW** index with cosine distance (`vector_cosine_ops`) for sub-millisecond similarity search.
4. Keep the embedding model as `all-MiniLM-L6-v2` (384 dimensions). Pre-warm the embedding model and cache FAQ results in memory during worker startup to maintain low turn latencies.

## Alternatives Considered
- **Pinecone / Weaviate**: Rejected due to additional SaaS vendors, network hops, and cost when Supabase PostgreSQL already supports native pgvector.
- **Retaining ChromaDB**: Rejected because local disk dependence prevents horizontal worker autoscaling.

## Consequences
- Voice agent workers are completely stateless.
- FAQ ingestion is idempotent and centrally managed via `db/seeds/seed.py`.
