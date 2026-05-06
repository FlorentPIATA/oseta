"""OSETA — Flow Prefect : pipeline quotidien principal.

Schedule : tous les jours à 05:00 UTC.
Pipeline : collect → analyze (batch) → (briefing_flow s'enchaîne à 06:00 UTC)

Ce flow ne génère pas le briefing — c'est briefing_job.py qui s'en charge.
"""

from datetime import datetime, timezone

from loguru import logger
from prefect import flow, task

from models.enums import ArticleStatus
from services.analyzer import analyze_article
from services.collector import collect_sector_articles
from services.database import AsyncSessionLocal


_ANALYZE_BATCH_SIZE = 50


# ─────────────────────── Tasks ───────────────────────────────────────────

@task(name="collect-articles", retries=2, retry_delay_seconds=60)
async def task_collect(sectors: list[str] | None = None) -> dict[str, int]:
    """Collecte des articles pour tous les secteurs (Brave + EventRegistry)."""
    async with AsyncSessionLocal() as session:
        return await collect_sector_articles(session, sectors=sectors)


@task(name="analyze-batch", retries=1, retry_delay_seconds=30)
async def task_analyze_batch(article_ids: list[int]) -> dict[str, int]:
    """Analyse un batch d'articles (LLM → CI/IS → statut published/scored).

    Args:
        article_ids: IDs des articles à analyser.

    Returns:
        {published, scored, rejected, errors}
    """
    counts = {"published": 0, "scored": 0, "rejected": 0, "errors": 0}

    async with AsyncSessionLocal() as session:
        for article_id in article_ids:
            try:
                result = await analyze_article(article_id, session)
                await session.commit()
                if result.status == str(ArticleStatus.PUBLISHED):
                    counts["published"] += 1
                elif result.status == str(ArticleStatus.REJECTED):
                    counts["rejected"] += 1
                else:
                    counts["scored"] += 1
            except Exception as exc:
                logger.warning(f"Analysis failed for article {article_id}: {exc}")
                await session.rollback()
                counts["errors"] += 1

    return counts


@task(name="fetch-raw-article-ids", retries=1, retry_delay_seconds=10)
async def task_fetch_raw_ids(limit: int = _ANALYZE_BATCH_SIZE) -> list[int]:
    """Récupère les IDs des articles en statut 'raw' à analyser."""
    from sqlalchemy import select
    from models.db import Article

    async with AsyncSessionLocal() as session:
        rows = await session.scalars(
            select(Article.id)
            .where(Article.status == str(ArticleStatus.RAW))
            .order_by(Article.created_at.asc())
            .limit(limit)
        )
        return list(rows.all())


# ─────────────────────── Flow principal ──────────────────────────────────

@flow(
    name="daily-pipeline",
    description="Daily collect → analyze pipeline. Briefing runs separately at 06:00 UTC.",
    log_prints=True,
)
async def daily_pipeline_flow(
    sectors: list[str] | None = None,
    analyze_batch_size: int = _ANALYZE_BATCH_SIZE,
) -> dict:
    """Flow quotidien : collecte d'articles + analyse LLM batch.

    Étapes :
      1. Collecte articles (Brave + EventRegistry) pour tous les secteurs
      2. Récupère les IDs des articles en statut 'raw'
      3. Analyse les articles par batch (LLM → CI + IS → scored/published)

    Args:
        sectors: Secteurs à collecter. None = tous les secteurs.
        analyze_batch_size: Taille du batch d'analyse.
    """
    started_at = datetime.now(tz=timezone.utc)
    logger.info(f"Daily pipeline started at {started_at.isoformat()}")

    # Étape 1 : collecte
    collect_counts = await task_collect(sectors)
    total_collected = sum(collect_counts.values())
    logger.info(f"Collected {total_collected} new articles across {len(collect_counts)} sectors")

    # Étape 2 : récupération des IDs raw (inclut les articles d'avant si non traités)
    raw_ids = await task_fetch_raw_ids(analyze_batch_size)
    logger.info(f"Found {len(raw_ids)} raw articles to analyze")

    # Étape 3 : analyse batch
    analyze_counts: dict[str, int] = {"published": 0, "scored": 0, "rejected": 0, "errors": 0}
    if raw_ids:
        analyze_counts = await task_analyze_batch(raw_ids)
        logger.info(
            f"Analysis done — published={analyze_counts['published']} "
            f"scored={analyze_counts['scored']} rejected={analyze_counts['rejected']} "
            f"errors={analyze_counts['errors']}"
        )

    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    logger.info(f"Daily pipeline done in {elapsed:.1f}s")

    return {
        "collected_by_sector": collect_counts,
        "total_collected": total_collected,
        "analyzed": len(raw_ids),
        **analyze_counts,
        "elapsed_seconds": elapsed,
    }


# ─────────────────────── Deployment ──────────────────────────────────────

def build_deployment() -> None:
    """Crée le déploiement Prefect avec schedule quotidien 05:00 UTC.

    Usage : python -m flows.daily_pipeline
    """
    daily_pipeline_flow.serve(
        name="daily-pipeline-prod",
        cron="0 5 * * *",
        parameters={"sectors": None, "analyze_batch_size": _ANALYZE_BATCH_SIZE},
        tags=["oseta", "pipeline", "daily"],
    )
    logger.info("Deployment 'daily-pipeline-prod' registered in Prefect.")


if __name__ == "__main__":
    build_deployment()
