"""OSETA — Health check endpoint."""

import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import ComponentStatus, HealthResponse
from services.database import get_session

router = APIRouter()
_started_at = time.time()


@router.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    """Vérifie la connectivité DB et retourne l'état global."""
    components: list[ComponentStatus] = []

    # DB check
    try:
        t0 = time.perf_counter()
        await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - t0) * 1000
        components.append(ComponentStatus(name="db", status="ok", latency_ms=round(latency, 2)))
    except Exception as exc:
        components.append(ComponentStatus(name="db", status="down", detail=str(exc)))

    overall = "ok" if all(c.status == "ok" for c in components) else "degraded"
    return HealthResponse(
        status=overall,
        version="0.1.0",
        environment="development",
        components=components,
        uptime_seconds=round(time.time() - _started_at, 1),
    )
