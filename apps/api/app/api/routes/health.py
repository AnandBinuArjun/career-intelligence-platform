from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "career-intelligence-api", "version": "1.0.0"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, Any]:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    if settings.storage_backend == "local":
        checks["storage"] = "ok (local)"
    else:
        checks["storage"] = "configured (s3)"

    checks["ai_routing"] = settings.ai_routing_mode
    overall = "ok" if checks["database"] == "ok" else "degraded"
    return {"status": overall, "checks": checks}
