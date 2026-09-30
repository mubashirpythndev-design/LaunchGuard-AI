"""In-process asyncio pub/sub and SSE stream generator.

Constitution 3.IV, Research R5, contracts/events.md.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.base import async_session_factory
from db.repo import append_run_event, get_run_events


def utc_iso_now() -> str:
    """Return RFC 3339 formatted current UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EventMessage:
    """Wire envelope for SSE stream events."""

    seq: int
    event_type: str
    payload: dict[str, Any]
    at: str

    def to_sse_frame(self) -> str:
        """Serialize event to a compliant single-line SSE frame."""
        data_json = json.dumps(
            {"seq": self.seq, "at": self.at, "payload": self.payload},
            separators=(",", ":"),
        )
        return f"id: {self.seq}\nevent: {self.event_type}\ndata: {data_json}\n\n"


class EventBroadcaster:
    """In-process pub/sub managing event fan-out per run_id."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._channels: dict[str, set[asyncio.Queue[EventMessage]]] = {}

    async def subscribe(self, run_id: str) -> asyncio.Queue[EventMessage]:
        """Register a subscriber queue for a specific run."""
        queue: asyncio.Queue[EventMessage] = asyncio.Queue()
        async with self._lock:
            if run_id not in self._channels:
                self._channels[run_id] = set()
            self._channels[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[EventMessage]) -> None:
        """Remove a subscriber queue and clean up empty run channels."""
        async with self._lock:
            if run_id in self._channels:
                self._channels[run_id].discard(queue)
                if not self._channels[run_id]:
                    del self._channels[run_id]

    async def publish(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        session: AsyncSession,
    ) -> EventMessage:
        """Persist event to database FIRST, then fan out to all active subscribers."""
        event_record = await append_run_event(
            session=session,
            run_id=run_id,
            event_type=event_type,
            payload=payload,
        )

        message = EventMessage(
            seq=event_record.seq,
            event_type=event_record.event_type,
            payload=event_record.payload_json,
            at=event_record.created_at.isoformat().replace("+00:00", "Z"),
        )

        async with self._lock:
            subscribers = list(self._channels.get(run_id, set()))

        for queue in subscribers:
            queue.put_nowait(message)

        return message

    def subscriber_count(self, run_id: str) -> int:
        """Return count of active subscribers for a run (used for testing)."""
        return len(self._channels.get(run_id, set()))


# Global in-process event broadcaster singleton (worker count = 1 required)
broadcaster = EventBroadcaster()


async def stream_run_events(
    run_id: str,
    last_event_id: int = 0,
    heartbeat_interval: float = 15.0,
) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events stream with DB replay and live pub/sub attachment."""
    # 1. Replay historical events from DB strictly greater than last_event_id
    replayed_max_seq = last_event_id
    async with async_session_factory() as session:
        records = await get_run_events(session, run_id, after_seq=last_event_id)
        for record in records:
            msg = EventMessage(
                seq=record.seq,
                event_type=record.event_type,
                payload=record.payload_json,
                at=record.created_at.isoformat().replace("+00:00", "Z"),
            )
            yield msg.to_sse_frame()
            if record.seq > replayed_max_seq:
                replayed_max_seq = record.seq

    # 2. Attach live subscriber queue
    queue = await broadcaster.subscribe(run_id)
    terminal_reached = False

    try:
        while not terminal_reached:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                # Deduplication: discard any message already yielded via replay
                if msg.seq <= replayed_max_seq:
                    continue

                replayed_max_seq = msg.seq
                yield msg.to_sse_frame()

                if msg.event_type in ("report.narrative_ready", "run.failed"):
                    terminal_reached = True
            except TimeoutError:
                # 15-second heartbeat to prevent idle connection termination
                yield ":heartbeat\n\n"
    finally:
        await broadcaster.unsubscribe(run_id, queue)
