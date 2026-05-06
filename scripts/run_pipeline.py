"""Daily correlation pipeline — runs as a Render cron job (no Prefect, no LLM calls).

Schedule: 05:00 UTC daily (see render.yaml)
Usage:    python scripts/run_pipeline.py
"""

import asyncio
import sys

from loguru import logger

from services.correlation_store import run_correlation_job
from services.data_fetcher import fetch_and_store_etfs, fetch_and_store_fred
from services.database import AsyncSessionLocal


async def main() -> None:
    logger.info("Pipeline started: fetch ETFs + FRED → compute correlations")

    async with AsyncSessionLocal() as session:
        etf_counts = await fetch_and_store_etfs(session)
    etf_new = sum(etf_counts.values())
    logger.info(f"ETF fetch done — {etf_new} new data points across {len(etf_counts)} symbols")

    async with AsyncSessionLocal() as session:
        fred_counts = await fetch_and_store_fred(session)
    fred_new = sum(fred_counts.values())
    logger.info(f"FRED fetch done — {fred_new} new data points")

    async with AsyncSessionLocal() as session:
        result = await run_correlation_job(session, window_days=90)
    logger.info(f"Correlation matrix: {result['computed']} pairs computed, {result['skipped']} skipped")

    logger.info("Pipeline complete")


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
