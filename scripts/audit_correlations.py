"""Audit script: fetch ETF data and compute correlation matrix for audit gate."""
import asyncio
import sys

sys.path.insert(0, "/app")

from services.data_fetcher import fetch_and_store_etfs, fetch_and_store_fred
from services.correlation_store import run_correlation_job, load_sector_series
from services.database import AsyncSessionLocal


async def main() -> None:
    print("=== Step 1: Fetch ETF data (9 ETFs, ~2 min due to rate limit) ===", flush=True)
    async with AsyncSessionLocal() as session:
        etf = await fetch_and_store_etfs(session)
    for sym, count in etf.items():
        print(f"  {sym}: {count} new points", flush=True)

    print("=== Step 2: Fetch FRED macro data ===", flush=True)
    async with AsyncSessionLocal() as session:
        fred = await fetch_and_store_fred(session)
    for series_id, count in fred.items():
        print(f"  {series_id}: {count} new points", flush=True)

    print("=== Step 3: Compute correlation matrix (90d window, Pearson) ===", flush=True)
    async with AsyncSessionLocal() as session:
        result = await run_correlation_job(session, window_days=90)
    print(f"  Computed={result['computed']} pairs, skipped={result['skipped']}", flush=True)

    print("=== DONE ===", flush=True)


asyncio.run(main())
