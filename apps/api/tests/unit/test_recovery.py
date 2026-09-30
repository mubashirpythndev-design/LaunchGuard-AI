"""Unit test for startup recovery of interrupted runs (Constitution 2.II, R12, T048)."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.recovery import reconcile_running_runs
from db.base import Base
from db.models import RunMode, RunStatus, SourceType
from db.repo import create_run, get_run, get_run_events


@dataclass
class MockTask:
    interrupts: tuple[str, ...] = ()


@dataclass
class MockCheckpointTuple:
    tasks: tuple[MockTask, ...] = ()
    metadata: dict[str, str] | None = None


class MockCheckpointer:
    def __init__(self, interrupted_threads: set[str]) -> None:
        self.interrupted_threads = interrupted_threads

    async def aget_tuple(self, config: dict[str, dict[str, str]]) -> MockCheckpointTuple | None:
        thread_id = config.get("configurable", {}).get("thread_id", "")
        if thread_id in self.interrupted_threads:
            return MockCheckpointTuple(tasks=(MockTask(interrupts=("awaiting_input",)),))
        return None


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_recovery_interrupted_run_becomes_paused(test_session: AsyncSession) -> None:
    # 1. Create a run that was left RUNNING
    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )
    assert run.status == RunStatus.RUNNING

    checkpointer = MockCheckpointer(interrupted_threads={run.id})

    # 2. Reconcile on startup
    await reconcile_running_runs(test_session, checkpointer)

    # 3. Assert run is now PAUSED and has no verdict
    updated = await get_run(test_session, run.id)
    assert updated is not None
    assert updated.status == RunStatus.PAUSED
    assert updated.verdict is None


@pytest.mark.asyncio
async def test_recovery_crashed_run_becomes_failed_with_interrupted_by_restart(
    test_session: AsyncSession,
) -> None:
    # 1. Create a run that was left RUNNING without an interrupt
    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )
    assert run.status == RunStatus.RUNNING

    checkpointer = MockCheckpointer(interrupted_threads=set())

    # 2. Reconcile on startup
    await reconcile_running_runs(test_session, checkpointer)

    # 3. Assert run is now FAILED with interrupted_by_restart and NO verdict
    updated = await get_run(test_session, run.id)
    assert updated is not None
    assert updated.status == RunStatus.FAILED
    assert updated.status_reason == "interrupted_by_restart"
    assert updated.verdict is None

    # 4. Assert run.failed event was persisted
    events = await get_run_events(test_session, run.id)
    assert len(events) == 1
    assert events[0].event_type == "run.failed"
    assert events[0].payload_json.get("reason") == "interrupted_by_restart"
