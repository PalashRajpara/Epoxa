"""
Knowledge Base Service for semantic vector retrieval over FAQ chunks with in-memory caching.
Implements Decision D5 (pgvector in Supabase replacing local ChromaDB, 384 dimensions).
"""

import hashlib
import uuid
from typing import Dict, List, Optional, Tuple
from epoxa_core.models.entities import KBChunk, KBDocument
from epoxa_core.uow import UnitOfWork


class KBService:
    """Manages FAQ vector search and document ingestion with local pre-warmed caching."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        # In-memory query cache: maps query hash -> top matched chunk content
        self._cache: Dict[str, str] = {}

    def _query_key(self, organization_id: uuid.UUID, query: str) -> str:
        h = hashlib.sha256(f"{organization_id}:{query.strip().lower()}".encode()).hexdigest()
        return h

    async def search_faq(
        self,
        organization_id: uuid.UUID,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 1,
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """Searches FAQ chunks using cached vector results or repository cosine similarity."""
        cache_key = self._query_key(organization_id, query_text)
        if cache_key in self._cache:
            cached_content = self._cache[cache_key]
            return [cached_content], [{"source": "cache"}]

        if query_embedding:
            chunks = await self.uow.kb.search_similar(organization_id, query_embedding, limit=limit)
        else:
            # Fallback list if embedding not yet generated
            chunks = await self.uow.kb.list_all(limit=limit)

        if not chunks:
            return ["No matching FAQ document found."], []

        matched_texts = [chunk.content for chunk in chunks]
        metas = [{"chunk_id": str(chunk.id), "source": "pgvector"} for chunk in chunks]

        # Cache top result
        if matched_texts:
            self._cache[cache_key] = matched_texts[0]

        return matched_texts, metas

    def clear_cache(self) -> None:
        """Clears the in-memory retrieval cache."""
        self._cache.clear()
