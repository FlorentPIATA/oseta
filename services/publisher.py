"""OSETA — Service publication : sélection articles + génération briefing.

Responsabilités :
  1. Sélectionner les meilleurs articles du jour (IS >= seuil)
  2. Appeler prompts/briefing.py pour générer le briefing exécutif
  3. Appeler prompts/signals.py pour détecter les signaux faibles

Pas de persistance du briefing en DB (MVP) — retourné au flow appelant.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Article
from models.enums import ArticleStatus
from prompts.briefing import BriefingOutput, generate_briefing
from prompts.signals import SignalOutput, detect_signals


_IS_BRIEFING_MIN = 40.0
_IS_SIGNALS_MIN = 60.0
_MAX_ARTICLES_BRIEFING = 10
_MAX_ARTICLES_SIGNALS = 20


async def _fetch_top_articles(
    session: AsyncSession,
    since: datetime,
    min_is: float,
    limit: int,
) -> list[dict[str, Any]]:
    """Récupère les articles récents avec IS >= seuil, triés par IS décroissant."""
    q = (
        select(Article)
        .where(
            and_(
                Article.status.in_([str(ArticleStatus.PUBLISHED), str(ArticleStatus.SCORED)]),
                Article.is_score >= min_is,
                Article.created_at >= since,
            )
        )
        .order_by(Article.is_score.desc())
        .limit(limit)
    )
    rows = await session.scalars(q)

    results: list[dict[str, Any]] = []
    for a in rows.all():
        analysis: dict[str, Any] = a.llm_analysis or {}
        results.append({
            "id": a.id,
            "title": a.title,
            "summary_meso": analysis.get("summary_meso", ""),
            "sector_tags": analysis.get("sector_tags", [a.sector_tag] if a.sector_tag else []),
            "weak_signals": analysis.get("weak_signals", []),
            "is_score": float(a.is_score or 0),
            "ci_score": float(a.ci_score or 0),
        })

    return results


async def generate_daily_briefing(
    session: AsyncSession,
    target_date: date | None = None,
    sector_focus: str | None = None,
    lookahead_hours: int = 24,
) -> BriefingOutput | None:
    """Génère le briefing exécutif quotidien.

    Args:
        session: Session async.
        target_date: Date cible (défaut : aujourd'hui UTC).
        sector_focus: Secteur à mettre en avant (optionnel).
        lookahead_hours: Fenêtre d'articles à inclure (défaut : dernières 24h).

    Returns:
        BriefingOutput généré, ou None si pas assez d'articles.
    """
    today = target_date or date.today()
    since = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) - timedelta(
        hours=lookahead_hours - 24
    )

    articles = await _fetch_top_articles(
        session, since=since, min_is=_IS_BRIEFING_MIN, limit=_MAX_ARTICLES_BRIEFING
    )

    if not articles:
        logger.warning(f"No articles found for briefing {today} (IS >= {_IS_BRIEFING_MIN})")
        return None

    import asyncio
    from functools import partial

    loop = asyncio.get_running_loop()
    try:
        briefing = await loop.run_in_executor(
            None,
            partial(
                generate_briefing,
                top_articles=articles,
                date_str=str(today),
                sector_focus=sector_focus,
            ),
        )
    except Exception as exc:
        logger.error(f"Briefing generation failed for {today}: {exc}")
        raise

    logger.info(
        f"Briefing generated for {today} — "
        f"{len(articles)} articles — headline: '{briefing.headline}'"
    )
    return briefing


async def detect_daily_signals(
    session: AsyncSession,
    target_date: date | None = None,
    sector_focus: str | None = None,
) -> SignalOutput | None:
    """Détecte les signaux faibles cross-articles du jour.

    Args:
        session: Session async.
        target_date: Date cible (défaut : aujourd'hui UTC).
        sector_focus: Secteur à surveiller en priorité (optionnel).

    Returns:
        SignalOutput avec la liste des signaux, ou None si pas assez d'articles.
    """
    today = target_date or date.today()
    since = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=24)

    articles = await _fetch_top_articles(
        session, since=since, min_is=_IS_SIGNALS_MIN, limit=_MAX_ARTICLES_SIGNALS
    )

    if len(articles) < 3:
        logger.warning(f"Not enough articles for signal detection on {today} ({len(articles)} found)")
        return None

    import asyncio
    from functools import partial

    loop = asyncio.get_running_loop()
    try:
        signals = await loop.run_in_executor(
            None,
            partial(detect_signals, articles=articles, sector_focus=sector_focus),
        )
    except Exception as exc:
        logger.error(f"Signal detection failed for {today}: {exc}")
        raise

    logger.info(
        f"Signal detection for {today}: {len(signals.signals)} signals found "
        f"(confidence={signals.analysis_confidence:.2f})"
    )
    return signals
