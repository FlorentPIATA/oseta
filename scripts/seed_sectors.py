"""OSETA — Seed des 9 secteurs SPDR en base.

À lancer une seule fois après `alembic upgrade head`.
Idempotent : ne recrée pas les secteurs déjà existants.

Usage :
    docker compose exec api python scripts/seed_sectors.py
"""

import asyncio

from loguru import logger
from sqlalchemy import select

from models.db import Sector
from services.database import AsyncSessionLocal

SECTORS = [
    ("XLK",  "Technology",             "macro"),
    ("XLF",  "Financials",             "macro"),
    ("XLE",  "Energy",                 "macro"),
    ("XLV",  "Health Care",            "macro"),
    ("XLI",  "Industrials",            "macro"),
    ("XLB",  "Materials",              "macro"),
    ("XLU",  "Utilities",              "macro"),
    ("XLC",  "Communication Services", "macro"),
    ("XLRE", "Real Estate",            "macro"),
]


async def seed() -> None:
    """Insère les secteurs manquants. Log chaque action."""
    async with AsyncSessionLocal() as session:
        inserted = 0
        for code, name, level in SECTORS:
            exists = await session.scalar(select(Sector.id).where(Sector.code == code))
            if exists:
                logger.info(f"Sector '{code}' already exists — skipped")
                continue
            session.add(Sector(code=code, name=name, level=level))
            inserted += 1
            logger.info(f"Sector '{code}' ({name}) created")

        await session.commit()
        logger.info(f"Done — {inserted} sectors inserted, {len(SECTORS) - inserted} skipped")


if __name__ == "__main__":
    asyncio.run(seed())
