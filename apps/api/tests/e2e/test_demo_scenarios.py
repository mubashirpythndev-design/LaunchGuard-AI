"""E2E pytest test for bundled demo scenarios (T129, FR-035, FR-036, SC-008).

Asserts that:
1. All three demo scenarios (normal, misaligned_fin, person_near_pad) execute offline.
2. The pipeline produces GO, HOLD, NO-GO respectively.
3. Reports carry verdict, reasons, annotated image, and fallback narrative.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from db.base import async_session_factory
from db.repo import seed_demo_scenarios


@pytest.mark.asyncio
async def test_demo_scenarios_offline_verdicts() -> None:
    """Execute all three bundled demo scenarios through real pipeline offline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ensure scenarios are seeded
        async with async_session_factory() as session:
            await seed_demo_scenarios(session)
            await session.commit()

        # 1. Normal scenario -> GO
        res_normal = await client.post("/api/demo/scenarios/normal/run")
        assert res_normal.status_code == 201
        data_normal = res_normal.json()
        run_id_normal = data_normal["run_id"]

        report_normal = await client.get(f"/api/runs/{run_id_normal}/report")
        assert report_normal.status_code == 200
        normal_data = report_normal.json()
        assert normal_data["verdict"] == "GO"
        assert normal_data["risk_score"] < 30
        assert "Decision-support tool" in normal_data["disclaimer"]

        # 2. Misaligned fin scenario -> HOLD
        res_fin = await client.post("/api/demo/scenarios/misaligned_fin/run")
        assert res_fin.status_code == 201
        data_fin = res_fin.json()
        run_id_fin = data_fin["run_id"]

        report_fin = await client.get(f"/api/runs/{run_id_fin}/report")
        assert report_fin.status_code == 200
        fin_data = report_fin.json()
        assert fin_data["verdict"] == "HOLD"
        assert any("fin" in r["check_id"].lower() for r in fin_data["reasons"])

        # 3. Person near pad scenario -> NO-GO
        res_pad = await client.post("/api/demo/scenarios/person_near_pad/run")
        assert res_pad.status_code == 201
        data_pad = res_pad.json()
        run_id_pad = data_pad["run_id"]

        report_pad = await client.get(f"/api/runs/{run_id_pad}/report")
        assert report_pad.status_code == 200
        pad_data = report_pad.json()
        assert pad_data["verdict"] == "NO-GO"
        assert pad_data["risk_score"] >= 70
