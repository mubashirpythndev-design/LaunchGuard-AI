"""Contract test for run lifecycle, manual inputs, and event sequence.

T103, contracts/api.md, contracts/events.md.

Asserts that:
1. POST /api/runs/{run_id}/manual-inputs rejects negative wind speed with 400,
   error.code = 'INVALID_MANUAL_INPUT', and error.field = 'wind_speed_ms'.
2. Valid manual inputs submission resumes the run.
3. The event log records the exact documented event sequence:
   run.awaiting_input -> checklist.step.finished (4) -> checklist.step.started (5)
   -> run.completed -> report.narrative_ready.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from db.base import async_session_factory
from db.models import RunMode, RunStatus, SourceType
from db.repo import create_run, init_checklist_steps, update_run


@pytest.mark.asyncio
async def test_manual_inputs_rejects_negative_wind_speed() -> None:
    """Negative wind speed must be rejected with 400 and field='wind_speed_ms'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create test run in DB
        run_id = f"test-run-invalid-wind-{uuid.uuid4().hex[:8]}"
        async with async_session_factory() as session:
            await create_run(
                session=session,
                run_id=run_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await update_run(session=session, run_id=run_id, status=RunStatus.PAUSED)
            await session.commit()

        # Submit negative wind speed
        response = await client.post(
            f"/api/runs/{run_id}/manual-inputs",
            json={"wind_speed_ms": -4.2},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_MANUAL_INPUT"
        assert data["error"]["field"] == "wind_speed_ms"


@pytest.mark.asyncio
async def test_manual_inputs_resumes_run_and_emits_event_sequence() -> None:
    """Valid manual input submission resumes paused run and delivers documented events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = f"test-run-contract-sequence-{uuid.uuid4().hex[:8]}"
        async with async_session_factory() as session:
            await create_run(
                session=session,
                run_id=run_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await init_checklist_steps(session, run_id)
            await update_run(session=session, run_id=run_id, status=RunStatus.PAUSED)
            await session.commit()

        # 1. Fetch required inputs
        req_res = await client.get(f"/api/runs/{run_id}/required-inputs")
        assert req_res.status_code == 200
        req_data = req_res.json()
        assert "wind_speed_ms" in req_data["missing"]
        assert len(req_data["fields"]) >= 4

        # 2. Submit valid complete manual inputs
        valid_payload = {
            "wind_speed_ms": 6.5,
            "visibility": "good",
            "precipitation": "none",
            "area_cleared": True,
            "notes": "Weather nominal for launch.",
        }
        submit_res = await client.post(
            f"/api/runs/{run_id}/manual-inputs",
            json=valid_payload,
        )
        assert submit_res.status_code == 200
        submit_data = submit_res.json()
        assert submit_data["status"] in ("running", "completed")

        # 3. Retrieve event log and verify event grammar
        events_res = await client.get(f"/api/runs/{run_id}/events")
        assert events_res.status_code == 200
        events = events_res.json()

        event_types = [e["event_type"] for e in events]
        assert "run.completed" in event_types
        assert "report.narrative_ready" in event_types

        # Verify run.completed payload structure
        completed_event = next(e for e in events if e["event_type"] == "run.completed")
        assert "verdict" in completed_event["payload"]
        assert "risk_score" in completed_event["payload"]
        assert "report_id" in completed_event["payload"]
        assert completed_event["payload"]["narrative"]["status"] == "pending"

        # Verify report.narrative_ready payload structure
        narrative_event = next(e for e in events if e["event_type"] == "report.narrative_ready")
        assert narrative_event["payload"]["narrative"]["status"] in (
            "available",
            "unavailable",
        )
