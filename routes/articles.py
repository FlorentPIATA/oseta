"""OSETA — Routes articles : CRUD + déclenchement analyse LLM.

Endpoints :
  GET  /articles                  → liste paginée + filtres
  GET  /articles/{id}             → article + analyse LLM complète
  POST /articles/{id}/analyze     → déclenche scoring CI/IS
  POST /articles/collect          → collecte manuelle (X-Master-Key requis)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Article
from models.enums import ArticleStatus
from models.schemas import ArticleDetailed, ArticleListResponse, ArticleRead
from services.analyzer import analyze_article
from services.collector import collect_sector_articles
from services.database import get_session
from services.exceptions import AnalysisError, ArticleNotFoundError

router = APIRouter()


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    article_status: ArticleStatus | None = Query(None, alias="status"),
    sector_tag: str | None = Query(None),
    min_ci: float | None = Query(None, ge=0, le=100),
    min_is: float | None = Query(None, ge=0, le=100),
    session: AsyncSession = Depends(get_session),
) -> ArticleListResponse:
    """Liste paginée des articles avec filtres optionnels."""
    q = select(Article).order_by(Article.created_at.desc())

    if article_status is not None:
        q = q.where(Article.status == str(article_status))
    if sector_tag is not None:
        q = q.where(Article.sector_tag == sector_tag)
    if min_ci is not None:
        q = q.where(Article.ci_score >= min_ci)
    if min_is is not None:
        q = q.where(Article.is_score >= min_is)

    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    rows = await session.scalars(q.offset(skip).limit(limit))

    return ArticleListResponse(
        items=[ArticleRead.model_validate(a) for a in rows.all()],
        total=total or 0,
        skip=skip,
        limit=limit,
    )


# /collect doit être défini AVANT /{article_id} pour éviter le shadowing
@router.post("/collect", status_code=status.HTTP_202_ACCEPTED)
async def trigger_collect(
    x_master_key: Annotated[str | None, Header()] = None,
    sectors: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Déclenche la collecte manuelle (Brave + EventRegistry). Protégé par X-Master-Key.

    Passer les secteurs via query params répétés : ?sectors=Technology&sectors=Energy
    Sans paramètre → collecte tous les secteurs définis.
    """
    if x_master_key != settings.oseta_master_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid master key",
        )

    results = await collect_sector_articles(session, sectors=sectors)
    return {"collected": results, "total": sum(results.values())}


@router.get("/{article_id}", response_model=ArticleDetailed)
async def get_article(
    article_id: int,
    session: AsyncSession = Depends(get_session),
) -> ArticleDetailed:
    """Récupère un article avec son analyse LLM et ses scores CI/IS."""
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found",
        )
    return ArticleDetailed.model_validate(article)


@router.post("/{article_id}/analyze", response_model=ArticleDetailed)
async def trigger_analyze(
    article_id: int,
    session: AsyncSession = Depends(get_session),
) -> ArticleDetailed:
    """Déclenche l'analyse LLM + scoring CI/IS d'un article.

    Transitions de statut possibles :
      raw → analyzed → scored → published
      raw → rejected  (contenu trop court)
    """
    try:
        result = await analyze_article(article_id, session)
        await session.commit()
        return result
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except AnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
