"""OSETA — Configuration de la base de données async.

Toutes les sessions DB sont async. Utiliser get_session() comme dépendance FastAPI.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models.db import Base

_PROD = settings.is_production

engine = create_async_engine(
    settings.database_url,
    # Production (Neon free tier): 10 concurrent connection limit — stay well under it.
    # Development (local Docker): no limit, use larger pool for parallel test runs.
    pool_size=3 if _PROD else 10,
    max_overflow=2 if _PROD else 20,
    pool_timeout=30,
    pool_recycle=1800,   # Neon drops idle connections after ~5 min — recycle proactively
    echo=not _PROD,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI — session DB async avec gestion auto du commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
