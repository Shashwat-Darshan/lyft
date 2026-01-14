"""Health check endpoints."""
from fastapi import APIRouter, status, Response
from app.config import settings
from app.models import check_db_ready
import json

router = APIRouter()


@router.get("/health/live")
async def liveness():
    """Liveness probe - always returns 200 once app is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """
    Readiness probe - returns 200 only if:
    - DB is reachable and schema is applied
    - WEBHOOK_SECRET is set
    """
    if not settings.validate_webhook_secret():
        return Response(
            content=json.dumps({"status": "not ready", "reason": "WEBHOOK_SECRET not set"}),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    if not check_db_ready():
        return Response(
            content=json.dumps({"status": "not ready", "reason": "database not ready"}),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    return {"status": "ready"}

