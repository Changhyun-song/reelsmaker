from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config import get_settings

settings = get_settings()

_connect_args: dict = {}
if "neon.tech" in settings.database_url or "sslmode=require" in settings.database_url:
    _connect_args["ssl"] = True

engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
