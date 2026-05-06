"""OSETA — Configuration pytest et fixtures partagées."""

import asyncio
import os
from typing import AsyncGenerator
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from main import app
from models.db import Base
from services.database import get_session

_MAIN_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://oseta:oseta@db:5432/oseta")
_TEST_DB_URL = os.getenv(
    "DATABASE_URL_TEST",
    _MAIN_URL.rsplit("/", 1)[0] + "/oseta_test",
)


async def _ensure_test_db() -> None:
    parsed = urlparse(_TEST_DB_URL.replace("postgresql+asyncpg", "postgresql"))
    db_name = parsed.path.lstrip("/")
    try:
        conn = await asyncpg.connect(
            host=parsed.hostname or "db",
            port=parsed.port or 5432,
            user=parsed.username or "oseta",
            password=parsed.password or "oseta",
            database=parsed.username or "oseta",
        )
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}" OWNER "{parsed.username}"')
        await conn.close()
    except Exception:
        pass


def pytest_sessionstart(session: pytest.Session) -> None:
    """Crée la DB de test et le schéma avant le lancement des tests."""
    async def _setup() -> None:
        await _ensure_test_db()
        eng = create_async_engine(_TEST_DB_URL, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await eng.dispose()

    asyncio.run(_setup())


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Supprime le schéma de test après l'exécution de tous les tests."""
    async def _teardown() -> None:
        eng = create_async_engine(_TEST_DB_URL, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()

    asyncio.run(_teardown())


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Session DB isolée par test.

    L'engine est créé par test (NullPool) pour que toutes les opérations
    asyncpg utilisent la même boucle d'événements que la fonction de test.
    Tables tronquées au début (pas en teardown) pour éviter les conflits de loop.
    """
    eng = create_async_engine(_TEST_DB_URL, poolclass=NullPool)

    async with eng.begin() as conn:
        names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        if names:
            await conn.execute(text(f"TRUNCATE {names} CASCADE"))

    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False, autoflush=True)
    async with factory() as s:
        yield s

    await eng.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP ASGI FastAPI avec get_session overridé → session de test."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
