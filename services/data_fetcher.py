"""OSETA — Collecte de données financières (Alpha Vantage + FRED).

Rate limits Alpha Vantage free tier : 5 appels/min, 25 appels/jour.
FRED : pas de limite stricte avec clé API.
"""

import asyncio
from datetime import datetime, timezone

import httpx
from fredapi import Fred
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import DataStream
from services.exceptions import DataFetchError


# ─────────────────────── Constantes ──────────────────────────────────────

SPDR_ETFS: dict[str, str] = {
    "XLK":  "Technology",
    "XLF":  "Financials",
    "XLE":  "Energy",
    "XLV":  "Health Care",
    "XLI":  "Industrials",
    "XLB":  "Materials",
    "XLU":  "Utilities",
    "XLC":  "Communication Services",
    "XLRE": "Real Estate",
}

FRED_SERIES: dict[str, tuple[str, str]] = {
    "DFF":      ("Fed Funds Rate",          "percent"),
    "DGS10":    ("10Y Treasury Yield",      "percent"),
    "CPIAUCSL": ("CPI All Urban Consumers", "index"),
    "UMCSENT":  ("Consumer Sentiment",      "index"),
}

_AV_BASE        = "https://www.alphavantage.co/query"
_AV_CALL_DELAY  = 13.0   # 5 calls/min → 12s + 1s buffer


# ─────────────────────── Alpha Vantage ───────────────────────────────────

async def _fetch_etf_ohlcv(symbol: str, client: httpx.AsyncClient) -> list[dict]:
    """Retourne [{date, close}] pour les 100 derniers jours via Alpha Vantage.

    Raises:
        DataFetchError: clé manquante, rate limit ou erreur API.
    """
    if not settings.alpha_vantage_api_key:
        raise DataFetchError("ALPHA_VANTAGE_API_KEY non configurée dans .env")

    try:
        resp = await client.get(
            _AV_BASE,
            params={
                "function":   "TIME_SERIES_DAILY",
                "symbol":     symbol,
                "outputsize": "compact",
                "apikey":     settings.alpha_vantage_api_key,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise DataFetchError(f"HTTP error fetching {symbol}: {exc}") from exc

    if "Note" in data:
        raise DataFetchError(f"Alpha Vantage rate limit atteint — réessayer dans 1 min")
    if "Error Message" in data:
        raise DataFetchError(f"Alpha Vantage: {data['Error Message']}")
    if "Time Series (Daily)" not in data:
        raise DataFetchError(f"Pas de données reçues pour {symbol}")

    return [
        {"date": dt_str, "close": float(v["4. close"])}
        for dt_str, v in data["Time Series (Daily)"].items()
    ]


# ─────────────────────── FRED ────────────────────────────────────────────

def _fetch_fred_sync(series_id: str, limit: int = 100) -> list[dict]:
    """Retourne [{date, value}] pour une série FRED (sync — fredapi non async).

    Raises:
        DataFetchError: clé manquante ou API indisponible.
    """
    if not settings.fred_api_key:
        raise DataFetchError("FRED_API_KEY non configurée dans .env")

    try:
        series = Fred(api_key=settings.fred_api_key).get_series(series_id)
        return [
            {"date": str(idx.date()), "value": float(v)}
            for idx, v in series.tail(limit).items()
            if v == v  # exclure NaN (NaN != NaN)
        ]
    except Exception as exc:
        raise DataFetchError(f"Erreur FRED {series_id}: {exc}") from exc


# ─────────────────────── Persistance ─────────────────────────────────────

async def _upsert(
    session: AsyncSession,
    time: datetime,
    stream_type: str,
    source_label: str,
    sector_id: int | None,
    value: float,
    unit: str,
) -> bool:
    """Insère dans data_streams. Retourne False si le point existe déjà."""
    exists = await session.scalar(
        select(DataStream.id).where(
            DataStream.time == time,
            DataStream.source_label == source_label,
        )
    )
    if exists:
        return False

    session.add(DataStream(
        time=time,
        stream_type=stream_type,
        source_label=source_label,
        sector_id=sector_id,
        value=value,
        unit=unit,
        is_stale=False,
    ))
    return True


# ─────────────────────── Orchestration publique ───────────────────────────

async def fetch_and_store_etfs(session: AsyncSession) -> dict[str, int]:
    """Télécharge les 9 ETFs SPDR et persiste dans data_streams.

    Respecte le rate limit AV free tier : 13 s entre chaque appel.
    """
    results: dict[str, int] = {}
    symbols = list(SPDR_ETFS.keys())

    async with httpx.AsyncClient() as client:
        for i, symbol in enumerate(symbols):
            try:
                rows = await _fetch_etf_ohlcv(symbol, client)
                count = 0
                for row in rows:
                    dt = datetime.strptime(row["date"], "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if await _upsert(session, dt, "etf_price", symbol, None, row["close"], "USD"):
                        count += 1
                results[symbol] = count
                logger.info(f"ETF {symbol}: {count} nouveaux points")
            except DataFetchError as exc:
                logger.warning(f"ETF {symbol} skipped: {exc}")
                results[symbol] = 0

            if i < len(symbols) - 1:
                await asyncio.sleep(_AV_CALL_DELAY)

    await session.commit()
    return results


async def fetch_and_store_fred(session: AsyncSession) -> dict[str, int]:
    """Télécharge les 4 indicateurs FRED et persiste dans data_streams."""
    results: dict[str, int] = {}
    loop = asyncio.get_event_loop()

    for series_id, (_, unit) in FRED_SERIES.items():
        try:
            rows = await loop.run_in_executor(None, _fetch_fred_sync, series_id)
            count = 0
            for row in rows:
                dt = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if await _upsert(session, dt, "macro_indicator", series_id, None, row["value"], unit):
                    count += 1
            results[series_id] = count
            logger.info(f"FRED {series_id}: {count} nouveaux points")
        except DataFetchError as exc:
            logger.warning(f"FRED {series_id} skipped: {exc}")
            results[series_id] = 0

    await session.commit()
    return results
