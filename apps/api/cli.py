"""CLI entry points for ReelsMaker API management tasks."""
import asyncio
import sys

from shared.config import setup_logging
from shared.database import async_session_factory


logger = setup_logging("reelsmaker.cli")


async def _run_seed():
    from app.seed import run_all_seeds
    async with async_session_factory() as session:
        await run_all_seeds(session)
    logger.info("Seed completed")


async def _run_reset():
    """Drop all data and re-seed."""
    from shared.models import Base
    from shared.database import engine

    logger.warning("Resetting database — dropping all tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables recreated")

    from app.seed import run_all_seeds
    async with async_session_factory() as session:
        await run_all_seeds(session)
    logger.info("Reset + seed completed")


def main():
    if len(sys.argv) < 2:
        print("Usage: python cli.py <command>")
        print("Commands: seed, reset")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "seed":
        asyncio.run(_run_seed())
    elif cmd == "reset":
        asyncio.run(_run_reset())
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
