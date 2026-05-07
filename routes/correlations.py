"""OSETA — Route heatmap de corrélation inter-sectorielle.

GET  /correlations/matrix          → heatmap prête pour Recharts
POST /correlations/refresh         → démarre le pipeline en background (master key requis)
GET  /correlations/pipeline-status → état courant du pipeline (master key requis)
"""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import CorrelationMatrixEntry, Sector
from models.enums import CorrelationMethod
from services.correlation_store import get_latest_matrix
from services.database import get_session
from services.pipeline import PipelineState, get_state, reset_for_run, run_pipeline

router = APIRouter(prefix="/correlations", tags=["correlations"])


# ─────────────────────── Schémas réponse ────────────────────────────────

class HeatmapCell(BaseModel):
    sector_a_code: str
    sector_b_code: str
    sector_a_name: str
    sector_b_name: str
    correlation: float
    p_value: float | None
    lag_days: int
    is_significant: bool
    window_days: int


class HeatmapResponse(BaseModel):
    sectors: list[str]          # codes ordonnés (axes x et y)
    cells: list[HeatmapCell]
    computed_at: datetime | None
    method: CorrelationMethod
    total_pairs: int


class RefreshStartedResponse(BaseModel):
    status: Literal["started", "already_running"]
    triggered_at: datetime | None


class PipelineStatusResponse(BaseModel):
    status: Literal["idle", "running", "success", "error"]
    step: str | None
    triggered_at: datetime | None
    finished_at: datetime | None
    etf_new: int | None
    fred_new: int | None
    computed: int | None
    skipped: int | None
    predictions: int | None
    error: str | None


# ─────────────────────── Helpers ─────────────────────────────────────────

async def _sector_map(
    session: AsyncSession,
    entries: list[CorrelationMatrixEntry],
) -> dict[int, Sector]:
    """Charge les secteurs référencés dans la matrice en une seule query."""
    from sqlalchemy import select

    ids = {e.sector_a_id for e in entries} | {e.sector_b_id for e in entries}
    if not ids:
        return {}
    rows = await session.execute(
        select(Sector).where(Sector.id.in_(ids))
    )
    return {s.id: s for s in rows.scalars().all()}


# ─────────────────────── Endpoints ───────────────────────────────────────

@router.get("/matrix", response_model=HeatmapResponse)
async def get_correlation_matrix(
    method: CorrelationMethod = Query(CorrelationMethod.PEARSON),
    min_correlation: float = Query(0.0, ge=0.0, le=1.0),
    lag_max: int = Query(60, ge=0, le=365),
    session: AsyncSession = Depends(get_session),
) -> HeatmapResponse:
    """Retourne la dernière matrice de corrélation formatée pour le heatmap.

    Filtre optionnel par corrélation minimale et lag maximum.
    """
    entries = await get_latest_matrix(session, method)

    if not entries:
        return HeatmapResponse(
            sectors=[],
            cells=[],
            computed_at=None,
            method=method,
            total_pairs=0,
        )

    sectors = await _sector_map(session, entries)
    computed_at = entries[0].computed_at

    cells: list[HeatmapCell] = []
    sector_codes: set[str] = set()

    for e in entries:
        sec_a = sectors.get(e.sector_a_id)
        sec_b = sectors.get(e.sector_b_id)
        if not sec_a or not sec_b:
            continue

        abs_corr = abs(float(e.correlation))
        if abs_corr < min_correlation:
            continue
        if e.lag_days > lag_max:
            continue

        sector_codes.add(sec_a.code)
        sector_codes.add(sec_b.code)

        cells.append(HeatmapCell(
            sector_a_code=sec_a.code,
            sector_b_code=sec_b.code,
            sector_a_name=sec_a.name,
            sector_b_name=sec_b.name,
            correlation=float(e.correlation),
            p_value=float(e.p_value) if e.p_value is not None else None,
            lag_days=e.lag_days,
            is_significant=(e.p_value is not None and float(e.p_value) < 0.05),
            window_days=e.window_days,
        ))

    return HeatmapResponse(
        sectors=sorted(sector_codes),
        cells=cells,
        computed_at=computed_at,
        method=method,
        total_pairs=len(cells),
    )


@router.post("/refresh", response_model=RefreshStartedResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    x_master_key: Annotated[str | None, Header()] = None,
    method: CorrelationMethod = Query(CorrelationMethod.PEARSON),
    window_days: int = Query(90, ge=30, le=365),
) -> RefreshStartedResponse:
    """Démarre le pipeline en background. Retourne immédiatement. Protégé par X-Master-Key."""
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid master key")

    state = get_state()
    if state.status == "running":
        return RefreshStartedResponse(status="already_running", triggered_at=state.triggered_at)

    now = datetime.utcnow()
    reset_for_run(now)
    background_tasks.add_task(run_pipeline, method, window_days)
    return RefreshStartedResponse(status="started", triggered_at=now)


@router.get("/pipeline-status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    x_master_key: Annotated[str | None, Header()] = None,
) -> PipelineStatusResponse:
    """Retourne l'état courant du pipeline. Protégé par X-Master-Key."""
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid master key")

    s = get_state()
    return PipelineStatusResponse(
        status=s.status,
        step=s.step,
        triggered_at=s.triggered_at,
        finished_at=s.finished_at,
        etf_new=s.etf_new,
        fred_new=s.fred_new,
        computed=s.computed,
        skipped=s.skipped,
        predictions=s.predictions,
        error=s.error,
    )
