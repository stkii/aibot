"""Async SQLAlchemy engine, session factory, and initialization."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.aibot.db import models  # noqa: F401  (imported to register ORM metadata)
from src.aibot.db.base import Base

_DATABASE_URL = "sqlite+aiosqlite:///aibot.db"

engine = create_async_engine(_DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they do not already exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional session scope (commit on success, rollback on error)."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
