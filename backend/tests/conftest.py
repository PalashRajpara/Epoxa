import pytest
import uuid
import sys
import os
from typing import AsyncGenerator
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import Base
from app.api.deps import get_db, get_current_supervisor
from app.main import app
from app.models.tenant import Organization, SupervisorProfile, OrganizationMembership
from app.schemas.auth import SupervisorContext

# Test database in memory
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def org_a(db_session: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        name="Tenant A Corp",
        slug="tenant-a",
        status="active"
    )
    db_session.add(org)
    await db_session.flush()
    return org

@pytest.fixture
async def org_b(db_session: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        name="Tenant B Corp",
        slug="tenant-b",
        status="active"
    )
    db_session.add(org)
    await db_session.flush()
    return org

@pytest.fixture
async def supervisor_a(db_session: AsyncSession, org_a: Organization) -> SupervisorProfile:
    from app.core.security import get_password_hash
    sup = SupervisorProfile(
        id=uuid.UUID("11111111-0000-0000-0000-000000000001"),
        email="sup_a@tenant-a.com",
        full_name="Supervisor A",
        password_hash=get_password_hash("ValidPass123!"),
        status="active"
    )
    db_session.add(sup)
    await db_session.flush()
    mem = OrganizationMembership(
        organization_id=org_a.id,
        supervisor_id=sup.id,
        role="supervisor"
    )
    db_session.add(mem)
    await db_session.flush()
    return sup

@pytest.fixture
async def client(db_session: AsyncSession, supervisor_a: SupervisorProfile, org_a: Organization) -> AsyncGenerator[httpx.AsyncClient, None]:
    # Dependency overrides
    async def override_get_db():
        yield db_session

    async def override_current_supervisor():
        return SupervisorContext(
            user_id=supervisor_a.id,
            email=supervisor_a.email,
            full_name=supervisor_a.full_name,
            organization_id=org_a.id,
            role="supervisor"
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_supervisor] = override_current_supervisor

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
