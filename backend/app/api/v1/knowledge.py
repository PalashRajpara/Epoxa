from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_supervisor
from app.repositories.knowledge_repo import knowledge_repo
from app.schemas.knowledge import KnowledgeQueryRequest, KnowledgeQueryResult
from app.schemas.auth import SupervisorContext

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & Retrieval"])

@router.post("/query", response_model=List[KnowledgeQueryResult], summary="Query grounded knowledge base chunks")
async def query_knowledge(
    req: KnowledgeQueryRequest,
    supervisor: SupervisorContext = Depends(get_current_supervisor),
    db: AsyncSession = Depends(get_db)
):
    results = await knowledge_repo.search_chunks(
        db, org_id=supervisor.organization_id, query=req.query, limit=req.limit
    )
    return [
        KnowledgeQueryResult(
            chunk_id=chunk.id,
            document_title=chunk.document.title if chunk.document else "FAQ",
            content=chunk.chunk_content,
            score=score
        )
        for chunk, score in results
    ]
