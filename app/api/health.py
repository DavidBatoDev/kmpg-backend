from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "academic-context-api",
        "env": settings.app_env,
        "supabase_configured": settings.supabase_configured,
    }
