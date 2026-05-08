"""OSETA — Background pipeline : ETF fetch + FRED fetch + corrélation.

État en mémoire (singleton). Conçu pour être déclenché via BackgroundTasks FastAPI.
Single-worker assumption (Render free tier) — pas de verrou distribué nécessaire.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from loguru import logger

from models.enums import CorrelationMethod
from services.correlation_store import run_correlation_job
from services.data_fetcher import fetch_and_store_etfs, fetch_and_store_fred
from services.database import AsyncSessionLocal
from services.predictor import generate_and_store_predictions


@dataclass
class PipelineState:
    """État courant du pipeline. Muté en place par run_pipeline()."""

    status: Literal["idle", "running", "success", "error"] = "idle"
    step: str | None = None
    triggered_at: datetime | None = None
    finished_at: datetime | None = None
    etf_new: int | None = None
    etf_errors: int | None = None
    fred_new: int | None = None
    computed: int | None = None
    skipped: int | None = None
    predictions: int | None = None
    error: str | None = None


_state = PipelineState()


def get_state() -> PipelineState:
    """Retourne l'état courant (lecture seule pour les routes)."""
    return _state


def reset_for_run(triggered_at: datetime) -> None:
    """Prépare l'état avant un nouveau run."""
    _state.status = "running"
    _state.step = None
    _state.triggered_at = triggered_at
    _state.finished_at = None
    _state.etf_new = None
    _state.etf_errors = None
    _state.fred_new = None
    _state.computed = None
    _state.skipped = None
    _state.predictions = None
    _state.error = None


async def run_pipeline(
    method: CorrelationMethod = CorrelationMethod.PEARSON,
    window_days: int = 90,
) -> None:
    """Exécute le pipeline complet : ETF → FRED → corrélations → prédictions.

    Modifie _state en place. Appelé via BackgroundTasks (ne bloque pas la requête).
    Conserve le step actif en cas d'erreur pour que le frontend sache où ça a échoué.
    """
    try:
        _state.step = "fetching_etfs"
        logger.info("Pipeline: fetching ETFs")
        async with AsyncSessionLocal() as session:
            etf_counts = await fetch_and_store_etfs(session)
        _state.etf_new = sum(etf_counts.values())
        logger.info(f"Pipeline: ETFs done ({_state.etf_new} new points)")

        _state.step = "fetching_fred"
        logger.info("Pipeline: fetching FRED")
        async with AsyncSessionLocal() as session:
            fred_counts = await fetch_and_store_fred(session)
        _state.fred_new = sum(fred_counts.values())
        logger.info(f"Pipeline: FRED done ({_state.fred_new} new points)")

        _state.step = "computing"
        logger.info("Pipeline: computing correlations")
        async with AsyncSessionLocal() as session:
            result = await run_correlation_job(session, window_days, method)
        _state.computed = result["computed"]
        _state.skipped = result["skipped"]
        logger.info(f"Pipeline: correlations done ({_state.computed} pairs)")

        _state.step = "predicting"
        logger.info("Pipeline: generating predictions")
        async with AsyncSessionLocal() as session:
            _state.predictions = await generate_and_store_predictions(session, method)
        logger.info(f"Pipeline: predictions done ({_state.predictions} written)")

        _state.status = "success"
        _state.step = None
        _state.finished_at = datetime.utcnow()
        logger.info("Pipeline complete")

    except Exception as exc:
        _state.status = "error"
        _state.error = str(exc)
        _state.finished_at = datetime.utcnow()
        logger.error(f"Pipeline failed at step={_state.step}: {exc}")
