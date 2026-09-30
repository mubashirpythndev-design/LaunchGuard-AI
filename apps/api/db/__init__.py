"""Database package initialization and migration-free table creation."""
from __future__ import annotations

from db.base import Base, async_session_factory, engine, get_db
from db.models import (
    ChecklistStepModel,
    DangerZoneModel,
    DemoScenarioModel,
    FindingModel,
    ManualInputModel,
    NarrativeStatus,
    ReportModel,
    RunEventModel,
    RunMode,
    RunModel,
    RunStatus,
    SourceType,
    StepStatus,
)
from db.repo import seed_demo_scenarios


async def init_db() -> None:
    """Create all database tables if they do not exist and seed initial demo data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_demo_scenarios(session)
        await session.commit()


__all__ = [
    "Base",
    "ChecklistStepModel",
    "DangerZoneModel",
    "DemoScenarioModel",
    "FindingModel",
    "ManualInputModel",
    "NarrativeStatus",
    "ReportModel",
    "RunEventModel",
    "RunMode",
    "RunModel",
    "RunStatus",
    "SourceType",
    "StepStatus",
    "async_session_factory",
    "engine",
    "get_db",
    "init_db",
]
