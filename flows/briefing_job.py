"""OSETA — Flow Prefect : génération du briefing exécutif quotidien.

Schedule : tous les jours à 06:00 UTC (après la collecte de 05:00 UTC).
Génère briefing + détection de signaux faibles.
"""

from datetime import date, datetime, timezone

from loguru import logger
from prefect import flow, task

from services.database import AsyncSessionLocal
from services.publisher import detect_daily_signals, generate_daily_briefing


# ─────────────────────── Tasks ───────────────────────────────────────────

@task(name="generate-briefing", retries=2, retry_delay_seconds=60)
async def task_generate_briefing(
    target_date: str,
    sector_focus: str | None = None,
) -> dict:
    """Génère le briefing exécutif quotidien."""
    parsed_date = date.fromisoformat(target_date)
    async with AsyncSessionLocal() as session:
        briefing = await generate_daily_briefing(
            session, target_date=parsed_date, sector_focus=sector_focus
        )

    if briefing is None:
        logger.warning(f"No briefing generated for {target_date} — insufficient articles")
        return {"status": "skipped", "reason": "insufficient_articles"}

    return {
        "status": "ok",
        "headline": briefing.headline,
        "key_implications_count": len(briefing.key_implications),
        "top_technologies": briefing.top_technologies,
        "risk_alert": briefing.risk_alert,
    }


@task(name="detect-signals", retries=1, retry_delay_seconds=30)
async def task_detect_signals(
    target_date: str,
    sector_focus: str | None = None,
) -> dict:
    """Détecte les signaux faibles cross-articles du jour."""
    parsed_date = date.fromisoformat(target_date)
    async with AsyncSessionLocal() as session:
        result = await detect_daily_signals(
            session, target_date=parsed_date, sector_focus=sector_focus
        )

    if result is None:
        logger.warning(f"No signals detected for {target_date} — insufficient articles")
        return {"status": "skipped", "signals_count": 0}

    return {
        "status": "ok",
        "signals_count": len(result.signals),
        "dominant_theme": result.dominant_theme,
        "analysis_confidence": result.analysis_confidence,
        "signals": [
            {"name": s.signal_name, "type": s.signal_type, "sectors": s.sector_codes}
            for s in result.signals
        ],
    }


# ─────────────────────── Flow principal ──────────────────────────────────

@flow(
    name="briefing-daily",
    description="Generate daily executive briefing and detect weak signals.",
    log_prints=True,
)
async def briefing_flow(
    target_date: str | None = None,
    sector_focus: str | None = None,
) -> dict:
    """Flow quotidien : briefing exécutif + détection signaux faibles.

    Args:
        target_date: Date cible au format 'YYYY-MM-DD'. Défaut : aujourd'hui UTC.
        sector_focus: Secteur à mettre en avant (optionnel).
    """
    today_str = target_date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    started_at = datetime.now(tz=timezone.utc)
    logger.info(f"Briefing flow started for {today_str}")

    briefing_result = await task_generate_briefing(today_str, sector_focus)
    signals_result = await task_detect_signals(today_str, sector_focus)

    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    logger.info(f"Briefing flow done in {elapsed:.1f}s for {today_str}")

    return {
        "date": today_str,
        "elapsed_seconds": elapsed,
        "briefing": briefing_result,
        "signals": signals_result,
    }


# ─────────────────────── Deployment ──────────────────────────────────────

def build_deployment() -> None:
    """Crée le déploiement Prefect avec schedule quotidien 06:00 UTC.

    Usage : python -m flows.briefing_job
    """
    briefing_flow.serve(
        name="briefing-daily-prod",
        cron="0 6 * * *",
        parameters={"sector_focus": None},
        tags=["oseta", "briefing", "daily"],
    )
    logger.info("Deployment 'briefing-daily-prod' registered in Prefect.")


if __name__ == "__main__":
    build_deployment()
