"""API routes package for myoneAI Web Dashboard (Phase 11)."""

from fastapi import APIRouter

from web.api.routes.activity import router as activity_router
from web.api.routes.assistant import router as assistant_router
from web.api.routes.chat import router as chat_router
from web.api.routes.memory import router as memory_router
from web.api.routes.notes import router as notes_router
from web.api.routes.reminders import router as reminders_router
from web.api.routes.settings import router as settings_router
from web.api.routes.system import router as system_router
from web.api.routes.tasks import router as tasks_router

api_router = APIRouter(prefix="/api")

api_router.include_router(system_router)
api_router.include_router(assistant_router)
api_router.include_router(chat_router)
api_router.include_router(memory_router)
api_router.include_router(tasks_router)
api_router.include_router(reminders_router)
api_router.include_router(notes_router)
api_router.include_router(activity_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
