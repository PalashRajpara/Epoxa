from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.voice import router as voice_router
from app.api.v1.calls import router as calls_router
from app.api.v1.customers import router as customers_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.knowledge import router as knowledge_router

api_v1_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(voice_router)
api_v1_router.include_router(calls_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(tickets_router)
api_v1_router.include_router(knowledge_router)
