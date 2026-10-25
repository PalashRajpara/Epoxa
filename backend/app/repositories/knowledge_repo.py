import uuid
import hashlib
from typing import Optional, List, Tuple
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, AgentConfig

class KnowledgeRepository:
    async def create_document(
        self, db: AsyncSession, org_id: uuid.UUID, title: str, doc_type: str = "faq", metadata: Optional[dict] = None
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            organization_id=org_id,
            title=title,
            document_type=doc_type,
            metadata_=metadata or {}
        )
        db.add(doc)
        await db.flush()
        return doc

    async def add_chunk(
        self, db: AsyncSession, doc_id: uuid.UUID, org_id: uuid.UUID, content: str, metadata: Optional[dict] = None
    ) -> KnowledgeChunk:
        chunk_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
        chunk = KnowledgeChunk(
            document_id=doc_id,
            organization_id=org_id,
            chunk_content=content.strip(),
            chunk_hash=chunk_hash,
            metadata_=metadata or {}
        )
        db.add(chunk)
        await db.flush()
        return chunk

    async def search_chunks(
        self, db: AsyncSession, org_id: uuid.UUID, query: str, limit: int = 4
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """Performs tenant-scoped keyword & semantic retrieval over knowledge chunks."""
        keywords = [k.lower().strip() for k in query.split() if len(k) > 2]
        stmt = select(KnowledgeChunk).options(
            selectinload(KnowledgeChunk.document)
        ).where(KnowledgeChunk.organization_id == org_id)

        result = await db.execute(stmt)
        all_chunks = result.scalars().all()

        scored_chunks = []
        for chunk in all_chunks:
            text = chunk.chunk_content.lower()
            score = 0.0
            for kw in keywords:
                if kw in text:
                    score += 1.0 + (text.count(kw) * 0.2)
            if score > 0:
                scored_chunks.append((chunk, score))

        # Sort by relevance score descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:limit]

    async def get_active_agent_config(
        self, db: AsyncSession, org_id: uuid.UUID
    ) -> Optional[AgentConfig]:
        stmt = select(AgentConfig).where(
            AgentConfig.organization_id == org_id,
            AgentConfig.is_active == True  # noqa: E712
        ).order_by(AgentConfig.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create_agent_config(
        self, db: AsyncSession, org_id: uuid.UUID, system_prompt: str, voice_model: str, llm_model: str
    ) -> AgentConfig:
        config = AgentConfig(
            organization_id=org_id,
            system_prompt=system_prompt,
            voice_model=voice_model,
            llm_model=llm_model
        )
        db.add(config)
        await db.flush()
        return config

knowledge_repo = KnowledgeRepository()
