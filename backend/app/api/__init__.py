from fastapi import APIRouter

from app.api.routes_admin import router as admin_router
from app.api.routes_ai import router as ai_router
from app.api.routes_auth import router as auth_router
from app.api.routes_check import router as check_router
from app.api.routes_dictionary import router as dictionary_router
from app.api.routes_export import router as export_router
from app.api.routes_feedback import router as feedback_router
from app.api.routes_health import router as health_router
from app.api.routes_import import router as import_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(check_router)
api_router.include_router(ai_router)
api_router.include_router(dictionary_router)
api_router.include_router(import_router)
api_router.include_router(export_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_router)
