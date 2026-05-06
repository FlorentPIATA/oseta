"""OSETA — Prefect worker entry point."""

import asyncio
from loguru import logger


async def main() -> None:
    """Keep worker alive — flows are triggered via Prefect UI or API."""
    logger.info("OSETA worker started, waiting for flow runs...")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
