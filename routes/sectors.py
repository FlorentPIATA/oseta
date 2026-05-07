"""OSETA — Routes secteurs.

Endpoints :
  GET  /sectors                          → liste tous les secteurs
  POST /sectors                          → crée un secteur (X-Master-Key requis)
  GET  /sectors/{sector_id}              → détail d'un secteur
  GET  /sectors/{sector_id}/correlations → corrélations d'un secteur
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import CorrelationMatrixEntry, Sector
from models.enums import SectorLevel
from models.schemas import CorrelationResult, SectorCreate, SectorRead
from services.database import get_session

router = APIRouter()


@router.get("", response_model=list[SectorRead])
async def list_sectors(
    level: SectorLevel | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[SectorRead]:
    """Liste tous les secteurs, filtrables par niveau (macro/meso/micro)."""
    q = select(Sector).order_by(Sector.level, Sector.name)
    if level is not None:
        q = q.where(Sector.level == str(level))
    rows = await session.scalars(q)
    return [SectorRead.model_validate(s) for s in rows.all()]


@router.post("", response_model=SectorRead, status_code=status.HTTP_201_CREATED)
async def create_sector(
    payload: SectorCreate,
    x_master_key: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> SectorRead:
    """Crée un nouveau secteur. Protégé par X-Master-Key."""
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid master key")

    existing = await session.scalar(select(Sector.id).where(Sector.code == payload.code))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sector with code '{payload.code}' already exists",
        )

    sector = Sector(
        code=payload.code,
        name=payload.name,
        level=str(payload.level),
        parent_id=payload.parent_id,
    )
    session.add(sector)
    await session.commit()
    await session.refresh(sector)
    return SectorRead.model_validate(sector)


@router.delete("/{sector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sector(
    sector_id: int,
    x_master_key: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Supprime un secteur. Protégé par X-Master-Key."""
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid master key")

    sector = await session.get(Sector, sector_id)
    if sector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sector {sector_id} not found")

    await session.delete(sector)
    await session.commit()


@router.get("/{sector_id}", response_model=SectorRead)
async def get_sector(
    sector_id: int,
    session: AsyncSession = Depends(get_session),
) -> SectorRead:
    """Détail d'un secteur par ID."""
    sector = await session.get(Sector, sector_id)
    if sector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sector {sector_id} not found")
    return SectorRead.model_validate(sector)


@router.get("/{sector_id}/correlations", response_model=list[CorrelationResult])
async def get_sector_correlations(
    sector_id: int,
    min_correlation: float = Query(0.3, ge=0.0, le=1.0),
    session: AsyncSession = Depends(get_session),
) -> list[CorrelationResult]:
    """Retourne les corrélations significatives pour un secteur (depuis la dernière matrice calculée).

    Args:
        sector_id: ID du secteur source.
        min_correlation: Valeur absolue minimale de corrélation à retourner.
    """
    sector = await session.get(Sector, sector_id)
    if sector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sector {sector_id} not found")

    # Récupère les entrées de la dernière matrice impliquant ce secteur
    latest_q = (
        select(CorrelationMatrixEntry.computed_at)
        .order_by(CorrelationMatrixEntry.computed_at.desc())
        .limit(1)
    )
    latest_ts = await session.scalar(latest_q)
    if latest_ts is None:
        return []

    q = (
        select(CorrelationMatrixEntry, Sector)
        .where(CorrelationMatrixEntry.computed_at == latest_ts)
        .where(
            (CorrelationMatrixEntry.sector_a_id == sector_id)
            | (CorrelationMatrixEntry.sector_b_id == sector_id)
        )
    )
    rows = await session.execute(q)

    results: list[CorrelationResult] = []
    for (entry, _) in rows.all():
        abs_corr = float(abs(entry.correlation))
        if abs_corr < min_correlation:
            continue

        if entry.sector_a_id == sector_id:
            other_id = entry.sector_b_id
        else:
            other_id = entry.sector_a_id

        other_sector = await session.get(Sector, other_id)
        if other_sector is None:
            continue

        from models.enums import CorrelationMethod, LinkType
        results.append(CorrelationResult(
            source_sector_id=sector_id,
            target_sector_id=other_id,
            source_sector_name=sector.name,
            target_sector_name=other_sector.name,
            correlation_coeff=float(entry.correlation),
            lag_days=entry.lag_days or 0,
            strength=abs_corr,
            method=CorrelationMethod(entry.method),
            confidence=1.0 - float(entry.p_value or 0.05),
            is_significant=(entry.p_value is not None and float(entry.p_value) < 0.05),
            link_type=LinkType.MACRO,
            p_value=float(entry.p_value) if entry.p_value is not None else None,
            computed_at=entry.computed_at,
        ))

    results.sort(key=lambda r: abs(r.correlation_coeff), reverse=True)
    return results
