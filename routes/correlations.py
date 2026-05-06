"""OSETA — Route heatmap de corrélation inter-sectorielle.

GET  /correlations/matrix  → heatmap prête pour Recharts
POST /correlations/refresh → déclenche recalcul (master key requis)
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import CorrelationMatrixEntry, Sector
from models.enums import CorrelationMethod
from services.correlation_store import get_latest_matrix, run_correlation_job
from services.database import get_session

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


class RefreshResponse(BaseModel):
    computed: int
    skipped: int
    triggered_at: datetime


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


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_refresh(
    x_master_key: Annotated[str | None, Header()] = None,
    method: CorrelationMethod = Query(CorrelationMethod.PEARSON),
    window_days: int = Query(90, ge=30, le=365),
    session: AsyncSession = Depends(get_session),
) -> RefreshResponse:
    """Déclenche un recalcul immédiat de la matrice. Protégé par X-Master-Key."""
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid master key")

    result = await run_correlation_job(session, window_days=window_days, method=method)
    return RefreshResponse(
        computed=result["computed"],
        skipped=result["skipped"],
        triggered_at=datetime.utcnow(),
    )
