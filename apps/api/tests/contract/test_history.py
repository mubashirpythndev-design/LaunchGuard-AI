"""Contract test for history and dashboard summary endpoints (T117, contracts/api.md).

Asserts that:
1. GET /api/runs?verdict= filters results by verdict and total is accurate.
2. GET /api/runs/latest returns the latest run's verdict, risk score, checklist, and recent runs.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from db.base import async_session_factory
from db.models import RunMode, RunStatus, SourceType, StepStatus
from db.repo import create_run, init_checklist_steps, update_checklist_step, update_run
from rule_engine.types import Verdict


@pytest.mark.asyncio
async def test_get_runs_filtering_by_verdict() -> None:
    """GET /api/runs filters correctly by verdict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid = uuid.uuid4().hex[:6]
        go_id = f"test-run-go-{uid}"
        hold_id = f"test-run-hold-{uid}"
        nogo_id = f"test-run-nogo-{uid}"

        async with async_session_factory() as session:
            # 1. Create GO run
            await create_run(
                session=session,
                run_id=go_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await update_run(
                session=session,
                run_id=go_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.GO,
                risk_score=15,
                completed=True,
            )

            # 2. Create HOLD run
            await create_run(
                session=session,
                run_id=hold_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await update_run(
                session=session,
                run_id=hold_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.HOLD,
                risk_score=55,
                completed=True,
            )

            # 3. Create NO-GO run
            await create_run(
                session=session,
                run_id=nogo_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await update_run(
                session=session,
                run_id=nogo_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.NO_GO,
                risk_score=90,
                completed=True,
            )
            await session.commit()

        # Query filter for GO
        res_go = await client.get("/api/runs?verdict=GO")
        assert res_go.status_code == 200
        data_go = res_go.json()
        assert data_go["total"] >= 1
        assert all(item["verdict"] == "GO" for item in data_go["items"])
        assert any(item["run_id"] == go_id for item in data_go["items"])

        # Query filter for NO-GO
        res_nogo = await client.get("/api/runs?verdict=NO-GO")
        assert res_nogo.status_code == 200
        data_nogo = res_nogo.json()
        assert data_nogo["total"] >= 1
        assert all(item["verdict"] == "NO-GO" for item in data_nogo["items"])
        assert any(item["run_id"] == nogo_id for item in data_nogo["items"])

        # Query without filter includes all
        res_all = await client.get("/api/runs")
        assert res_all.status_code == 200
        data_all = res_all.json()
        all_ids = [item["run_id"] for item in data_all["items"]]
        assert go_id in all_ids
        assert hold_id in all_ids
        assert nogo_id in all_ids


@pytest.mark.asyncio
async def test_get_runs_latest_summary() -> None:
    """GET /api/runs/latest returns dashboard summary with checklist and recent runs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        latest_id = f"test-run-latest-{uuid.uuid4().hex[:8]}"

        async with async_session_factory() as session:
            await create_run(
                session=session,
                run_id=latest_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await init_checklist_steps(session, latest_id)
            await update_checklist_step(session, latest_id, 1, StepStatus.PASSED)
            await update_run(
                session=session,
                run_id=latest_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.GO,
                risk_score=10,
                completed=True,
            )
            await session.commit()

        res = await client.get("/api/runs/latest")
        assert res.status_code == 200
        data = res.json()
        assert data["verdict"] is not None
        assert data["risk_score"] is not None
        assert len(data["checklist"]) == 5
        assert len(data["latest_runs"]) >= 1
        # The newest run should be at the front of latest_runs
        assert data["latest_runs"][0]["run_id"] == latest_id
