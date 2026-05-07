"""OSETA — Service génération prédictions depuis la matrice de corrélation.

Responsabilités :
  1. Charger les corrélations significatives (p<0.05, lag≥3j, |r|≥0.5)
  2. Appeler prompts/predict.py via LiteLLM (run_in_executor — synchrone)
  3. Résoudre sector_code → sector_id et persister les Prediction en DB
"""

import asyncio
from datetime import date
from functools import partial
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Prediction, Sector
from models.enums import CorrelationMethod
from prompts.predict import generate_predictions
from services.correlation_store import get_latest_matrix


_MIN_ABS_CORRELATION = 0.5
_MIN_LAG_DAYS = 3
_P_VALUE_THRESHOLD = 0.05


async def _load_sector_map(session: AsyncSession, ids: set[int]) -> dict[int, Sector]:
    """Charge les secteurs référencés en une seule query."""
    if not ids:
        return {}
    rows = await session.execute(select(Sector).where(Sector.id.in_(ids)))
    return {s.id: s for s in rows.scalars().all()}


async def _build_correlation_input(
    session: AsyncSession,
    method: CorrelationMethod,
) -> list[dict[str, Any]]:
    """Charge et filtre les corrélations significatives pour l'appel LLM."""
    entries = await get_latest_matrix(session, method)
    significant = [
        e for e in entries
        if e.p_value is not None
        and float(e.p_value) < _P_VALUE_THRESHOLD
        and e.lag_days >= _MIN_LAG_DAYS
        and abs(float(e.correlation)) >= _MIN_ABS_CORRELATION
    ]
    if not significant:
        return []

    ids = {e.sector_a_id for e in significant} | {e.sector_b_id for e in significant}
    sectors = await _load_sector_map(session, ids)

    result = []
    for e in sorted(significant, key=lambda x: abs(float(x.correlation)), reverse=True):
        sa = sectors.get(e.sector_a_id)
        sb = sectors.get(e.sector_b_id)
        if sa and sb:
            result.append({
                "sector_a_code": sa.code,
                "sector_b_code": sb.code,
                "sector_a_id": e.sector_a_id,
                "sector_b_id": e.sector_b_id,
                "r": float(e.correlation),
                "lag_days": e.lag_days,
                "p_value": float(e.p_value) if e.p_value is not None else None,
                "window_days": e.window_days,
            })
    return result


async def generate_and_store_predictions(
    session: AsyncSession,
    method: CorrelationMethod = CorrelationMethod.PEARSON,
    target_date: date | None = None,
) -> int:
    """Génère des prédictions LLM et les persiste en DB.

    Args:
        session: Session async SQLAlchemy.
        method: Méthode de corrélation source.
        target_date: Date d'analyse (défaut : aujourd'hui UTC).

    Returns:
        Nombre de prédictions écrites.
    """
    from config import settings

    today = target_date or date.today()
    correlations = await _build_correlation_input(session, method)

    if not correlations:
        logger.warning("predictor: no significant correlations — skipping prediction generation")
        return 0

    loop = asyncio.get_running_loop()
    output = await loop.run_in_executor(
        None,
        partial(generate_predictions, correlations=correlations, date_str=str(today)),
    )

    all_sectors = await session.execute(select(Sector))
    code_to_id: dict[str, int] = {s.code: s.id for s in all_sectors.scalars().all()}

    written = 0
    for item in output.predictions:
        sector_id = code_to_id.get(item.sector_code)
        if sector_id is None:
            logger.warning(f"predictor: unknown sector code '{item.sector_code}' — skipping")
            continue

        linked_sector_id = (
            code_to_id.get(item.linked_sector_code)
            if item.linked_sector_code
            else None
        )

        session.add(Prediction(
            sector_id=sector_id,
            linked_sector_id=linked_sector_id,
            prediction_type=item.prediction_type,
            horizon_days=item.horizon_days,
            confidence_score=item.confidence_score,
            predicted_direction=item.predicted_direction,
            predicted_magnitude=item.predicted_magnitude,
            features_used={
                "rationale": item.rationale,
                "source": "correlation_matrix",
                "method": str(method),
            },
            model_version=f"litellm/{settings.litellm_default_model}",
        ))
        written += 1

    if written:
        await session.commit()
        logger.info(f"predictor: {written} predictions written for {today}")

    return written
