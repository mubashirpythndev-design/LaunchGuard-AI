"""Two concurrent subscribers test (T092, SC-006, Constitution 3.IV).

Verifies that two concurrent SSE subscribers on one run receive identical event streams,
preserve monotonic sequence ordering, and neither corrupts the run entity.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.events import broadcaster
from db.models import RunMode, SourceType
from db.repo import create_run


@pytest.mark.asyncio
async def test_two_concurrent_subscribers_stay_consistent(db_session: AsyncSession) -> None:
    """Two concurrent subscribers receive identical events without interfering."""
    run_id = "test-two-tabs-run"

    # 1. Create run
    run = await create_run(
        session=db_session,
        run_id=run_id,
        mode=RunMode.MONITOR,
        source_type=SourceType.LIVE_STREAM,
    )
    assert run.id == run_id

    # 2. Subscribe tab 1 and tab 2
    queue_1 = await broadcaster.subscribe(run_id)
    queue_2 = await broadcaster.subscribe(run_id)

    received_tab1: list[Any] = []
    received_tab2: list[Any] = []

    async def consume_tab1() -> None:
        while len(received_tab1) < 3:
            msg = await queue_1.get()
            received_tab1.append(msg)

    async def consume_tab2() -> None:
        while len(received_tab2) < 3:
            msg = await queue_2.get()
            received_tab2.append(msg)

    consumer_task1 = asyncio.create_task(consume_tab1())
    consumer_task2 = asyncio.create_task(consume_tab2())

    # Allow listener tasks to register
    await asyncio.sleep(0.05)

    # 3. Publish sequence of 3 events
    await broadcaster.publish(run_id, "frame.analyzed", {"frame_seq": 1}, session=db_session)
    await broadcaster.publish(run_id, "zone.alert", {"status": "WARNING"}, session=db_session)
    await broadcaster.publish(run_id, "frame.analyzed", {"frame_seq": 2}, session=db_session)

    # 4. Await both consumers
    await asyncio.wait_for(asyncio.gather(consumer_task1, consumer_task2), timeout=3.0)

    # 5. Assert both received all 3 events in exact same order with gapless sequence
    assert len(received_tab1) == 3
    assert len(received_tab2) == 3

    for msg1, msg2 in zip(received_tab1, received_tab2):
        assert msg1.seq == msg2.seq
        assert msg1.event_type == msg2.event_type
        assert msg1.payload == msg2.payload

    seqs = [m.seq for m in received_tab1]
    assert seqs == [1, 2, 3]
