"""Unit test for report sharing capabilities and idempotency (T118, FR-033, contracts/api.md).

Asserts that:
1. POST /api/runs/{run_id}/share is idempotent (returns identical token on repeat calls).
2. GET /api/share/{token} exposes the read-only public report document.
3. A non-existent or purged run token returns 410 SHARE_NOT_AVAILABLE.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.main import app
from db.base import async_session_factory
from db.models import RunMode, RunModel, RunStatus, SourceType
from db.repo import create_run, update_run, upsert_report
from rule_engine.types import Verdict


@pytest.mark.asyncio
async def test_share_token_idempotent() -> None:
    """POST /api/runs/{run_id}/share returns identical token on repeated calls."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = f"test-share-idemp-{uuid.uuid4().hex[:8]}"

        async with async_session_factory() as session:
            await create_run(
                session=session,
                run_id=run_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await update_run(
                session=session,
                run_id=run_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.GO,
                risk_score=12,
                completed=True,
            )
            await upsert_report(
                session=session,
                run_id=run_id,
                verdict=Verdict.GO,
                risk_score=12,
                reasons=[],
                checklist=[
                    {"position": 1, "step_key": "body", "label": "Body", "status": "passed"}
                ],
                recommended_actions=[],
                disclaimer="Decision-support tool. Not a replacement for certified range safety.",
            )
            await session.commit()

        # First call generates token
        res1 = await client.post(f"/api/runs/{run_id}/share")
        assert res1.status_code == 200
        data1 = res1.json()
        assert "token" in data1
        assert data1["read_only"] is True
        token = data1["token"]

        # Second call returns same token
        res2 = await client.post(f"/api/runs/{run_id}/share")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["token"] == token


@pytest.mark.asyncio
async def test_get_public_report_by_token() -> None:
    """GET /api/share/{token} returns read-only document without controls."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_id = f"test-share-pub-{uuid.uuid4().hex[:8]}"
        share_token = f"share-cap-{uuid.uuid4().hex}"

        async with async_session_factory() as session:
            await create_run(
                session=session,
                run_id=run_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await update_run(
                session=session,
                run_id=run_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.HOLD,
                risk_score=48,
                completed=True,
            )
            await upsert_report(
                session=session,
                run_id=run_id,
                verdict=Verdict.HOLD,
                risk_score=48,
                reasons=["Fin deviation detected."],
                checklist=[
                    {"position": 2, "step_key": "fins", "label": "Fins", "status": "failed"}
                ],
                recommended_actions=["Re-measure fin alignment."],
                disclaimer="Decision-support tool. Not a replacement for certified range safety.",
                share_token=share_token,
            )
            await session.commit()

        res = await client.get(f"/api/share/{share_token}")
        assert res.status_code == 200
        data = res.json()
        assert data["run_id"] == run_id
        assert data["verdict"] == "HOLD"
        assert data["risk_score"] == 48
        assert "Decision-support tool" in data["disclaimer"]
        assert len(data["checklist"]) == 1
        assert len(data["reasons"]) == 1
        assert len(data["recommended_actions"]) == 1


@pytest.mark.asyncio
async def test_get_share_not_available_410() -> None:
    """Non-existent token or orphaned report returns 410 SHARE_NOT_AVAILABLE."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Non-existent token
        res_non = await client.get("/api/share/non-existent-share-token-xyz")
        assert res_non.status_code == 410
        data_non = res_non.json()
        assert "error" in data_non
        assert data_non["error"]["code"] == "SHARE_NOT_AVAILABLE"

        # 2. Token whose run was deleted
        orphaned_run_id = f"test-orphaned-{uuid.uuid4().hex[:8]}"
        orphaned_token = f"share-orphaned-{uuid.uuid4().hex}"

        async with async_session_factory() as session:
            await create_run(
                session=session,
                run_id=orphaned_run_id,
                mode=RunMode.INSPECTION,
                source_type=SourceType.IMAGE_UPLOAD,
            )
            await upsert_report(
                session=session,
                run_id=orphaned_run_id,
                verdict=Verdict.GO,
                risk_score=5,
                reasons=[],
                checklist=[],
                recommended_actions=[],
                disclaimer="Decision-support tool. Not a replacement for certified range safety.",
                share_token=orphaned_token,
            )
            # Delete run entity leaving orphaned report
            await session.execute(delete(RunModel).where(RunModel.id == orphaned_run_id))
            await session.commit()

        res_orphaned = await client.get(f"/api/share/{orphaned_token}")
        assert res_orphaned.status_code == 410
        data_orphaned = res_orphaned.json()
        assert "error" in data_orphaned
        assert data_orphaned["error"]["code"] == "SHARE_NOT_AVAILABLE"
