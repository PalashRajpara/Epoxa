import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.base import GUID, TimestampMixin

class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="faq", nullable=False)
    # Types: faq, policy, guide
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)

    # Relationships
    chunks: Mapped[List["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")

class AgentConfig(Base, TimestampMixin):
    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    voice_model: Mapped[str] = mapped_column(String(100), default="aura-asteria-en", nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), default="llama-3.3-70b-versatile", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
