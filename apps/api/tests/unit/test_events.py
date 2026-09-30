"""Unit tests for SSE event broadcasting, DB persistence, fan-out, and reconnection (T047)."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.events as events_module
from app.events import EventBroadcaster, stream_run_events
from db.base import Base
from db.models import RunMode, SourceType
from db.repo import create_run


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
async def test_sse_fan_out_and_reconnection(test_session: AsyncSession) -> None:
    # Set up test broadcaster and mock session factory for stream generator
    test_broadcaster = EventBroadcaster()
    events_module.broadcaster = test_broadcaster

    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )
    run_id = run.id

    # 1. Two subscribers attach
    q1 = await test_broadcaster.subscribe(run_id)
    q2 = await test_broadcaster.subscribe(run_id)
    assert test_broadcaster.subscriber_count(run_id) == 2

    # 2. Publish 3 events
    msg1 = await test_broadcaster.publish(
        run_id, "checklist.step.started", {"position": 1}, test_session
    )
    msg2 = await test_broadcaster.publish(
        run_id, "finding.raised", {"check_id": "body.cracks"}, test_session
    )
    msg3 = await test_broadcaster.publish(
        run_id, "checklist.step.finished", {"position": 1}, test_session
    )

    # 3. Assert sequence is monotonic and gapless
    assert msg1.seq == 1
    assert msg2.seq == 2
    assert msg3.seq == 3

    # 4. Both subscribers receive every event
    rec1 = [await q1.get(), await q1.get(), await q1.get()]
    rec2 = [await q2.get(), await q2.get(), await q2.get()]

    assert [m.seq for m in rec1] == [1, 2, 3]
    assert [m.seq for m in rec2] == [1, 2, 3]

    # 5. Clean up first two subscribers
    await test_broadcaster.unsubscribe(run_id, q1)
    await test_broadcaster.unsubscribe(run_id, q2)
    assert test_broadcaster.subscriber_count(run_id) == 0


@pytest.mark.asyncio
async def test_last_event_id_deduplication(
    monkeypatch: pytest.MonkeyPatch,
    test_session: AsyncSession,
) -> None:
    test_broadcaster = EventBroadcaster()
    events_module.broadcaster = test_broadcaster

    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )
    run_id = run.id

    # Publish 3 events to DB
    await test_broadcaster.publish(run_id, "step.1", {}, test_session)
    await test_broadcaster.publish(run_id, "step.2", {}, test_session)
    await test_broadcaster.publish(run_id, "step.3", {}, test_session)

    # Mock async_session_factory in events module to use our test session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session_factory() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    monkeypatch.setattr(events_module, "async_session_factory", mock_session_factory)

    # Reconnect with last_event_id = 2 -> Should only receive seq = 3
    collected_frames: list[str] = []
    gen = stream_run_events(run_id, last_event_id=2, heartbeat_interval=0.1)

    async def consume_one() -> None:
        async for frame in gen:
            collected_frames.append(frame)
            break

    await asyncio.wait_for(consume_one(), timeout=1.0)

    assert len(collected_frames) == 1
    assert "id: 3" in collected_frames[0]
    assert "id: 1" not in collected_frames[0]
    assert "id: 2" not in collected_frames[0]
