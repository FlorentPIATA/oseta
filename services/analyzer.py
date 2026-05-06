"""OSETA — Orchestration analyse LLM + scoring CI/IS d'un article.

Pipeline : Article(raw) → LLM analyze → LLM score_impact → CI + IS → Article(scored/published)
Les appels LLM (sync) sont exécutés dans un thread pool pour ne pas bloquer l'event loop.
"""

import asyncio
from functools import partial

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Article, Source
from models.enums import ArticleStatus
from models.schemas import ArticleDetailed
from prompts.analyze import analyze_article as _llm_analyze
from prompts.score_impact import score_impact as _llm_score_impact
from services.exceptions import AnalysisError, ArticleNotFoundError
from services.scorer import compute_ci, compute_is


async def analyze_article(article_id: int, session: AsyncSession) -> ArticleDetailed:
    """Analyse complète d'un article : LLM → scoring CI/IS → persistance.

    Args:
        article_id: ID de l'article à analyser.
        session: Session async ouverte par la route.

    Returns:
        ArticleDetailed avec scores et analyse LLM persistés.

    Raises:
        ArticleNotFoundError: Article introuvable.
        AnalysisError: Échec LLM après 3 retries.
    """
    result = await session.execute(
        select(Article, Source)
        .outerjoin(Source, Article.source_id == Source.id)
        .where(Article.id == article_id)
    )
    row = result.one_or_none()
    if row is None:
        raise ArticleNotFoundError(f"Article {article_id} not found")

    article, source = row

    if not article.content or len(article.content.strip()) < 50:
        article.status = str(ArticleStatus.REJECTED)
        await session.flush()
        logger.warning(f"Article {article_id} rejected — content too short")
        return ArticleDetailed.model_validate(article)

    loop = asyncio.get_running_loop()

    try:
        analysis = await loop.run_in_executor(
            None,
            partial(_llm_analyze, content=article.content, title=article.title or ""),
        )
        impact = await loop.run_in_executor(
            None,
            partial(
                _llm_score_impact,
                article_summary=analysis.summary_meso,
                sector_tags=analysis.sector_tags,
                entities=analysis.key_entities,
            ),
        )
    except Exception as exc:
        raise AnalysisError(f"LLM failed for article {article_id}: {exc}") from exc

    reliability = float(source.reliability) if source and source.reliability else 0.6
    ci = compute_ci(
        source_reliability=reliability,
        cross_source_count=1,
        published_at=article.published_at,
        has_contradiction=analysis.manipulation_warning,
        has_primary_source=True,
    )
    is_score = compute_is(
        llm_output=impact,
        sector_tags=analysis.sector_tags,
        source_domains=[source.name] if source else [],
    )

    article.sentiment_score = analysis.sentiment
    article.sector_tag = analysis.sector_tags[0] if analysis.sector_tags else article.sector_tag
    article.ci_score = ci.total
    article.is_score = is_score.total
    article.llm_analysis = {
        "summary_micro": analysis.summary_micro,
        "summary_meso": analysis.summary_meso,
        "key_entities": analysis.key_entities,
        "sector_tags": analysis.sector_tags,
        "disruption_level": analysis.disruption_level,
        "leading_indicators": analysis.leading_indicators,
        "weak_signals": analysis.weak_signals,
        "confidence": analysis.confidence,
        "manipulation_warning": analysis.manipulation_warning,
        "strategic_importance": impact.strategic_importance_raw,
        "risk_level": impact.risk_level,
        "recommended_action": impact.recommended_action,
        "ci_total": ci.total,
        "is_total": is_score.total,
        "is_alert": is_score.alert_required,
    }
    article.status = str(ArticleStatus.PUBLISHED if ci.is_published else ArticleStatus.SCORED)

    await session.flush()
    logger.info(
        f"Article {article_id} analyzed — "
        f"CI={ci.total:.1f} IS={is_score.total:.1f} status={article.status}"
    )
    return ArticleDetailed.model_validate(article)
