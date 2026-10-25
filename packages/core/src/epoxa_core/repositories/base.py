"""
Generic base repository with standard asynchronous persistence operations.
"""

from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from epoxa_core.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository implementing standard CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: Any) -> Optional[ModelType]:
        """Fetches an entity by primary key."""
        result = await self.session.get(self.model, entity_id)
        return result

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Lists entities with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add(self, entity: ModelType) -> ModelType:
        """Stages an entity for insertion."""
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Deletes an entity."""
        await self.session.delete(entity)

    async def flush(self) -> None:
        """Flushes pending changes to the database."""
        await self.session.flush()
