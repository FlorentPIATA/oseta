"""OSETA — Routes prédictions + track record.

Endpoints :
  GET   /predictions                        → liste paginée avec filtres
  GET   /predictions/{prediction_id}        → détail d'une prédiction
  PATCH /predictions/{prediction_id}/realize → marque comme réalisée (track record)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Prediction, Sector
from models.enums import PredictionStatus
from models.schemas import PredictionRead
from services.database import get_session

router = APIRouter()


async def _enrich(
    session: AsyncSession,
    preds: list[Prediction],
) -> list[PredictionRead]:
    """Batch-loads sector codes and attaches them to PredictionRead objects."""
    if not preds:
        return []
    ids = {p.sector_id for p in preds} | {p.linked_sector_id for p in preds if p.linked_sector_id}
    rows = await session.execute(select(Sector).where(Sector.id.in_(ids)))
    code_map: dict[int, str] = {s.id: s.code for s in rows.scalars().all()}

    result = []
    for p in preds:
        data = {
            "id": p.id,
            "sector_id": p.sector_id,
            "sector_code": code_map.get(p.sector_id),
            "linked_sector_id": p.linked_sector_id,
            "linked_sector_code": code_map.get(p.linked_sector_id) if p.linked_sector_id else None,
            "prediction_type": p.prediction_type,
            "horizon_days": p.horizon_days,
            "confidence_score": p.confidence_score,
            "predicted_direction": p.predicted_direction,
            "predicted_magnitude": p.predicted_magnitude,
            "status": p.status,
            "realized_at": p.realized_at,
            "created_at": p.created_at,
        }
        result.append(PredictionRead.model_validate(data))
    return result


@router.get("", response_model=list[PredictionRead])
async def list_predictions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    pred_status: PredictionStatus | None = Query(None, alias="status"),
    sector_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[PredictionRead]:
    """Liste paginée des prédictions avec filtres optionnels."""
    q = select(Prediction).order_by(Prediction.created_at.desc())

    if pred_status is not None:
        q = q.where(Prediction.status == str(pred_status))
    if sector_id is not None:
        q = q.where(Prediction.sector_id == sector_id)

    rows = await session.scalars(q.offset(skip).limit(limit))
    return await _enrich(session, list(rows.all()))


@router.get("/track-record")
async def get_track_record(
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Retourne le track record global des prédictions (taux de réussite par statut)."""
    total = await session.scalar(select(func.count()).select_from(Prediction))
    realized = await session.scalar(
        select(func.count()).select_from(Prediction).where(
            Prediction.status == str(PredictionStatus.REALIZED)
        )
    )
    partial = await session.scalar(
        select(func.count()).select_from(Prediction).where(
            Prediction.status == str(PredictionStatus.PARTIAL)
        )
    )
    failed = await session.scalar(
        select(func.count()).select_from(Prediction).where(
            Prediction.status == str(PredictionStatus.FAILED)
        )
    )
    pending = await session.scalar(
        select(func.count()).select_from(Prediction).where(
            Prediction.status == str(PredictionStatus.PENDING)
        )
    )

    settled = (realized or 0) + (partial or 0) + (failed or 0)
    accuracy = round((realized or 0) / settled, 3) if settled > 0 else None

    return {
        "total": total or 0,
        "pending": pending or 0,
        "realized": realized or 0,
        "partial": partial or 0,
        "failed": failed or 0,
        "accuracy": accuracy,
    }


@router.get("/{prediction_id}", response_model=PredictionRead)
async def get_prediction(
    prediction_id: int,
    session: AsyncSession = Depends(get_session),
) -> PredictionRead:
    """Détail d'une prédiction par ID."""
    pred = await session.get(Prediction, prediction_id)
    if pred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction {prediction_id} not found",
        )
    enriched = await _enrich(session, [pred])
    return enriched[0]


@router.patch("/{prediction_id}/realize", response_model=PredictionRead)
async def realize_prediction(
    prediction_id: int,
    outcome: PredictionStatus = Query(..., description="realized | partial | failed"),
    x_master_key: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> PredictionRead:
    """Marque une prédiction comme réalisée/partielle/échouée (track record).

    Seuls les statuts terminaux sont acceptés (pas 'pending').
    Protégé par X-Master-Key.
    """
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid master key")

    if outcome == PredictionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set outcome to 'pending' — use realized, partial, or failed",
        )

    pred = await session.get(Prediction, prediction_id)
    if pred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction {prediction_id} not found",
        )

    if pred.status != str(PredictionStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prediction {prediction_id} is already settled (status: {pred.status})",
        )

    from datetime import datetime, timezone
    pred.status = str(outcome)
    pred.realized_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(pred)
    enriched = await _enrich(session, [pred])
    return enriched[0]
