"""Single uploads and historical completed runs always have readable reports."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from db.base import async_session_factory
from db.models import RunMode, RunStatus, SourceType
from db.repo import append_finding, create_run, update_run
from rule_engine.types import Finding, Measurement, Severity, Verdict
from tests.conftest import FIXTURES_IMAGES


@pytest.mark.asyncio
async def test_single_upload_persists_complete_report_without_pending_narrative() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        result = await client.post("/api/inspections", files={
            "file": ("normal.jpg", content, "image/jpeg"),
        })
        assert result.status_code == 201
        run_id = result.json()["run_id"]
        report = await client.get(f"/api/runs/{run_id}/report")
        assert report.status_code == 200
        data = report.json()
        run = (await client.get(f"/api/runs/{run_id}")).json()
        assert data["verdict"] == run["verdict"]
        assert data["risk_score"] == run["risk_score"]
        assert data["narrative"]["status"] == "unavailable"
        assert len(data["checklist"]) == 5
        assert data["reasons"]
        assert (await client.post(f"/api/runs/{run_id}/share")).status_code == 200


@pytest.mark.asyncio
async def test_legacy_report_recovers_idempotently_without_changing_original_no_go() -> None:
    run_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        await create_run(session, mode=RunMode.INSPECTION,
                         source_type=SourceType.IMAGE_UPLOAD, run_id=run_id)
        await append_finding(session, run_id, Finding(
            module="cv.body", check_id="body.damage", severity=Severity.CRITICAL,
            confidence=0.8, message="Possible recorded damage.",
            metrics=(Measurement("recorded_area", 3, "%"),),
        ))
        await update_run(session, run_id, status=RunStatus.COMPLETED,
                         verdict=Verdict.NO_GO, risk_score=91, completed=True)
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get(f"/api/runs/{run_id}/report")
        second = await client.get(f"/api/runs/{run_id}/report")
        assert first.status_code == second.status_code == 200
        assert first.json()["report_id"] == second.json()["report_id"]
        assert first.json()["verdict"] == "NO-GO"
        assert first.json()["risk_score"] == 91
        assert first.json()["reasons"][0]["severity"] == "critical"
        assert first.json()["narrative"]["status"] == "unavailable"
        assert (await client.get(f"/api/runs/{run_id}")).json()["verdict"] == "NO-GO"


@pytest.mark.asyncio
async def test_unknown_and_unfinished_runs_do_not_get_fabricated_reports() -> None:
    run_id = str(uuid.uuid4())
    async with async_session_factory() as session:
        await create_run(session, mode=RunMode.INSPECTION,
                         source_type=SourceType.IMAGE_UPLOAD, run_id=run_id)
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(f"/api/runs/{run_id}/report")).status_code == 404
        assert (await client.get(f"/api/runs/{uuid.uuid4()}/report")).status_code == 404
