"""OSETA — Persistence couche corrélation : chargement séries + sauvegarde matrice.

Séparation intentionnelle : correlator.py = math pur, correlation_store.py = I/O.
Appelé par flows/correlation_job.py, jamais sur requête API directe.
"""

from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import CorrelationMatrixEntry, DataStream, Sector
from models.enums import CorrelationMethod, SectorLevel
from services.correlator import RawCorrelation, compute_correlation_matrix, find_optimal_lag
from services.data_fetcher import SPDR_ETFS


# ─────────────────────── Helpers internes ────────────────────────────────

async def _get_or_create_sector(session: AsyncSession, code: str, name: str) -> int:
    """Retourne l'id du secteur, le crée s'il n'existe pas."""
    sector_id = await session.scalar(select(Sector.id).where(Sector.code == code))
    if sector_id is None:
        sector = Sector(code=code, name=name, level=SectorLevel.MACRO)
        session.add(sector)
        await session.flush()
        sector_id = sector.id
    return sector_id  # type: ignore[return-value]


# ─────────────────────── Lecture ─────────────────────────────────────────

async def load_sector_series(
    session: AsyncSession,
    window_days: int = 90,
) -> dict[str, list[float]]:
    """Charge les séries de prix ETF depuis data_streams.

    Returns:
        {etf_symbol: [valeurs close triées ASC par date]}
    """
    since = datetime.now(tz=timezone.utc) - timedelta(days=window_days)
    rows = await session.execute(
        select(DataStream.source_label, DataStream.value)
        .where(
            DataStream.stream_type == "etf_price",
            DataStream.time >= since,
            DataStream.is_stale == False,  # noqa: E712
        )
        .order_by(DataStream.source_label, DataStream.time.asc())
    )

    series: dict[str, list[float]] = {}
    for label, value in rows:
        series.setdefault(label, []).append(float(value))

    logger.info(f"Loaded {len(series)} ETF series (window={window_days}d)")
    return series


async def get_latest_matrix(
    session: AsyncSession,
    method: CorrelationMethod = CorrelationMethod.PEARSON,
) -> list[CorrelationMatrixEntry]:
    """Retourne les entrées de la dernière matrice calculée (pour le heatmap API)."""
    latest_at = await session.scalar(
        select(CorrelationMatrixEntry.computed_at)
        .where(CorrelationMatrixEntry.method == method)
        .order_by(CorrelationMatrixEntry.computed_at.desc())
        .limit(1)
    )
    if latest_at is None:
        return []

    rows = await session.execute(
        select(CorrelationMatrixEntry).where(
            CorrelationMatrixEntry.computed_at == latest_at,
            CorrelationMatrixEntry.method == method,
        )
    )
    return list(rows.scalars().all())


# ─────────────────────── Orchestration ───────────────────────────────────

async def run_correlation_job(
    session: AsyncSession,
    window_days: int = 90,
    method: CorrelationMethod = CorrelationMethod.PEARSON,
    max_lag_days: int = 60,
) -> dict[str, int]:
    """Calcule et persiste la matrice de corrélation complète.

    Pipeline : load series → compute matrix → find lag → upsert DB.
    Doit être appelé par le flow Prefect, jamais déclenché par une requête API.

    Returns:
        {"computed": N, "skipped": M}
    """
    series = await load_sector_series(session, window_days)
    if len(series) < 2:
        logger.warning("Not enough ETF series to compute correlations (need ≥ 2)")
        return {"computed": 0, "skipped": 0}

    sector_ids: dict[str, int] = {}
    for symbol, name in SPDR_ETFS.items():
        if symbol in series:
            sector_ids[symbol] = await _get_or_create_sector(session, symbol, name)
    await session.flush()

    matrix: dict[tuple[str, str], RawCorrelation] = compute_correlation_matrix(series, method)
    computed_at = datetime.now(tz=timezone.utc)
    computed = skipped = 0

    for (code_a, code_b), corr in matrix.items():
        if code_a not in sector_ids or code_b not in sector_ids:
            skipped += 1
            continue

        lag = find_optimal_lag(series[code_a], series[code_b], max_lag_days)

        already_exists = await session.scalar(
            select(CorrelationMatrixEntry.id).where(
                CorrelationMatrixEntry.computed_at == computed_at,
                CorrelationMatrixEntry.sector_a_id == sector_ids[code_a],
                CorrelationMatrixEntry.sector_b_id == sector_ids[code_b],
                CorrelationMatrixEntry.method == method,
            )
        )
        if not already_exists:
            session.add(CorrelationMatrixEntry(
                computed_at=computed_at,
                sector_a_id=sector_ids[code_a],
                sector_b_id=sector_ids[code_b],
                correlation=corr.coefficient,
                p_value=corr.p_value,
                lag_days=lag.optimal_lag_days,
                method=method,
                window_days=window_days,
                sample_size=len(series[code_a]),
            ))
            computed += 1

    await session.commit()
    logger.info(f"Correlation job: {computed} pairs computed, {skipped} skipped")
    return {"computed": computed, "skipped": skipped}
