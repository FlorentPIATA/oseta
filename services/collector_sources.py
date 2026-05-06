"""OSETA — Clients HTTP Brave Search + EventRegistry.

Extrait de collector.py pour respecter la limite de 200 lignes.
"""

from datetime import datetime

import httpx
from loguru import logger

from config import settings
from models.enums import SourceType
from services.exceptions import DataFetchError

_BRAVE_URL = "https://api.search.brave.com/res/v1/news/search"
_EVENTREGISTRY_URL = "https://eventregistry.org/api/v1/article/getArticles"


# Import circulaire évité : RawArticle est défini dans collector.py,
# donc on retourne des dicts ici et collector.py construit les RawArticle.

async def fetch_brave(
    query: str,
    client: httpx.AsyncClient,
    count: int = 10,
) -> list[dict]:
    """Récupère des articles via Brave News Search.

    Args:
        query: Terme de recherche.
        client: Client HTTPX partagé.
        count: Nombre d'articles demandés.

    Returns:
        Liste de dicts bruts (title, url, content, published_at, source_name, source_type).

    Raises:
        DataFetchError: Clé manquante, 429 ou erreur HTTP.
    """
    if not settings.brave_api_key:
        raise DataFetchError("BRAVE_API_KEY non configurée dans .env")

    try:
        resp = await client.get(
            _BRAVE_URL,
            params={"q": query, "count": count, "freshness": "pw"},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": settings.brave_api_key,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise DataFetchError(f"Brave HTTP {exc.response.status_code} for '{query}'") from exc
    except httpx.HTTPError as exc:
        raise DataFetchError(f"Brave network error for '{query}': {exc}") from exc

    results: list[dict] = []
    for item in data.get("results", []):
        url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        if not url or not title:
            continue

        pub_at: datetime | None = None
        age = item.get("age") or item.get("page_age")
        if isinstance(age, str):
            try:
                pub_at = datetime.fromisoformat(age.replace("Z", "+00:00"))
            except ValueError:
                pass

        source_name = (item.get("meta_url") or {}).get("hostname") or "brave_news"
        results.append({
            "title": title,
            "url": url,
            "content": item.get("description", "") or "",
            "published_at": pub_at,
            "source_name": source_name,
            "source_type": SourceType.NEWS,
        })

    logger.debug(f"Brave '{query}': {len(results)} articles fetched")
    return results


async def fetch_eventregistry(
    query: str,
    client: httpx.AsyncClient,
    count: int = 10,
) -> list[dict]:
    """Récupère des articles via EventRegistry.

    Args:
        query: Terme de recherche.
        client: Client HTTPX partagé.
        count: Nombre d'articles demandés.

    Returns:
        Liste de dicts bruts.

    Raises:
        DataFetchError: Clé manquante ou erreur HTTP.
    """
    if not settings.eventregistry_api_key:
        raise DataFetchError("EVENTREGISTRY_API_KEY non configurée dans .env")

    try:
        resp = await client.post(
            _EVENTREGISTRY_URL,
            json={
                "action": "getArticles",
                "keyword": query,
                "articlesCount": count,
                "articlesSortBy": "date",
                "resultType": "articles",
                "dataType": ["news"],
                "apiKey": settings.eventregistry_api_key,
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise DataFetchError(f"EventRegistry error for '{query}': {exc}") from exc

    results: list[dict] = []
    for item in data.get("articles", {}).get("results", []):
        url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        if not url or not title:
            continue

        pub_at: datetime | None = None
        date_str = item.get("dateTime") or item.get("date")
        if isinstance(date_str, str):
            try:
                pub_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        source_name = (item.get("source") or {}).get("title") or "eventregistry"
        results.append({
            "title": title,
            "url": url,
            "content": item.get("body", "") or item.get("description", "") or "",
            "published_at": pub_at,
            "source_name": source_name,
            "source_type": SourceType.NEWS,
        })

    logger.debug(f"EventRegistry '{query}': {len(results)} articles fetched")
    return results
