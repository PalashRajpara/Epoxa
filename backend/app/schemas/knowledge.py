import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import BaseSchema

class KnowledgeDocumentCreate(BaseModel):
    title: str
    document_type: str = "faq"
    content: str
    metadata: Dict[str, Any] = {}

class KnowledgeChunkRead(BaseSchema):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_content: str
    metadata: Dict[str, Any]
    created_at: datetime

class KnowledgeDocumentRead(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    document_type: str
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    chunks: Optional[List[KnowledgeChunkRead]] = None

class KnowledgeQueryRequest(BaseModel):
    query: str
    limit: int = 4

class KnowledgeQueryResult(BaseModel):
    chunk_id: uuid.UUID
    document_title: str
    content: str
    score: float
