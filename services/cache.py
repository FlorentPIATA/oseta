"""OSETA — Cache Redis avec TTL simple.

Pas de pub/sub, pas d'invalidation complexe.
Stratégie : TTL + invalidation par versioning (cache_versions).
"""

import json
from typing import Any

import redis.asyncio as aioredis
from loguru import logger

from config import settings


_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Retourne le client Redis (singleton)."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def cache_get(key: str) -> Any | None:
    """Récupère une valeur du cache. Retourne None si absente ou expirée."""
    try:
        r = await get_redis()
        value = await r.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache GET error for key={key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int) -> bool:
    """Stocke une valeur avec TTL (secondes). Retourne False en cas d'erreur."""
    try:
        r = await get_redis()
        serialized = json.dumps(value, default=str)
        await r.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache SET error for key={key}: {e}")
        return False


async def cache_delete(key: str) -> None:
    """Supprime une entrée du cache."""
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as e:
        logger.warning(f"Cache DELETE error for key={key}: {e}")


# ─────────────────── Clés de cache standardisées ─────────────────────────

def key_correlation_matrix(method: str = "pearson") -> str:
    return f"correlation:matrix:{method}"


def key_sector_graph() -> str:
    return "sectors:graph"


def key_article_analysis(article_id: int) -> str:
    return f"article:analysis:{article_id}"


def key_sector_scores(sector_id: int) -> str:
    return f"sector:scores:{sector_id}"
