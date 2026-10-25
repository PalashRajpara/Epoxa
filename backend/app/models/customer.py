import uuid
from typing import Optional, Dict, Any
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.base import GUID, TimestampMixin

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

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

    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Extra customer notes / synthetic attributes
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
