"""OSETA — Flow Prefect : recalcul hebdomadaire de la matrice de corrélation.

Schedule : tous les lundis à 04:00 UTC (marchés fermés, données stables).
Peut aussi être déclenché manuellement via POST /correlations/refresh.
"""

from datetime import datetime, timezone

from loguru import logger
from prefect import flow, task

from models.enums import CorrelationMethod
from services.correlation_store import run_correlation_job
from services.data_fetcher import fetch_and_store_etfs, fetch_and_store_fred
from services.database import AsyncSessionLocal


# ─────────────────────── Tasks ───────────────────────────────────────────

@task(name="fetch-etf-data", retries=2, retry_delay_seconds=60)
async def task_fetch_etfs() -> dict[str, int]:
    """Télécharge les 9 ETFs SPDR via Alpha Vantage (~2 min à cause du rate limit)."""
    async with AsyncSessionLocal() as session:
        return await fetch_and_store_etfs(session)


@task(name="fetch-fred-data", retries=2, retry_delay_seconds=30)
async def task_fetch_fred() -> dict[str, int]:
    """Télécharge les 4 indicateurs macro FRED."""
    async with AsyncSessionLocal() as session:
        return await fetch_and_store_fred(session)


@task(name="compute-correlation-matrix", retries=1, retry_delay_seconds=30)
async def task_compute_matrix(
    window_days: int,
    method: CorrelationMethod,
) -> dict[str, int]:
    """Calcule et persiste la matrice de corrélation."""
    async with AsyncSessionLocal() as session:
        return await run_correlation_job(session, window_days=window_days, method=method)


# ─────────────────────── Flow principal ──────────────────────────────────

@flow(
    name="correlation-weekly",
    description="Fetch ETF + FRED data, then compute cross-sector correlation matrix.",
    log_prints=True,
)
async def correlation_flow(
    window_days: int = 90,
    method: CorrelationMethod = CorrelationMethod.PEARSON,
) -> dict[str, object]:
    """Flow hebdomadaire complet : collecte → corrélation → persistance.

    Étapes :
      1. Fetch 9 ETFs SPDR (Alpha Vantage, ~2 min)
      2. Fetch 4 indicateurs FRED (sync via executor)
      3. Calcule la matrice Pearson sur window_days jours
    """
    started_at = datetime.now(tz=timezone.utc)
    logger.info(f"Correlation flow started at {started_at.isoformat()}")

    # Étapes 1 & 2 : collecte des données (séquentiel pour respecter le rate limit AV)
    etf_counts = await task_fetch_etfs()
    fred_counts = await task_fetch_fred()

    etf_new = sum(etf_counts.values())
    fred_new = sum(fred_counts.values())
    logger.info(f"Data collected — ETF new points: {etf_new}, FRED new points: {fred_new}")

    # Étape 3 : calcul de la matrice
    matrix_result = await task_compute_matrix(window_days, method)

    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    logger.info(f"Flow done in {elapsed:.1f}s — {matrix_result['computed']} pairs computed")

    return {
        "etf_new_points": etf_new,
        "fred_new_points": fred_new,
        "matrix_computed": matrix_result["computed"],
        "matrix_skipped": matrix_result["skipped"],
        "elapsed_seconds": elapsed,
    }


# ─────────────────────── Deployment ──────────────────────────────────────

def build_deployment() -> None:
    """Crée le déploiement Prefect avec schedule hebdomadaire.

    Usage : python -m flows.correlation_job
    """
    correlation_flow.serve(
        name="correlation-weekly-prod",
        cron="0 4 * * 1",   # lundi 04:00 UTC
        parameters={"window_days": 90, "method": CorrelationMethod.PEARSON},
        tags=["oseta", "correlation", "weekly"],
    )
    logger.info("Deployment 'correlation-weekly-prod' registered in Prefect.")


if __name__ == "__main__":
    build_deployment()
