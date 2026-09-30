"""Database engine, session factory, and declarative base for LaunchGuard AI."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./launchguard.db"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
