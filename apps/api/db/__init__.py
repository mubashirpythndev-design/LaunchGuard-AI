"""Database package initialization and migration-free table creation."""

from __future__ import annotations

from sqlalchemy import Connection, inspect, text

from db.base import Base, async_session_factory, engine, get_db
from db.models import (
    ChecklistStepModel,
    DangerZoneModel,
    DemoScenarioModel,
    FindingModel,
    ManualInputModel,
    NarrativeStatus,
    ReportModel,
    RocketModel,
    RocketReferenceModel,
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
        # Additive, idempotent migration for existing Day 1 SQLite databases.
        for table, column, definition in (
            ("runs", "rocket_id", "VARCHAR(36) REFERENCES rockets(id)"),
            ("findings", "quadrant", "VARCHAR(10)"),
        ):
            def column_names(sync_conn: Connection) -> set[str]:
                return {entry["name"] for entry in inspect(sync_conn).get_columns(table)}

            columns = await conn.run_sync(column_names)
            if column not in columns:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))

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
    "RocketModel",
    "RocketReferenceModel",
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
