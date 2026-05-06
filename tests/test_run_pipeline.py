"""Subprocess test for scripts/run_pipeline.py.

Verifies the pipeline exits 0 and writes ≥1 CorrelationMatrixEntry when
pre-seeded ETF data exists. External API keys are intentionally left empty
so fetch_and_store_etfs/fred fail gracefully, letting the correlator run on
the already-present data.
"""

import os
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from models.db import CorrelationMatrixEntry, DataStream

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent

_MAIN_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://oseta:oseta@db:5432/oseta")
_TEST_ASYNC = os.getenv(
    "DATABASE_URL_TEST",
    _MAIN_URL.rsplit("/", 1)[0] + "/oseta_test",
)
_TEST_SYNC = _TEST_ASYNC.replace("postgresql+asyncpg", "postgresql")


@pytest_asyncio.fixture
async def seeded_correlation_data():
    """Seeds 40 days of fake ETF closes for XLK and XLF, cleans up after."""
    eng = create_async_engine(_TEST_ASYNC, poolclass=NullPool)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async with eng.begin() as conn:
        await conn.execute(
            text('TRUNCATE "correlation_matrix", "data_streams" RESTART IDENTITY CASCADE')
        )

    base_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
    async with factory() as s:
        for symbol, base_price in [("XLK", 180.0), ("XLF", 40.0)]:
            for i in range(40):
                s.add(DataStream(
                    time=base_date + timedelta(days=i),
                    stream_type="etf_price",
                    source_label=symbol,
                    sector_id=None,
                    value=base_price + i * 0.15 + (i % 5) * 0.3,
                    unit="USD",
                    is_stale=False,
                ))
        await s.commit()

    yield eng

    async with eng.begin() as conn:
        await conn.execute(
            text('TRUNCATE "correlation_matrix", "data_streams" RESTART IDENTITY CASCADE')
        )
    await eng.dispose()


@pytest.mark.asyncio
async def test_run_pipeline_exits_zero(seeded_correlation_data: AsyncSession) -> None:
    """Pipeline exits 0 and writes ≥1 correlation pair from pre-seeded data."""
    env = {
        **os.environ,
        "DATABASE_URL": _TEST_ASYNC,
        "DATABASE_URL_SYNC": _TEST_SYNC,
        "ALPHA_VANTAGE_API_KEY": "",   # triggers graceful DataFetchError
        "FRED_API_KEY": "",
        "ENVIRONMENT": "test",
    }

    result = subprocess.run(
        [sys.executable, "scripts/run_pipeline.py"],
        env=env,
        capture_output=True,
        timeout=30,
        cwd=str(_PROJECT_ROOT),
    )

    assert result.returncode == 0, (
        f"Pipeline exited {result.returncode}\n"
        f"stdout: {result.stdout.decode()}\n"
        f"stderr: {result.stderr.decode()}"
    )

    eng = seeded_correlation_data
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        count = await s.scalar(
            select(func.count()).select_from(CorrelationMatrixEntry)
        )

    assert count is not None and count >= 1, (
        f"Expected ≥1 CorrelationMatrixEntry written, found {count}"
    )
