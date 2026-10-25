from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

T = TypeVar("T")

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    livekit: str
    deepgram: str
    groq: str
    timestamp: datetime

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    correlation_id: Optional[str] = None
