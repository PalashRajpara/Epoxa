import uuid
from typing import Optional, List
from sqlalchemy import String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.base import GUID, TimestampMixin, utc_now

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    businesses: Mapped[List["Business"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    memberships: Mapped[List["OrganizationMembership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class Business(Base, TimestampMixin):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="businesses")
    locations: Mapped[List["BusinessLocation"]] = relationship(back_populates="business", cascade="all, delete-orphan")

class BusinessLocation(Base, TimestampMixin):
    __tablename__ = "business_locations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="locations")

class SupervisorProfile(Base, TimestampMixin):
    """Internal supervisor record linked 1-to-1 with Supabase Auth User ID."""
    __tablename__ = "supervisor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)  # Matches auth.users.id
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(back_populates="supervisor", cascade="all, delete-orphan")

class OrganizationMembership(Base, TimestampMixin):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "supervisor_id", name="uq_org_membership"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("supervisor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="supervisor", nullable=False)  # admin, supervisor
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    supervisor: Mapped["SupervisorProfile"] = relationship(back_populates="memberships")

class BusinessMembership(Base, TimestampMixin):
    __tablename__ = "business_memberships"
    __table_args__ = (
        UniqueConstraint("business_id", "supervisor_id", name="uq_biz_membership"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("supervisor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="supervisor", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
