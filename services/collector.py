"""OSETA — Collecteur d'articles (Brave Search + EventRegistry).

Ingestion sources → persiste dans articles + sources tables.
Les clients HTTP sont dans collector_sources.py pour respecter la limite 200 lignes.
"""

from dataclasses import dataclass
from datetime import datetime

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Article, Source
from models.enums import ArticleStatus, SourceType
from services.collector_sources import fetch_brave, fetch_eventregistry
from services.exceptions import DataFetchError


@dataclass
class RawArticle:
    """Article brut avant persistance."""
    title: str
    url: str
    content: str
    published_at: datetime | None
    source_name: str
    source_type: SourceType
    sector_tag: str | None = None


SECTOR_QUERIES: dict[str, list[str]] = {
    "Technology":             ["AI semiconductor investment", "cloud hyperscaler infrastructure"],
    "Energy":                 ["renewable energy transition", "oil gas market geopolitics"],
    "Financials":             ["central bank monetary policy fintech", "banking regulation crisis"],
    "Health Care":            ["biotech clinical trial FDA approval", "healthcare AI diagnostic"],
    "Industrials":            ["supply chain disruption manufacturing", "industrial automation robotics"],
    "Materials":              ["critical minerals mining lithium", "commodity metals prices"],
    "Utilities":              ["power grid electrification nuclear", "energy storage battery grid"],
    "Communication Services": ["streaming media AI regulation", "telecom 5G spectrum"],
    "Real Estate":            ["commercial real estate rates", "data center construction REIT"],
}


async def _get_or_create_source(session: AsyncSession, name: str, source_type: SourceType) -> int:
    source_id = await session.scalar(select(Source.id).where(Source.name == name))
    if source_id is None:
        src = Source(name=name, type=str(source_type), reliability=0.6, is_active=True)
        session.add(src)
        await session.flush()
        source_id = src.id
    return source_id  # type: ignore[return-value]


async def _persist(session: AsyncSession, raw: list[dict], sector_tag: str | None) -> int:
    """Insère les articles non dupliqués. Retourne le nombre inséré."""
    inserted = 0
    for item in raw:
        exists = await session.scalar(select(Article.id).where(Article.url == item["url"]))
        if exists:
            continue
        source_id = await _get_or_create_source(session, item["source_name"], item["source_type"])
        session.add(Article(
            source_id=source_id,
            title=item["title"],
            content=item["content"],
            url=item["url"],
            published_at=item["published_at"],
            sector_tag=sector_tag or item.get("sector_tag"),
            status=str(ArticleStatus.RAW),
        ))
        inserted += 1
    await session.flush()
    return inserted


async def collect_sector_articles(
    session: AsyncSession,
    sectors: list[str] | None = None,
    articles_per_query: int = 10,
) -> dict[str, int]:
    """Collecte des articles pour les secteurs donnés (Brave + EventRegistry).

    Args:
        sectors: Secteurs cibles. None = tous les secteurs définis.
        articles_per_query: Articles récupérés par requête de recherche.

    Returns:
        {sector_name: nb_articles_insérés}
    """
    targets = sectors or list(SECTOR_QUERIES.keys())
    totals: dict[str, int] = {}

    async with httpx.AsyncClient() as client:
        for sector in targets:
            raw: list[dict] = []
            for query in SECTOR_QUERIES.get(sector, [sector]):
                try:
                    raw.extend(await fetch_brave(query, client, articles_per_query))
                except DataFetchError as exc:
                    logger.warning(f"Brave skipped for '{query}': {exc}")

                if settings.eventregistry_api_key:
                    try:
                        raw.extend(await fetch_eventregistry(query, client, articles_per_query))
                    except DataFetchError as exc:
                        logger.warning(f"EventRegistry skipped for '{query}': {exc}")

            count = await _persist(session, raw, sector_tag=sector)
            totals[sector] = count
            logger.info(f"Sector '{sector}': {count} new articles inserted")

    await session.commit()
    return totals
